from telegram_webapp_auth.auth import TelegramAuthenticator, generate_secret_key
from telegram_webapp_auth.data import WebAppUser
from telegram_webapp_auth.errors import InvalidInitDataError

from config import BOT_TOKEN


def _bot_id() -> int | None:
    """Return the numeric bot ID from the bot token, or None if not parseable."""
    try:
        return int(BOT_TOKEN.split(":", 1)[0])
    except (ValueError, IndexError):
        return None


def _authenticator() -> TelegramAuthenticator:
    """Return an authenticator configured with the current bot token."""
    return TelegramAuthenticator(generate_secret_key(BOT_TOKEN))


def _has_signature(init_data: str) -> bool:
    """Return True if initData contains an Ed25519 signature field."""
    for part in init_data.split("&"):
        if part.startswith("signature="):
            return True
    return False


def validate_init_data(init_data: str) -> int | None:
    """Validate Telegram WebApp initData and return the user_id or None.

    Supports both legacy HMAC-SHA256 ``hash`` signatures (signed with the bot
    token) and newer Ed25519 ``signature`` signatures (signed by Telegram).
    """
    user = get_init_data_user(init_data)
    if user is None:
        return None
    return int(user.id)


def get_init_data_user(init_data: str) -> WebAppUser | None:
    """Validate initData and return the Telegram user object, or None."""
    if not init_data:
        return None

    authenticator = _authenticator()

    try:
        web_app_data = authenticator.validate(init_data)
        return web_app_data.user
    except InvalidInitDataError:
        pass

    if _has_signature(init_data):
        bot_id = _bot_id()
        if bot_id is not None:
            try:
                web_app_data = authenticator.validate_third_party(init_data, bot_id)
                return web_app_data.user
            except InvalidInitDataError:
                pass

    return None
