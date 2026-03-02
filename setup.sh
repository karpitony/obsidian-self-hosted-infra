#!/bin/bash

# [1] 경로 및 변수 설정
PROJECT_DIR=$(pwd)
MAIN_SCRIPT="$PROJECT_DIR/main.py"
LOG_FILE="$PROJECT_DIR/data/logs/setup.log"

echo "🚀 Obsidian Infra 관리 시스템을 시작합니다..."


# [2] uv 설치 확인 및 자동 설치
UV_BIN="$HOME/.local/bin/uv"

if command -v uv &> /dev/null || [ -f "$UV_BIN" ]; then
    echo "✅ uv가 이미 설치되어 있습니다."
    
    # PATH에 없는데 파일만 있는 경우를 대비해 경로 추가
    if ! command -v uv &> /dev/null; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
else
    echo "[*] uv를 찾을 수 없습니다. 설치를 시작합니다..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # 설치 직후 현재 세션에서 즉시 사용 가능하도록 설정
    export PATH="$HOME/.local/bin:$PATH"
    [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
    
    # 향후 재접속 시에도 uv를 쓸 수 있게 .bashrc에 한 번만 추가
    if ! grep -q ".local/bin" ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo "[*] .bashrc에 uv 경로를 추가했습니다."
    fi
fi

UV_PATH="$HOME/.local/bin/uv"


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


# [5] DB 초기화 스크립트 실행 (main.py CLI 사용)
if [ -f "$MAIN_SCRIPT" ]; then
    echo "[*] 시스템 데이터베이스 초기화 중..."
    $UV_PATH  run "$MAIN_SCRIPT" init
else
    echo "⚠️  main.py를 찾을 수 없어 건너뜁니다."
fi


# [6] Cron 백업 등록 
# 매일 00:00, 12:00에 실행
0 0,12 * * * cd $PROJECT_DIR && $UV_PATH run $MAIN_SCRIPT backup >> $PROJECT_DIR/data/logs/cron.log 2>&1

(crontab -l 2>/dev/null | grep -Fq "$MAIN_SCRIPT") || (
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ 00:00, 12:00 백업 작업이 Crontab에 등록되었습니다."
)

echo "✨ 모든 인프라 세팅이 완료되었습니다!"
echo "🔍 상태 확인: docker ps"
echo "📂 로그 확인: tail -f data/logs/backup.log"