import os
import sys
from pathlib import Path
from dotenv import load_dotenv


# [1] 경로 설정
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_DIR = BASE_DIR / "configs"
DATA_DIR = BASE_DIR / "data"


# [2] .env 로드
ENV_PATH = CONFIG_DIR / ".env"
if not ENV_PATH.exists():
    # .env 파일 자체가 없을 경우에 대한 경고
    print(f"⚠️ 경고: {ENV_PATH} 파일을 찾을 수 없습니다.")
load_dotenv(ENV_PATH)


# [3] 환경 변수 및 타입 가드 함수
def get_env_or_raise(key: str) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise KeyError(f"❌ 설정 오류: '.env' 파일에 '{key}' 항목이 비어있거나 누락되었습니다.")
    return value


# [4] 필수 상수 (없으면 바로 에러 발생)
try:
    COUCHDB_USER = get_env_or_raise("COUCHDB_USER")
    COUCHDB_PASSWORD = get_env_or_raise("COUCHDB_PASSWORD")
    COUCHDB_URL = get_env_or_raise("COUCHDB_URL")
    GDRIVE_FOLDER_ID = get_env_or_raise("GDRIVE_FOLDER_ID")
    
    # OAuth용 설정
    GDRIVE_REDIRECT_URI = get_env_or_raise("GDRIVE_REDIRECT_URI")
    SERVER_IP = get_env_or_raise("SERVER_IP")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))

except (KeyError, ValueError) as e:
    sys.exit(f"❌ 설정 오류: SERVER_PORT는 숫자여야 합니다.\n{str(e)}")


# [5] 파일 및 디렉토리 경로
CLIENT_SECRETS_FILE = CONFIG_DIR / "client_secrets.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
COUCHDB_DATA = DATA_DIR / "couchdb"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "backup.log"

# 필요한 디렉토리가 없으면 자동 생성
LOG_DIR.mkdir(parents=True, exist_ok=True)

# [6] 선택적 상수 (기본값 제공)
DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL") # 알림은 필수가 아닐 수 있음