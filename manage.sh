#!/bin/bash

# [1] 경로 및 변수 설정
PROJECT_DIR=$(pwd)
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup.py"
INIT_SCRIPT="$PROJECT_DIR/scripts/init_db.py"
LOG_FILE="$PROJECT_DIR/data/logs/setup.log"

echo "🚀 Obsidian Infra 관리 시스템을 시작합니다..."


# [2] uv 설치 확인 및 자동 설치
if ! command -v uv &> /dev/null; then
    echo "[*] uv를 찾을 수 없습니다. 설치를 시작합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # 설치 직후 현재 스크립트 세션에서 uv를 즉시 사용할 수 있도록 설정
    # 설치 경로가 /root/.local/bin 이므로 해당 경로를 PATH에 추가합니다.
    export PATH="$HOME/.local/bin:$PATH"
    
    # 만약 uv 환경 설정 파일이 있다면 로드
    [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
    
    echo "✅ uv 설치 및 경로 반영 완료."
else
    echo "✅ uv가 이미 설치되어 있습니다."
fi


# [3] Docker Compose 실행
echo "[*] Docker 컨테이너 실행 중..."
docker compose up -d


# [4] CouchDB 준비 대기 (Health Check)
echo "[*] CouchDB 응답 대기 중 (최대 30초)..."
MAX_RETRIES=15
COUNT=0
until curl -s http://localhost:5984 > /dev/null || [ $COUNT -eq $MAX_RETRIES ]; do
    # 401 Unauthorized가 떠도 프로세스가 살아있으면 통과됨
    sleep 2
    ((COUNT++))
done


# [5] DB 초기화 스크립트 실행
if [ -f "$INIT_SCRIPT" ]; then
    echo "[*] 시스템 데이터베이스 초기화 중..."
    uv run "$INIT_SCRIPT"
else
    echo "⚠️  init_db.py를 찾을 수 없어 건너뜁니다."
fi


# [6] Cron 백업 등록 (매일 새벽 3시)
# 이미 등록되어 있는지 확인 후 추가
UV_BIN=$(command -v uv)
CRON_JOB="0 3 * * * cd $PROJECT_DIR && uv run $BACKUP_SCRIPT >> $PROJECT_DIR/data/logs/backup.log 2>&1"

(crontab -l 2>/dev/null | grep -Fq "$BACKUP_SCRIPT") || (
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ 새벽 3시 백업 작업이 Crontab에 등록되었습니다."
)

echo "✨ 모든 인프라 세팅이 완료되었습니다!"
echo "🔍 상태 확인: docker ps"
echo "📂 로그 확인: tail -f data/logs/setup.log"