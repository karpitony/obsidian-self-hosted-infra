#!/bin/bash

# [1] 경로 및 변수 설정
PROJECT_DIR=$(pwd)
MAIN_SCRIPT="$PROJECT_DIR/cli.py"
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


# [5] DB 초기화 스크립트 실행 (cli.py CLI 사용)
if [ -f "$MAIN_SCRIPT" ]; then
    echo "[*] 시스템 데이터베이스 초기화 중..."
    $UV_PATH  run "$MAIN_SCRIPT" init
else
    echo "⚠️  cli.py를 찾을 수 없어 건너뜁니다."
fi


# [6] 기존 Cron 제거 (통합 데몬으로 전환)
if crontab -l 2>/dev/null | grep -Eq "main.py backup|cli.py backup"; then
    echo "[*] 기존 Cron 백업 작업을 제거합니다..."
    crontab -l 2>/dev/null | grep -Ev "main.py backup|cli.py backup" | crontab -
fi

# [7] systemd 서비스 등록 (자동 시작 + 자동 재시작)
SERVICE_NAME="obsidian-infra"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

if command -v systemctl &> /dev/null; then
    echo "[*] systemd 서비스 파일 생성 중..."
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Obsidian Infra Unified Daemon
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_PATH run $MAIN_SCRIPT daemon
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    echo "[*] systemd 리로드 및 서비스 활성화..."
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$SERVICE_NAME"

    echo "✅ 서비스 활성화 완료: $SERVICE_NAME"
    echo "🔍 상태 확인: sudo systemctl status $SERVICE_NAME"
    echo "📂 로그 확인: sudo journalctl -u $SERVICE_NAME -f"
else
    echo "⚠️ systemctl을 찾지 못해 자동 시작 등록을 건너뜁니다."
    echo "수동 실행: $UV_PATH run $MAIN_SCRIPT daemon"
fi

echo "✨ 모든 인프라 세팅이 완료되었습니다!"
echo "🔍 CouchDB 상태 확인: docker ps"