import requests
from config import COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB_URL

def create_db(db_name, auth: tuple[str, str]):
    print(f"[*] Creating {db_name}...")
    try:
        # auth 매개변수에 정확히 (str, str) 튜플이 전달됨
        response = requests.put(f"{COUCHDB_URL}/{db_name}", auth=auth, timeout=5)
        
        if response.status_code in [201, 202]:
            print(f"  ✅ {db_name} 생성 성공!")
        elif response.status_code == 412:
            print(f"  ⚠️ {db_name} 이미 존재함.")
        elif response.status_code == 401:
            print(f"  ❌ 인증 실패: 아이디나 비밀번호를 확인하세요.")
        else:
            print(f"  ❌ {db_name} 실패: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("  ❌ 서버 연결 실패: CouchDB가 실행 중인지 확인하세요.")


def main():
    # [2] 타입 가드: USER와 PASS가 모두 str인 경우에만 로직 실행
    if isinstance(COUCHDB_USER, str) and isinstance(COUCHDB_PASSWORD, str):
        credentials = (COUCHDB_USER, COUCHDB_PASSWORD)
        
        # 필수 시스템 DB 및 앱 DB 목록
        dbs = ["_users", "_replicator", "_global_changes", "obsidian"]
        for db in dbs:
            create_db(db, credentials)
            
        print("\n🎉 모든 DB 초기화 작업이 완료되었습니다!")
    else:
        print("❌ 에러: .env 파일에 COUCHDB_USER 또는 COUCHDB_PASSWORD 설정이 누락되었습니다.")

if __name__ == "__main__":
    main()