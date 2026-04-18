import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import questionary

from .config import BASE_DIR, DATA_DIR, COUCHDB_DATA, GDRIVE_FOLDER_ID, DISCORD_URL
from .logger import setup_logger
from .notifier import DiscordNotifier
from .auth import GoogleDriveAuthenticator

logger = setup_logger(__name__)
notifier = DiscordNotifier(DISCORD_URL)

class RestoreManager:
    """구글 드라이브 백업 파일 복구 매니저"""

    def __init__(self):
        self.authenticator = GoogleDriveAuthenticator(notifier)
        self.service: Any = None

    def authenticate(self) -> None:
        """인증을 수행하고 드라이브 서비스를 빌드한다."""
        creds = self.authenticator.get_credentials()
        self.service = build("drive", "v3", credentials=creds, static_discovery=False)
        logger.info("구글 드라이브 서비스가 준비되었습니다.")

    def run(self) -> None:
        """대화형 인터페이스 기반의 전체 복구 워크플로우 실행"""
        try:
            self.authenticate()

            logger.info("구글 드라이브에서 백업 목록을 가져오는 중...")
            query = f"'{GDRIVE_FOLDER_ID}' in parents and name contains 'obsidian_db_snapshot_' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc",
            ).execute()

            files = results.get("files", [])
            if not files:
                logger.error("구글 드라이브에 복구할 백업 파일이 없습니다.")
                return

            choices = []
            for f in files:
                choices.append({
                    "name": f"{f['name']}",
                    "value": f
                })

            # 사용자에게 복구할 파일 선택받기
            selected_file = questionary.select(
                "복구할 백업 파일을 선택하세요 (위아래 방향키 이동, Enter 선택):",
                choices=choices
            ).ask()

            if not selected_file:
                logger.info("복구 작업이 취소되었습니다.")
                return

            file_id = selected_file["id"]
            file_name = selected_file["name"]

            logger.warning("⚠️ 복구 시 현재 로컬 데이터는 모두 'couchdb_backup_pre_restore'로 덮어씌워지고 삭제됩니다.")
            
            auto_docker = questionary.confirm(
                "도커 컨테이너를 자동으로 중지하고, 복구 완료 후 다시 시작하시겠습니까?",
                default=True
            ).ask()
            
            if auto_docker is None:
                logger.info("복구 작업이 취소되었습니다.")
                return

            # 도커 중지
            if auto_docker:
                logger.info("도커 컨테이너 중지 중 (docker compose down couchdb)...")
                subprocess.run(["docker", "compose", "down", "couchdb"], cwd=BASE_DIR, check=False)
                time.sleep(2)

            # 다운로드 폴더 임시 확보
            temp_zip_path = BASE_DIR / "temp_restore.zip"
            logger.info(f"선택한 백업 파일 다운로드 중... ({file_name})")
            
            request = self.service.files().get_media(fileId=file_id)
            with open(temp_zip_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        sys.stdout.write(f"\r다운로드 진행률: {int(status.progress() * 100)}%")
                        sys.stdout.flush()
            print() # 진행률 퍼센트 뒤 줄바꿈

            # 기존 데이터 백업 로직
            backup_pre_restore = DATA_DIR / "couchdb_backup_pre_restore"
            if backup_pre_restore.exists():
                logger.info("기존에 있던 couchdb_backup_pre_restore 폴더를 지웁니다...")
                shutil.rmtree(backup_pre_restore)
            
            if COUCHDB_DATA.exists():
                logger.info("기존 데이터를 couchdb_backup_pre_restore 폴더로 이동합니다...")
                shutil.move(str(COUCHDB_DATA), str(backup_pre_restore))
            
            # 압축 해제
            logger.info("다운로드된 백업 데이터를 로컬 경로로 압축 해제합니다...")
            COUCHDB_DATA.mkdir(parents=True, exist_ok=True)
            shutil.unpack_archive(str(temp_zip_path), extract_dir=str(COUCHDB_DATA), format="zip")

            # 임시 파일 정리
            try:
                os.remove(temp_zip_path)
            except OSError:
                pass
                
            logger.info("🎉 데이터 복구가 성공적으로 완료되었습니다.")
            
            # 도커 재시작
            if auto_docker:
                logger.info("도커 컨테이너 시작 중 (docker compose up -d couchdb)...")
                subprocess.run(["docker", "compose", "up", "-d", "couchdb"], cwd=BASE_DIR, check=False)

            notifier.success("Restore 완료", f"데이터 복구가 성공적으로 완료되었습니다.\n**복구 파일명:** `{file_name}`")

        except KeyboardInterrupt:
            logger.info("\n복구 작업이 취소되었습니다.")
            return
        except Exception as e:
            logger.error(f"복원 중 에러 발생: {e}", exc_info=True)
            notifier.error("Restore 실패", f"에러가 발생하여 복구에 실패했습니다.\n`{e}`")
