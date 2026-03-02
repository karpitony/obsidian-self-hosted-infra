import os
import datetime
import shutil
import time
from pathlib import Path
from typing import Any, cast

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .config import (
    BASE_DIR,
    DATA_DIR,
    GDRIVE_FOLDER_ID,
    DISCORD_URL,
)
from .logger import setup_logger
from .notifier import DiscordNotifier
from .auth import GoogleDriveAuthenticator 

logger = setup_logger(__name__)
notifier = DiscordNotifier(DISCORD_URL)

DATA_TO_BACKUP = DATA_DIR / "couchdb"

class BackupManager:
    """구글 드라이브 백업 매니저"""

    def __init__(self, keep_count: int = 10):
        self.keep_count = keep_count
        self.authenticator = GoogleDriveAuthenticator(notifier)
        self.service: Any = None  # 타입 에러 방지를 위해 Any 사용

    def authenticate(self) -> None:
        """인증을 수행하고 드라이브 서비스를 빌드한다."""
        creds = self.authenticator.get_credentials()
        # static_discovery=False는 일부 환경에서 발생하는 라이브러리 경고를 줄여줍니다.
        self.service = build("drive", "v3", credentials=creds, static_discovery=False)
        logger.info("구글 드라이브 서비스가 준비되었습니다.")

    def create_archive(self) -> Path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"obsidian_db_snapshot_{timestamp}"
        zip_path = BASE_DIR / zip_name

        logger.info(f"데이터 압축 중: {zip_name}.zip")
        shutil.make_archive(str(zip_path), "zip", str(DATA_TO_BACKUP))

        full_zip_path = Path(f"{zip_path}.zip")
        return full_zip_path

    def upload(self, zip_path: Path) -> str:
        if self.service is None:
            raise RuntimeError("서비스가 초기화되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        file_metadata = {
            "name": zip_path.name,
            "parents": [GDRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(str(zip_path), resumable=True)

        logger.info("구글 드라이브 업로드 중...")
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()

        return cast(str, file.get("id"))

    def cleanup_old_backups(self) -> None:
        """구글 드라이브에서 오래된 백업 파일을 삭제한다 (최신 N개 유지)."""
        try:
            if not self.service: return
             
            query = f"'{GDRIVE_FOLDER_ID}' in parents and name contains 'obsidian_db_snapshot_' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc",
            ).execute()

            files = results.get("files", [])
            if len(files) > self.keep_count:
                for old_file in files[self.keep_count:]:
                    logger.info(f" 🗑️ 삭제: {old_file['name']}")
                    self.service.files().delete(fileId=old_file["id"]).execute()
                logger.info("정리 완료.")
        except Exception as e:
            logger.error(f"정리 중 에러: {e}")

    def _cleanup_temp_file(self, zip_path: Path) -> None:
        if not zip_path.exists(): return
        time.sleep(1)
        for i in range(3):
            try:
                os.remove(zip_path)
                logger.info("임시 파일 삭제 완료.")
                break
            except PermissionError:
                time.sleep(2)

    def run(self) -> None:
        """전체 워크플로우 실행"""
        zip_path = None
        try:
            self.authenticate()
            zip_path = self.create_archive()
            file_id = self.upload(zip_path)
            
            view_link = f"https://drive.google.com/file/d/{file_id}/view"
            notifier.success("Backup 완료", f"**파일명:** `{zip_path.name}`\n[드라이브 보기]({view_link})")
            
            self.cleanup_old_backups()
        except Exception as e:
            logger.error(f"백업 에러: {e}", exc_info=True)
            notifier.error("Backup 실패", f"에러 발생: `{e}`")
        finally:
            if zip_path:
                self._cleanup_temp_file(zip_path)