import os
import datetime
import shutil
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv


# 설정 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# OAuth 2.0 관련 파일
CLIENT_SECRETS_FILE = Path(__file__).parent / "client_secrets.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

PARENT_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")
DATA_TO_BACKUP = BASE_DIR / "data" / "couchdb"


def get_gdrive_service():
    creds = None
    # 이전에 생성된 토큰이 있는지 확인
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    # 인증이 필요하거나 유효하지 않은 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        # 토큰 저장
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)


def run_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"obsidian_db_snapshot_{timestamp}"
    zip_path = BASE_DIR / zip_name

    try:
        service = get_gdrive_service()
        
        print(f"[*] 데이터 압축 중: {zip_name}.zip")
        shutil.make_archive(str(zip_path), 'zip', str(DATA_TO_BACKUP))

        file_metadata = {'name': f"{zip_name}.zip", 'parents': [PARENT_FOLDER_ID]}
        media = MediaFileUpload(f"{zip_path}.zip", resumable=True)
        
        print(f"[*] 사용자 계정 용량으로 업로드 중...")
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"[+] 업로드 완료! ID: {file.get('id')}")
        del media 
        
    except Exception as e:
        print(f"[!] 백업 실패: {e}")
        
    finally:
        # 가끔 del 만으로 부족할 때를 대비해 잠시 대기하거나 예외 처리
        full_zip_path = Path(f"{zip_path}.zip")
        if full_zip_path.exists():
            try:
                os.remove(full_zip_path)
                print("[*] 임시 파일 삭제 완료.")
            except PermissionError:
                import time
                time.sleep(1) # 1초 대기 후 재시도
                try:
                    os.remove(full_zip_path)
                    print("[*] 임시 파일 삭제 완료 (재시도 성공).")
                except Exception as final_e:
                    print(f"[!] 임시 파일 삭제 실패 (나중에 수동 삭제 필요): {final_e}")


if __name__ == "__main__":
    run_backup()