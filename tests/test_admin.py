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


class TestBanMiddleware:
    @pytest.fixture
    async def db_path(self, tmp_path, monkeypatch):
        path = str(tmp_path / "ban_test.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user, ban_user

        await init_db()
        await add_user(
            user_id=200,
            username="banned",
            age=20,
            name="Banned",
            gender="male",
            looking_for="female",
            goal="relationship",
            interests=["Аниме"],
        )
        await ban_user(200)
        return path

    async def test_banned_message_is_blocked(self, db_path):
        from aiogram.types import Message
        from middlewares.ban import BanMiddleware

        middleware = BanMiddleware()
        event = MagicMock(spec=Message)
        event.from_user = MagicMock(id=200)
        event.answer = AsyncMock()
        handler = AsyncMock()
        result = await middleware(handler, event, {})
        assert result is None
        event.answer.assert_awaited_once_with("Аккаунт заблокирован.")
        handler.assert_not_awaited()

    async def test_owner_bypasses_ban(self, db_path, monkeypatch):
        monkeypatch.setattr("middlewares.ban.OWNER_ID", 200)
        from aiogram.types import Message
        from middlewares.ban import BanMiddleware

        middleware = BanMiddleware()
        event = MagicMock(spec=Message)
        event.from_user = MagicMock(id=200)
        event.answer = AsyncMock()
        handler = AsyncMock(return_value="ok")
        result = await middleware(handler, event, {})
        assert result == "ok"


class TestWebBanGuard:
    async def test_banned_user_gets_403_on_me(self, aiohttp_client, tmp_path, monkeypatch):
        path = str(tmp_path / "ban_web.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user, ban_user

        await init_db()
        await add_user(
            user_id=600,
            username="banned",
            age=20,
            name="Banned",
            gender="male",
            looking_for="female",
            goal="relationship",
            interests=["Аниме"],
        )
        await ban_user(600)
        from tests.test_web_auth import _make_init_data

        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        from web_app import create_app

        app = create_app()
        cli = await aiohttp_client(app)
        init_data = _make_init_data(600, "test_token_12345")
        resp = await cli.get("/api/me", headers={"X-Init-Data": init_data})
        assert resp.status == 403


class TestAdminCommand:
    def test_admin_denied_for_regular_user(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        from handlers.admin import cmd_admin

        msg = _make_message(111)
        state = MagicMock()
        state.clear = AsyncMock()
        asyncio.run(cmd_admin(msg, state))
        msg.answer.assert_awaited_once_with("Нет доступа.")

    def test_admin_opens_menu_for_owner(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        from handlers.admin import cmd_admin

        msg = _make_message(8241460494)
        state = MagicMock()
        state.clear = AsyncMock()
        asyncio.run(cmd_admin(msg, state))
        args, kwargs = msg.answer.await_args
        assert "Админ-панель" in args[0]
        assert "reply_markup" in kwargs


class TestAdminUserLookup:
    async def test_lookup_by_user_id(self, tmp_path, monkeypatch):
        path = str(tmp_path / "lookup.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user

        await init_db()
        await add_user(
            user_id=300,
            username="alice",
            age=22,
            name="Alice",
            gender="female",
            looking_for="male",
            goal="relationship",
            interests=["Аниме", "Кино"],
            city="Москва",
        )

        from handlers.admin import admin_user_lookup

        msg = _make_message(8241460494)
        msg.text = "300"
        state = MagicMock()
        state.clear = AsyncMock()
        await admin_user_lookup(msg, state)
        args, _ = msg.answer.await_args
        assert "Alice" in args[0]


class TestAdminActions:
    async def test_ban_button_bans_user(self, tmp_path, monkeypatch):
        path = str(tmp_path / "actions.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user, is_banned

        await init_db()
        await add_user(
            user_id=400,
            username="victim",
            age=20,
            name="Victim",
            gender="male",
            looking_for="female",
            goal="relationship",
            interests=["Аниме"],
        )

        from handlers.admin import admin_ban_toggle

        cb = _make_callback(8241460494, "admin:ban:400:1")
        state = MagicMock()
        await admin_ban_toggle(cb, state)
        assert await is_banned(400) is True
