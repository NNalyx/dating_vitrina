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


class TestAdminDatabase:
    @pytest.fixture
    async def db_path(self, tmp_path, monkeypatch):
        path = str(tmp_path / "admin_test.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db

        await init_db()
        return path

    async def test_ban_and_unban_user(self, db_path):
        from database import add_user, ban_user, is_banned, unban_user

        await add_user(
            user_id=100,
            username="test",
            age=20,
            name="Test",
            gender="male",
            looking_for="female",
            goal="relationship",
            interests=["Аниме"],
        )
        assert await is_banned(100) is False
        await ban_user(100)
        assert await is_banned(100) is True
        await unban_user(100)
        assert await is_banned(100) is False

    async def test_interests_seeded_from_config(self, db_path):
        from database import get_interests_from_db

        categories = await get_interests_from_db()
        assert len(categories) > 0
        assert all("items" in c and c["items"] for c in categories)
