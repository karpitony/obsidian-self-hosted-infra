import os
from pathlib import Path
from dotenv import load_dotenv

# [1] 경로 설정
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_DIR = BASE_DIR / "configs"
DATA_DIR = BASE_DIR / "data"

# [2] .env 로드
load_dotenv(CONFIG_DIR / ".env")


# [3] 환경 변수 및 타입 가드
def get_env_or_raise(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise EnvironmentError(f"❌ .env 파일에 '{key}' 설정이 누락되었습니다.")
    return value


# [4] 공통 상수들
COUCHDB_USER = get_env_or_raise("COUCHDB_USER")
COUCHDB_PASSWORD = get_env_or_raise("COUCHDB_PASSWORD")
GDRIVE_FOLDER_ID = get_env_or_raise("GDRIVE_FOLDER_ID")
COUCHDB_URL = get_env_or_raise("COUCHDB_URL")

CLIENT_SECRETS_FILE = CONFIG_DIR / "client_secrets.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
COUCHDB_DATA = DATA_DIR / "couchdb"

DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL") # 필수가 아닐 수도 있으니 get_env 대신 사용