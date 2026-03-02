"""
중앙 집중형 로깅 모듈

모든 모듈에서 공통으로 사용하는 로거를 제공한다.
- 콘솔: INFO 레벨, 간결한 포맷
- 파일: RotatingFileHandler (5MB, 3개 유지)
"""

import logging
from logging.handlers import RotatingFileHandler
from .config import LOG_DIR, LOG_FILE


def setup_logger(name: str) -> logging.Logger:
    """
    지정된 이름의 로거를 생성하고 핸들러를 설정한다.

    Args:
        name: 로거 이름 (보통 모듈명)

    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정된 경우 중복 추가 방지
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- 콘솔 핸들러 (INFO 이상) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_format)

    # --- 파일 핸들러 (DEBUG 이상, 5MB, 최대 3개 유지) ---
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
