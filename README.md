# 📔 Obsidian Self-hosted Infra 

CouchDB와 Docker를 이용한 옵시디언 실시간 동기화 및 **자동화된 구글 드라이브 백업** 시스템입니다.

## 📂 프로젝트 구조

* `main.py`: 프로젝트 전체 제어를 위한 중앙 CLI 엔트리포인트
* `configs/`: `.env`, `client_secrets.json`, `token.json` 등 보안/설정 파일
* `data/`: CouchDB 데이터 저장소 및 실행 로그 (`logs/`)
* `scripts/`: 백업, 인증, DB 초기화 등 핵심 로직 모듈
* `docker-compose.yml`: CouchDB 컨테이너 정의

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 설정

`configs/.env` 파일을 생성하고 아래 항목들을 입력합니다.

* `COUCHDB_USER / PASSWORD`: DB 계정 설정
* `GDRIVE_FOLDER_ID`: 백업 파일이 저장될 구글 드라이브 폴더 ID
* `SERVER_IP / PORT`: 테일스케일 IP 및 포트 (8080 권장)
* `GDRIVE_REDIRECT_URI`: `http://127.0.0.1:8080/` (고정)

### 2. 원클릭 인프라 가동

아래 스크립트를 실행하면 **uv 설치, 도커 가동, DB 초기화, 크론잡 등록**까지 한 번에 완료됩니다.

```bash
chmod +x setup.sh
./setup.sh
```

### 3. 최초 구글 인증

백업을 위해 구글 권한을 획득해야 합니다.

```bash
uv run main.py auth
```

* 디스코드 알림의 링크를 클릭하여 인증을 완료하세요.
* **iOS 유저:** `127.0.0.1` 에러 페이지가 뜨면 주소창 URL을 복사해 인증 페이지 하단 입력창에 붙여넣으세요.

---

## 🛠️ CLI 사용법 (main.py)

모든 기능은 `main.py`를 통해 실행됩니다.

| 명령어 | 설명 | 비고 |
| --- | --- | --- |
| `uv run main.py backup` | 즉시 백업 실행 | `--count 10` 옵션으로 유지 개수 조절 가능 |
| `uv run main.py auth` | 구글 드라이브 인증 | `token.json` 갱신 시 사용 |
| `uv run main.py init` | CouchDB 초기화 | 기본 시스템 DB 및 `obsidian` DB 생성 |

---

## ⏰ 자동 백업 스케줄 (Crontab)

시스템은 **매일 00:00, 12:00**에 자동으로 백업을 시도합니다.

* **상태 확인:** `crontab -l`
* **로그 확인:** `tail -f data/logs/cron.log`

---

## 📱 옵시디언 앱 설정 (Self-hosted LiveSync)

옵시디언 **Self-hosted LiveSync** 플러그인에서 아래와 같이 설정하세요.

* **Remote Type:** `CouchDB`
* **URI:** `http://[테일스케일-IP]:5984`
* **Username/Password:** `.env`에 설정한 값
* **Database:** `obsidian`

---

## 🔍 문제 해결 (Troubleshooting)

**1. 인증 타임아웃이 발생했어요**
새벽에 인증 알림을 놓치면 보안을 위해 2시간 뒤 프로세스가 종료됩니다. 아침에 일어나서 `uv run main.py auth`를 한 번 실행해 주면 됩니다.

**2. 서버가 응답하지 않아요**
컨테이너 로그를 확인하여 CouchDB 상태를 점검하세요.

```bash
docker compose logs -f obsidian_db
```

**3. 리디렉션 오류 (redirect_uri_mismatch)**
구글 콘솔에 등록된 URI와 `.env`의 `GDRIVE_REDIRECT_URI`가 일치하는지 확인하세요. (끝에 `/` 포함 여부 필수 체크)

---

### 💡 Tip

백업 성공/실패 여부는 설정된 디스코드 웹훅으로 실시간 전송됩니다. 폰에 디스코드 알림을 켜두시면 편리합니다.
