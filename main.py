"""Backward-compatible CLI entrypoint.

권장 실행은 cli.py를 사용하고, 기존 main.py 경로도 계속 지원합니다.
"""

from cli import main


if __name__ == "__main__":
    main()
