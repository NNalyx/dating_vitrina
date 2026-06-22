import hmac
import json
import urllib.parse
from hashlib import sha256

from config import BOT_TOKEN


def _constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def validate_init_data(init_data: str) -> int | None:
    """Validate Telegram WebApp initData and return user_id or None."""
    if not init_data:
        return None

    pairs = []
    received_hash = None
    for part in init_data.split("&"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "hash":
            received_hash = value
        else:
            pairs.append((key, value))

    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs))

    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()

    if not _constant_time_compare(received_hash, expected_hash):
        return None

    user_value = None
    for k, v in pairs:
        if k == "user":
            user_value = urllib.parse.unquote(v)
            break
    if not user_value:
        return None

    try:
        user = json.loads(user_value)
        return int(user.get("id"))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
