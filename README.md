

## 📄 `README.md`

# 📔 Obsidian Self-hosted Infra

CouchDB와 Docker를 이용한 옵시디언 실시간 동기화 및 구글 드라이브 자동 백업 시스템입니다.

## 📂 프로젝트 구조
- `configs/`: API 키, 토큰, `.env`, `local.ini` 등 모든 설정 파일
- `data/`: CouchDB 데이터, 로그, 옵시디언 Vault (Git 제외)
- `scripts/`: 인프라 세팅 및 백업 실행 스크립트
- `docker-compose.yml`: CouchDB 컨테이너 정의



## 🚀 빠른 시작 (Quick Start)

### 1. 인프라 초기화
폴더 구조를 생성하고 `.gitkeep` 및 `.env` 템플릿을 세팅합니다.
```bash
uv run scripts/setup.py
```

### 2. 환경 설정

* `configs/.env`: DB 계정 및 구글 드라이브 폴더 ID 입력
* `configs/client_secrets.json`: 구글 클라우드 콘솔에서 받은 OAuth JSON 배치

### 3. 서버 실행

```bash
docker compose up -d
```



## 🔍 서버 상태 체크 (Health Check)

서버가 정상적으로 떴는지 확인하려면 터미널에서 아래 명령어를 입력하세요.

**1. API 응답 확인**

```bash
# .env에 적은 계정 정보를 사용하세요
curl -u admin:password http://localhost:5984
```

> `{"couchdb":"Welcome","version":"3.3.3" ...}` 메시지가 나오면 성공!

**2. 관리자 페이지 접속**
브라우저에서 `http://localhost:5984/_utils/` (Fauxton 인터페이스)에 접속하여 로그인되는지 확인합니다.



## 💾 백업 실행 (Manual Backup)

현재 데이터를 압축하여 구글 드라이브로 즉시 업로드합니다.

```bash
uv run scripts/backup.py

```

*최초 실행 시 브라우저 인증창이 뜨며, 인증 후 `configs/token.json`이 생성됩니다.*



## 📱 옵시디언 앱 설정 (Self-hosted LiveSync)

플러그인 설정창에 아래 정보를 입력하세요.

* **Remote Type:** CouchDB
* **URI:** `http://[서버-IP]:5984`
* **Username/Password:** `.env`에 설정한 값
* **Database:** `obsidian` (Check 버튼 눌러서 생성)





### `docker-compose` 로그 확인법

만약 서버가 안 뜨거나 옵시디언에서 접속이 안 된다면 이 명령어로 로그를 바로 확인해 보세요.
```bash
docker-compose logs -f obsidian_db
```
