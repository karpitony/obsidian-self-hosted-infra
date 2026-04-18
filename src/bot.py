import asyncio

import discord
from discord import app_commands

from .config import ALLOWED_USER_ID, DISCORD_BOT_TOKEN
from .logger import setup_logger
from .usecases import run_auth, run_backup

logger = setup_logger(__name__)


def parse_allowed_user_id() -> int:
	if not ALLOWED_USER_ID:
		raise RuntimeError("ALLOWED_USER_ID가 설정되지 않았습니다. configs/.env를 확인해 주세요.")

	try:
		return int(ALLOWED_USER_ID)
	except ValueError as exc:
		raise RuntimeError("ALLOWED_USER_ID는 숫자(Discord User ID)여야 합니다.") from exc


class InfraBot(discord.Client):
	def __init__(self, allowed_user_id: int):
		intents = discord.Intents.default()
		super().__init__(intents=intents)
		self.allowed_user_id = allowed_user_id
		self.tree = app_commands.CommandTree(self)

		@self.tree.command(name="status", description="봇 상태 확인")
		async def status(interaction: discord.Interaction) -> None:
			if interaction.user.id != self.allowed_user_id:
				return
			await interaction.response.send_message("✅ 봇이 정상 동작 중입니다.")

		@self.tree.command(name="auth", description="구글 드라이브 인증 프로세스 실행")
		@app_commands.describe(force="true면 기존 토큰을 무시하고 인증 링크를 강제로 재발송합니다")
		async def auth(interaction: discord.Interaction, force: bool = False) -> None:
			if interaction.user.id != self.allowed_user_id:
				return

			await interaction.response.send_message("🔐 인증 프로세스를 시작합니다. 잠시만 기다려 주세요.")
			try:
				ok = await asyncio.to_thread(run_auth, force)
			except Exception as e:
				logger.error(f"auth 명령 실패: {e}")
				await interaction.followup.send("❌ 인증 명령 실행 중 오류가 발생했습니다. 서버 로그를 확인해 주세요.")
				return

			if ok:
				if force:
					await interaction.followup.send("✅ 강제 재인증 요청이 처리되었습니다. 웹훅 인증 링크를 확인해 주세요.")
				else:
					await interaction.followup.send("✅ 인증 상태를 확인했습니다. 기존 토큰이 유효하면 웹훅 링크는 발송되지 않습니다.")
			else:
				await interaction.followup.send("❌ 인증에 실패했습니다. 서버 로그를 확인해 주세요.")

		@self.tree.command(name="backup", description="즉시 백업 실행")
		async def backup(interaction: discord.Interaction) -> None:
			if interaction.user.id != self.allowed_user_id:
				return

			await interaction.response.send_message("💾 백업 프로세스를 시작합니다. 잠시만 기다려 주세요.")
			try:
				ok = await asyncio.to_thread(run_backup)
			except Exception as e:
				logger.error(f"backup 명령 실패: {e}")
				await interaction.followup.send("❌ 백업 명령 실행 중 오류가 발생했습니다. 서버 로그를 확인해 주세요.")
				return

			if ok:
				await interaction.followup.send("✅ 백업 명령이 정상 완료되었습니다.")
			else:
				await interaction.followup.send("❌ 백업에 실패했습니다. 서버 로그를 확인해 주세요.")

	async def on_ready(self) -> None:
		await self.tree.sync()
		logger.info(f"디스코드 봇 로그인 완료: {self.user}")


def run_bot_daemon() -> None:
	if not DISCORD_BOT_TOKEN:
		raise RuntimeError("DISCORD_BOT_TOKEN이 설정되지 않았습니다. configs/.env를 확인해 주세요.")

	allowed_user_id = parse_allowed_user_id()
	bot = InfraBot(allowed_user_id=allowed_user_id)
	bot.run(DISCORD_BOT_TOKEN)


def create_bot() -> InfraBot:
	"""환경 변수 기반으로 InfraBot 인스턴스를 생성한다."""
	allowed_user_id = parse_allowed_user_id()
	return InfraBot(allowed_user_id=allowed_user_id)


async def start_bot_daemon() -> None:
	"""단일 이벤트 루프에 통합 가능한 비동기 시작 함수."""
	if not DISCORD_BOT_TOKEN:
		raise RuntimeError("DISCORD_BOT_TOKEN이 설정되지 않았습니다. configs/.env를 확인해 주세요.")

	bot = create_bot()
	await bot.start(DISCORD_BOT_TOKEN)
