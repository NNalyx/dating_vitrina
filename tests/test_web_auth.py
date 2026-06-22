import urllib.parse

import pytest

from services.init_data import validate_init_data


def _make_init_data(user_id: int, bot_token: str) -> str:
    """Build a valid Telegram initData string for tests."""
    from hmac import HMAC
    from hashlib import sha256

    user = urllib.parse.quote(f'{{"id":{user_id},"first_name":"Test"}}')
    pairs = [
        ("auth_date", "1690000000"),
        ("query_id", "test_query_id"),
        ("user", user),
    ]
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs))
    secret_key = HMAC(b"WebAppData", bot_token.encode(), sha256).digest()
    hash_value = HMAC(secret_key, data_check_string.encode(), sha256).hexdigest()
    pairs.append(("hash", hash_value))
    return "&".join(f"{k}={v}" for k, v in pairs)


class TestValidateInitData:
    def test_valid_init_data_returns_user_id(self, monkeypatch):
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        init_data = _make_init_data(123456, "test_token_12345")
        result = validate_init_data(init_data)
        assert result == 123456

    def test_invalid_hash_returns_none(self, monkeypatch):
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        result = validate_init_data("user=%7B%22id%22%3A123%7D&hash=wrong")
        assert result is None

    def test_missing_user_returns_none(self, monkeypatch):
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        from hmac import HMAC
        from hashlib import sha256

        pairs = [("auth_date", "1690000000")]
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs))
        secret_key = HMAC(b"WebAppData", b"test_token_12345", sha256).digest()
        hash_value = HMAC(secret_key, data_check_string.encode(), sha256).hexdigest()
        init_data = f"auth_date=1690000000&hash={hash_value}"
        result = validate_init_data(init_data)
        assert result is None
