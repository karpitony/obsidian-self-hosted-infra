"""
CouchDB 데이터베이스 초기화 모듈

필수 시스템 DB 및 앱 DB를 생성한다.
"""

import requests
from .config import COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB_URL
from .logger import setup_logger

logger = setup_logger(__name__)


class DatabaseInitializer:
    """CouchDB 데이터베이스 초기화 클래스"""

    # 생성할 데이터베이스 목록
    DATABASES = ["_users", "_replicator", "_global_changes", "obsidian"]

    def __init__(self):
        """config에서 CouchDB 접속 정보를 로드한다."""
        if not isinstance(COUCHDB_USER, str) or not isinstance(COUCHDB_PASSWORD, str):
            raise EnvironmentError(
                "❌ .env 파일에 COUCHDB_USER 또는 COUCHDB_PASSWORD 설정이 누락되었습니다."
            )
        self.auth = (COUCHDB_USER, COUCHDB_PASSWORD)

    def create_db(self, db_name: str) -> bool:
        """
        단일 데이터베이스를 생성한다.

        Args:
            db_name: 생성할 데이터베이스 이름

        Returns:
            생성 성공 여부
        """
        logger.info(f"'{db_name}' 생성 중...")
        try:
            response = requests.put(
                f"{COUCHDB_URL}/{db_name}",
                auth=self.auth,
                timeout=5,
            )

            if response.status_code in [201, 202]:
                logger.info(f"  ✅ '{db_name}' 생성 성공!")
                return True
            elif response.status_code == 412:
                logger.info(f"  ⚠️ '{db_name}' 이미 존재함.")
                return True
            elif response.status_code == 401:
                logger.error("  ❌ 인증 실패: 아이디나 비밀번호를 확인하세요.")
                return False
            else:
                logger.error(
                    f"  ❌ '{db_name}' 실패: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.ConnectionError:
            logger.error("  ❌ 서버 연결 실패: CouchDB가 실행 중인지 확인하세요.")
            return False

    def run(self) -> None:
        """전체 데이터베이스 초기화를 실행한다."""
        logger.info("CouchDB 데이터베이스 초기화를 시작합니다.")

        for db_name in self.DATABASES:
            self.create_db(db_name)

        logger.info("🎉 모든 DB 초기화 작업이 완료되었습니다!")