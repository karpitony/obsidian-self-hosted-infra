import os
import datetime
import shutil
import time
import requests
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from config import (
    BASE_DIR,
    DATA_DIR,
    TOKEN_FILE,
    CLIENT_SECRETS_FILE,
    GDRIVE_FOLDER_ID,
    DISCORD_URL
)


SCOPES = ['https://www.googleapis.com/auth/drive.file']
DATA_TO_BACKUP = DATA_DIR / "couchdb"
BACKUP_KEEP_COUNT = 10  # 구글 드라이브에 유지할 백업 파일 개수


def send_notification(content, is_success=True):
    """디스코드 웹훅으로 상태 알림 전송"""
    if not DISCORD_URL: return
    
    color = 0x2ECC71 if is_success else 0xE74C3C  # 초록색 / 빨간색
    status_emoji = "✅" if is_success else "🚨"
    
    payload = {
        "embeds": [{
            "title": f"{status_emoji} Obsidian Backup Report",
            "description": content,
            "color": color,
            "timestamp": datetime.datetime.now().isoformat(),
            "footer": {"text": "Karpitony's Infra Bot"}
        }]
    }
    try:
        requests.post(DISCORD_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"알림 전송 실패: {e}")


def get_gdrive_service():
    """구글 드라이브 서비스 인증 및 객체 생성"""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS_FILE.exists():
                raise FileNotFoundError(f"❌ {CLIENT_SECRETS_FILE} 파일이 없습니다!")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)


def cleanup_old_backups(service):
    """구글 드라이브에서 오래된 백업 파일 삭제 (최신 N개 유지)"""
    try:
        print(f"[*] 오래된 백업 정리 중 (유지 개수: {BACKUP_KEEP_COUNT})...")
        query = f"'{GDRIVE_FOLDER_ID}' in parents and name contains 'obsidian_db_snapshot_' and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        files = results.get('files', [])
        if len(files) > BACKUP_KEEP_COUNT:
            for old_file in files[BACKUP_KEEP_COUNT:]:
                print(f"  🗑️  삭제 대상: {old_file['name']} ({old_file['id']})")
                service.files().delete(fileId=old_file['id']).execute()
            print(f"[+] 정리 완료.")
        else:
            print("[*] 삭제할 오래된 백업이 없습니다.")
    
    except Exception as e:
        # 정리 실패 시 별도 알림 전송
        error_msg = f"백업 업로드는 성공했으나, **오래된 파일 정리 중 에러**가 발생했습니다.\n**Error:** `{str(e)}`"
        send_notification(error_msg, is_success=False)
        print(f"[!] 정리 에러 발생: {e}")


def run_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"obsidian_db_snapshot_{timestamp}"
    zip_path = BASE_DIR / zip_name  # 루트 폴더에 임시 생성
    full_zip_path = Path(f"{str(zip_path)}.zip")

    try:
        # 1. 인증 및 서비스 준비
        service = get_gdrive_service()
        
        # 2. 압축
        print(f"[*] 데이터 압축 중: {full_zip_path.name}")
        shutil.make_archive(str(zip_path), 'zip', str(DATA_TO_BACKUP))

        # 3. 업로드
        file_metadata = {'name': full_zip_path.name, 'parents': [GDRIVE_FOLDER_ID]}
        media = MediaFileUpload(str(full_zip_path), resumable=True)
        print(f"[*] 구글 드라이브 업로드 중...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        # 구글 드라이브 바로가기 링크 생성
        view_link = f"https://drive.google.com/file/d/{file_id}/view"
        
        del media  # 리소스 해제
        
        # 성공 알림
        notification_msg = (
            f"백업이 성공적으로 완료되었습니다.\n"
            f"**파일명:** `{full_zip_path.name}`\n"
            f"**링크:** [구글 드라이브에서 보기]({view_link})"
        )
        send_notification(notification_msg)
        print(f"[+] 업로드 완료! ID: {file_id}")
        
        # 4. 오래된 파일 정리
        cleanup_old_backups(service)
        
    except Exception as e:
        send_notification(f"백업 도중 에러가 발생했습니다.\n**Error:** `{str(e)}`", is_success=False)
        print(f"[!] 백업 에러 발생: {e}")
        
    finally:
        # 5. 임시 파일 삭제 (Windows PermissionError 방어 로직)
        if full_zip_path.exists():
            time.sleep(1)  # 시스템이 핸들을 완전히 놓을 때까지 잠시 대기
            for i in range(3):  # 최대 3번 시도
                try:
                    os.remove(full_zip_path)
                    print("[*] 임시 파일 삭제 완료.")
                    break
                except PermissionError:
                    if i < 2:
                        print(f"[*] 파일이 아직 사용 중입니다. 재시도 중... ({i+1}/3)")
                        time.sleep(2)
                    else:
                        print(f"[!] 임시 파일 삭제 실패: {full_zip_path}를 수동으로 지워주세요.")


if __name__ == "__main__":
    run_backup()