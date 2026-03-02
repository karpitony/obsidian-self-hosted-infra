"""
Obsidian Infra CLI 엔트리포인트

모든 기능을 하위 명령으로 제어하는 중앙 집중형 CLI.

사용법:
    python main.py backup           # 기본 백업 (최신 10개 유지)
    python main.py backup --count 5 # 최신 5개만 유지
    python main.py init             # CouchDB 데이터베이스 초기화
"""

import argparse
import sys
import traceback

from scripts.logger import setup_logger

logger = setup_logger("main")


def cmd_backup(args: argparse.Namespace) -> None:
    """backup 하위 명령 핸들러"""
    from scripts.backup import BackupManager

    logger.info(f"백업을 시작합니다. (유지 개수: {args.count})")
    manager = BackupManager(keep_count=args.count)
    manager.run()


def cmd_init(args: argparse.Namespace) -> None:
    """init 하위 명령 핸들러"""
    from scripts.init_db import DatabaseInitializer

    logger.info("DB 초기화를 시작합니다.")
    initializer = DatabaseInitializer()
    initializer.run()
    
def cmd_auth(args: argparse.Namespace) -> None:
    """auth 하위 명령 핸들러: 백업 없이 인증만 수행"""
    from scripts.auth import GoogleDriveAuthenticator
    from scripts.notifier import DiscordNotifier
    from scripts.config import DISCORD_URL

    logger.info("🔐 구글 드라이브 수동 인증을 시작합니다.")
    notifier = DiscordNotifier(DISCORD_URL)
    authenticator = GoogleDriveAuthenticator(notifier)
    
    # get_credentials를 호출하면 토큰이 없거나 만료된 경우 인증 흐름을 탐
    creds = authenticator.get_credentials()
    if creds and creds.valid:
        logger.info("✅ 인증에 성공했습니다. 이제 정기 백업이 가능합니다.")
    else:
        logger.error("❌ 인증에 실패했습니다.")


def main() -> None:
    """CLI 파서를 설정하고 하위 명령을 실행한다."""
    parser = argparse.ArgumentParser(
        prog="obsidian-infra",
        description="🛠️ Obsidian Infra 관리 도구",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        title="명령어",
        description="사용 가능한 하위 명령",
    )

    # --- backup 명령어 ---
    backup_parser = subparsers.add_parser(
        "backup",
        help="구글 드라이브로 CouchDB 데이터 백업",
    )
    backup_parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="구글 드라이브에 유지할 백업 파일 수 (기본값: 10)",
    )
    backup_parser.set_defaults(func=cmd_backup)

    # --- init 명령어 ---
    init_parser = subparsers.add_parser(
        "init",
        help="CouchDB 데이터베이스 초기화",
    )
    init_parser.set_defaults(func=cmd_init)
    
    # --- auth 명령어 ---
    auth_parser = subparsers.add_parser(
        "auth",
        help="구글 드라이브 인증 (token.json 생성)",
    )
    auth_parser.set_defaults(func=cmd_auth)

    # --- 파싱 및 실행 ---
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        logger.error(f"치명적 에러 발생: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
