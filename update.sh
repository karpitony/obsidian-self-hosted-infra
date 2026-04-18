#!/bin/bash

set -euo pipefail

PROJECT_DIR=$(pwd)
SERVICE_NAME="obsidian-infra"
HAS_GIT=0
CHANGED_FILES=""
SHOULD_SYNC=0
SHOULD_RESTART=0

echo "🚀 업데이트를 시작합니다..."

# [1] 최신 코드 반영
if [ -d "$PROJECT_DIR/.git" ]; then
    HAS_GIT=1
    PREV_REV=$(git rev-parse HEAD)
    echo "[*] git pull 실행"
    git pull --ff-only
    NEW_REV=$(git rev-parse HEAD)

    if [ "$PREV_REV" != "$NEW_REV" ]; then
        CHANGED_FILES=$(git diff --name-only "$PREV_REV" "$NEW_REV")
        echo "[*] 변경 파일 감지:"
        echo "$CHANGED_FILES"
    else
        echo "[*] 원격에 새로운 커밋이 없습니다."
    fi
fi

# [2] 변경 내용에 따라 동작 결정
if [ "$HAS_GIT" -eq 0 ] || [ -z "$CHANGED_FILES" ]; then
    # git 저장소가 아니거나 변경이 없으면 불필요한 재시작을 피함
    SHOULD_SYNC=0
    SHOULD_RESTART=0
else
    if echo "$CHANGED_FILES" | grep -Eq '(^|/)(pyproject.toml|uv.lock)$'; then
        SHOULD_SYNC=1
    fi

    if echo "$CHANGED_FILES" | grep -Eq '(^|/)(cli.py|main.py|setup.sh|update.sh|deploy.sh|src/|configs/\.env|configs/\.env.example|configs/local.ini|docker-compose.yml)'; then
        SHOULD_RESTART=1
    fi
fi

# [3] 의존성 동기화 (필요 시)
if [ "$SHOULD_SYNC" -eq 1 ]; then
    if command -v uv &> /dev/null; then
        echo "[*] 의존성 변경 감지: uv sync 실행"
        uv sync
    else
        echo "❌ uv 명령을 찾을 수 없습니다. 먼저 setup.sh를 실행해 주세요."
        exit 1
    fi
fi

# [4] 서비스 반영 (필요 시)
if [ "$SHOULD_RESTART" -eq 1 ]; then
    if command -v systemctl &> /dev/null; then
        echo "[*] $SERVICE_NAME 서비스 반영 (daemon-reload + restart)"
        sudo systemctl daemon-reload
        sudo systemctl restart "$SERVICE_NAME"
        sudo systemctl status "$SERVICE_NAME" --no-pager
    else
        echo "⚠️ systemctl을 찾지 못했습니다. 수동 재실행이 필요합니다."
    fi
else
    echo "[*] 서비스 재시작이 필요한 변경이 없어 현재 프로세스를 유지합니다."

    if command -v systemctl &> /dev/null; then
        if ! sudo systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "[*] $SERVICE_NAME 서비스가 비활성 상태여서 시작합니다."
            sudo systemctl start "$SERVICE_NAME"
            sudo systemctl status "$SERVICE_NAME" --no-pager
        fi
    fi
fi

echo "✅ 업데이트 완료"
