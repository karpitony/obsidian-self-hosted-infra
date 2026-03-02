"""
디스코드 웹훅 알림 모듈

Discord Embed 형식으로 info, success, warning, error 알림을 전송한다.
웹훅 URL이 설정되지 않은 경우 알림을 스킵한다.
"""

import datetime
import requests
from .logger import setup_logger

logger = setup_logger(__name__)


class DiscordNotifier:
    """디스코드 웹훅을 통한 알림 전송 클래스"""

    # Embed 색상 상수
    COLOR_INFO = 0x3498DB      # 파란색
    COLOR_SUCCESS = 0x2ECC71   # 초록색
    COLOR_WARNING = 0xF39C12   # 노란색
    COLOR_ERROR = 0xE74C3C     # 빨간색

    def __init__(self, webhook_url: str | None):
        """
        Args:
            webhook_url: 디스코드 웹훅 URL (None이면 알림 비활성화)
        """
        self.webhook_url = webhook_url
        if not webhook_url:
            logger.warning("디스코드 웹훅 URL이 설정되지 않았습니다. 알림이 비활성화됩니다.")

    def _send(self, title: str, message: str, color: int) -> None:
        """
        Discord Embed를 전송하는 내부 공통 메서드.

        Args:
            title: Embed 제목
            message: Embed 본문
            color: Embed 색상 (hex)
        """
        if not self.webhook_url:
            return

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "footer": {"text": "Karpitony's Infra Bot"},
            }]
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"디스코드 알림 전송 실패: {e}")

    def info(self, title: str, message: str) -> None:
        """정보성 알림 (파란색)"""
        self._send(f"ℹ️ {title}", message, self.COLOR_INFO)

    def success(self, title: str, message: str) -> None:
        """성공 알림 (초록색)"""
        self._send(f"✅ {title}", message, self.COLOR_SUCCESS)

    def warning(self, title: str, message: str) -> None:
        """경고 알림 (노란색)"""
        self._send(f"⚠️ {title}", message, self.COLOR_WARNING)

    def error(self, title: str, message: str) -> None:
        """에러 알림 (빨간색)"""
        self._send(f"🚨 {title}", message, self.COLOR_ERROR)
