import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_message(user_id: int):
    msg = MagicMock()
    msg.from_user = MagicMock(id=user_id)
    msg.answer = AsyncMock()
    return msg


def _make_callback(user_id: int, data: str):
    cb = MagicMock()
    cb.from_user = MagicMock(id=user_id)
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


class TestIsAdmin:
    def test_owner_is_admin(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        from services.admin import is_admin

        assert is_admin(8241460494) is True

    def test_regular_user_is_not_admin(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        from services.admin import is_admin

        assert is_admin(111) is False

    def test_none_is_not_admin(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        from services.admin import is_admin

        assert is_admin(None) is False
