from ..auth import GoogleDriveAuthenticator
from ..backup import BackupManager
from ..config import DISCORD_URL
from ..init_db import DatabaseInitializer
from ..notifier import DiscordNotifier
from ..restore import RestoreManager


def run_backup(keep_count: int = 10) -> bool:
    manager = BackupManager(keep_count=keep_count)
    manager.run()
    return True


def run_init() -> bool:
    initializer = DatabaseInitializer()
    initializer.run()
    return True


def run_restore() -> bool:
    manager = RestoreManager()
    manager.run()
    return True


def run_auth() -> bool:
    notifier = DiscordNotifier(DISCORD_URL)
    authenticator = GoogleDriveAuthenticator(notifier)
    creds = authenticator.get_credentials()
    return bool(creds and creds.valid)
