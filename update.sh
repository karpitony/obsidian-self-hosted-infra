#!/bin/bash

set -euo pipefail

PROJECT_DIR=$(pwd)
SERVICE_NAME="obsidian-infra"
HAS_GIT=0
CHANGED_FILES=""
SHOULD_SYNC=0
SHOULD_RESTART=0
UNIT_EXISTS=0
SETUP_SCRIPT="$PROJECT_DIR/setup.sh"
UNIT_FILE="/etc/systemd/system/$SERVICE_NAME.service"

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
if [ "$HAS_GIT" -eq 1 ] && [ -n "$CHANGED_FILES" ]; then
    if echo "$CHANGED_FILES" | grep -Eq '(^|/)(pyproject.toml|uv.lock)$'; then
        SHOULD_SYNC=1
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

# [4] systemd 유닛 존재 여부 확인
if command -v systemctl &> /dev/null; then
    if [ -f "$UNIT_FILE" ]; then
        UNIT_EXISTS=1
    else
        echo "[*] $SERVICE_NAME.service 유닛 파일이 없어 setup.sh를 먼저 실행합니다."
        if [ -f "$SETUP_SCRIPT" ]; then
            chmod +x "$SETUP_SCRIPT"
            bash "$SETUP_SCRIPT"
            exit 0
        fi
        echo "⚠️ setup.sh를 찾을 수 없습니다. 먼저 1회 ./setup.sh 를 실행해 서비스 등록을 완료해 주세요."
        exit 1
    fi
fi

# [5] 서비스 반영 (항상 재기동)
if [ "$UNIT_EXISTS" -eq 1 ]; then
    echo "[*] $SERVICE_NAME 서비스 반영 (daemon-reload + restart)"
    sudo systemctl daemon-reload
    sudo systemctl restart "$SERVICE_NAME"
    sudo systemctl status "$SERVICE_NAME" --no-pager
else
    echo "⚠️ systemctl을 찾지 못했습니다. 수동 재실행이 필요합니다."
fi

echo "✅ 업데이트 완료"
