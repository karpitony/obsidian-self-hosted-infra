"""
Obsidian Infra CLI 엔트리포인트

모든 기능을 하위 명령으로 제어하는 중앙 집중형 CLI.
"""

import argparse
import sys
import traceback

from src.daemon import run_daemon
from src.logger import setup_logger
from src.clients.bot import run_bot_daemon
from src.services.usecases import run_auth, run_backup, run_init, run_restore

logger = setup_logger("cli")


def cmd_backup(args: argparse.Namespace) -> None:
    logger.info(f"백업을 시작합니다. (유지 개수: {args.count})")
    run_backup(keep_count=args.count)


def cmd_init(args: argparse.Namespace) -> None:
    logger.info("DB 초기화를 시작합니다.")
    run_init()


def cmd_restore(args: argparse.Namespace) -> None:
    logger.info("구글 드라이브로부터 데이터 복원(Restore)을 시작합니다.")
    run_restore()


def cmd_auth(args: argparse.Namespace) -> None:
    logger.info("🔐 구글 드라이브 수동 인증을 시작합니다.")
    ok = run_auth()
    if ok:
        logger.info("✅ 인증에 성공했습니다. 이제 정기 백업이 가능합니다.")
    else:
        logger.error("❌ 인증에 실패했습니다.")
        sys.exit(1)


def cmd_bot(args: argparse.Namespace) -> None:
    logger.info("🤖 디스코드 봇 데몬을 시작합니다.")
    run_bot_daemon()


def cmd_daemon(args: argparse.Namespace) -> None:
    logger.info("🧩 통합 데몬을 시작합니다. (Discord Bot + Backup Scheduler)")
    run_daemon()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="obsidian-infra",
        description="🛠️ Obsidian Infra 관리 도구",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        title="명령어",
        description="사용 가능한 하위 명령",
    )

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

    init_parser = subparsers.add_parser(
        "init",
        help="CouchDB 데이터베이스 초기화",
    )
    init_parser.set_defaults(func=cmd_init)

    restore_parser = subparsers.add_parser(
        "restore",
        help="구글 드라이브에서 백업 데이터를 내려받아 로컬 DB를 복구",
    )
    restore_parser.set_defaults(func=cmd_restore)

    auth_parser = subparsers.add_parser(
        "auth",
        help="구글 드라이브 인증 (token.json 생성)",
    )
    auth_parser.set_defaults(func=cmd_auth)

    bot_parser = subparsers.add_parser(
        "bot",
        help="디스코드 봇 데몬 실행",
    )
    bot_parser.set_defaults(func=cmd_bot)

    daemon_parser = subparsers.add_parser(
        "daemon",
        help="통합 데몬 실행 (봇 + 정시 백업)",
    )
    daemon_parser.set_defaults(func=cmd_daemon)

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
