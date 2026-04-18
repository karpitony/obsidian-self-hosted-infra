import asyncio
import datetime as dt

from .clients.bot import start_bot_daemon
from .logger import setup_logger
from .services.usecases import run_backup

logger = setup_logger(__name__)

SCHEDULE_HOURS = (0, 12)


def _next_backup_time(now: dt.datetime) -> dt.datetime:
    candidates = []
    for hour in SCHEDULE_HOURS:
        candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += dt.timedelta(days=1)
        candidates.append(candidate)
    return min(candidates)


async def _run_scheduled_backup() -> None:
    try:
        ok = await asyncio.to_thread(run_backup)
        if ok:
            logger.info("정시 백업 작업이 완료되었습니다.")
        else:
            logger.error("정시 백업 작업이 실패했습니다.")
    except Exception as e:
        logger.error(f"정시 백업 작업 중 예외 발생: {e}")


async def backup_scheduler_loop() -> None:
    logger.info("백업 스케줄러 루프 시작 (매일 00:00, 12:00)")

    while True:
        now = dt.datetime.now()
        target = _next_backup_time(now)
        wait_seconds = max(1, int((target - now).total_seconds()))

        logger.info(
            "다음 정시 백업 예정 시각: %s (약 %d분 후)",
            target.strftime("%Y-%m-%d %H:%M:%S"),
            wait_seconds // 60,
        )

        await asyncio.sleep(wait_seconds)
        await _run_scheduled_backup()


async def run_daemon_async() -> None:
    logger.info("통합 데몬 시작: Discord Bot + Backup Scheduler")

    backup_task = asyncio.create_task(backup_scheduler_loop(), name="backup_scheduler")
    bot_task = asyncio.create_task(start_bot_daemon(), name="discord_bot")

    done, pending = await asyncio.wait(
        {backup_task, bot_task},
        return_when=asyncio.FIRST_EXCEPTION,
    )

    for task in done:
        exc = task.exception()
        if exc:
            logger.error(f"데몬 구성요소 오류 감지: {exc}")

    for task in pending:
        task.cancel()

    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    raise RuntimeError("통합 데몬이 비정상 종료되었습니다.")


def run_daemon() -> None:
    asyncio.run(run_daemon_async())
