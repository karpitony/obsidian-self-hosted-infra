import os
import re
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
        """구글 드라이브에서 오래된 백업 파일을 삭제한다 (최신 N개, Daily 10일, Weekly 6주 유지)."""
        try:
            if not self.service: return
             
            query = f"'{GDRIVE_FOLDER_ID}' in parents and name contains 'obsidian_db_snapshot_' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc",
            ).execute()

            files = results.get("files", [])
            if not files:
                return
            
            files_with_dt = []
            for f in files:
                match = re.search(r'obsidian_db_snapshot_(\d{8}_\d{6})', f['name'])
                if match:
                    dt = datetime.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
                    files_with_dt.append((dt, f))
                else:
                    try:
                        dt_str = f['createdTime'].replace('Z', '+00:00')
                        dt = datetime.datetime.fromisoformat(dt_str).replace(tzinfo=None)
                        files_with_dt.append((dt, f))
                    except Exception:
                        pass
            
            recent_ids = set()
            sorted_by_newest = sorted(files_with_dt, key=lambda x: x[0], reverse=True)
            
            # 1. 최신 N개 유지
            for dt, f in sorted_by_newest[:self.keep_count]:
                recent_ids.add(f['id'])
                
            now = datetime.datetime.now()
            daily_groups = {}
            weekly_groups = {}
            
            keep_daily_days = 10
            keep_weekly_weeks = 6
            
            for dt, f in sorted_by_newest[self.keep_count:]:
                age_days = (now - dt).days
                
                # 2. Daily (최근 10일 이내): 하루 중 처음(오전) 백업 하나만 보관
                if age_days <= keep_daily_days:
                    date_str = dt.strftime("%Y-%m-%d")
                    if date_str not in daily_groups:
                        daily_groups[date_str] = []
                    daily_groups[date_str].append((dt, f))
                    
                # 3. Weekly (최근 6주 이내): 주차별 처음 백업 하나만 보관
                age_weeks = age_days // 7
                if age_weeks <= keep_weekly_weeks:
                    week_str = dt.strftime("%Y-%W")
                    if week_str not in weekly_groups:
                        weekly_groups[week_str] = []
                    weekly_groups[week_str].append((dt, f))
                    
            daily_ids = set()
            # Daily 그룹 중 가장 시간대가 이른 백업 하나 유지
            for date_str, group in daily_groups.items():
                group.sort(key=lambda x: x[0])
                daily_ids.add(group[0][1]['id'])
                
            weekly_ids = set()
            # Weekly 그룹 중 가장 시간대가 이른 백업 하나 유지
            for week_str, group in weekly_groups.items():
                group.sort(key=lambda x: x[0])
                weekly_ids.add(group[0][1]['id'])
            
            keep_ids = recent_ids | daily_ids | weekly_ids
            
            delete_count = 0
            for dt, f in files_with_dt:
                if f['id'] not in keep_ids:
                    logger.info(f" 🗑️ 삭제: {f['name']}")
                    self.service.files().delete(fileId=f["id"]).execute()
                    delete_count += 1
                else:
                    # 이름 태깅 (구분하기 쉽게 변경)
                    target_tag = ""
                    if f['id'] in weekly_ids:
                        target_tag = "[WEEKLY]"
                    elif f['id'] in daily_ids:
                        target_tag = "[DAILY]"
                        
                    clean_name = re.sub(r'^\[(?:WEEKLY|DAILY)\]\s*', '', f['name'])
                    expected_name = f"{target_tag} {clean_name}" if target_tag else clean_name
                    
                    if f['name'] != expected_name:
                        logger.info(f" 📝 이름 변경 (태그 업데이트): {f['name']} -> {expected_name}")
                        self.service.files().update(
                            fileId=f['id'],
                            body={'name': expected_name}
                        ).execute()
                    
            if delete_count > 0:
                logger.info(f"정리 완료: {delete_count}개의 오래된 백업을 삭제했습니다.")
            else:
                logger.info("삭제할 오래된 백업이 없습니다.")
                
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