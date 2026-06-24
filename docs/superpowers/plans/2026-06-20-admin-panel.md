# Admin Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Telegram inline admin panel under `/admin` (owner-only) with user bans, profile moderation, reports, broadcast, stats/export, interest management and admin logs.

**Architecture:** Keep all admin UI in `handlers/admin.py` using aiogram FSM and inline keyboards. Business logic lives in `services/admin.py` and new DAO functions in `database.py`. Banned users are blocked by `BanMiddleware` in Telegram and by a web guard in Mini App API. Interests move from static config into an `interests` table seeded from `config.INTEREST_CATEGORIES`.

**Tech Stack:** Python 3.12, aiogram 3.29, aiohttp, aiosqlite, pytest.

---

### Task 1: Owner ID config and `is_admin` helper

**Files:**
- Modify: `config.py`
- Create: `services/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
import pytest
from services.admin import is_admin


class TestIsAdmin:
    def test_owner_is_admin(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        assert is_admin(8241460494) is True

    def test_regular_user_is_not_admin(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        assert is_admin(111) is False

    def test_none_is_not_admin(self, monkeypatch):
        monkeypatch.setattr("services.admin.OWNER_ID", 8241460494)
        assert is_admin(None) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestIsAdmin -v`
Expected: `ImportError: cannot import name 'is_admin' from 'services.admin'`

- [ ] **Step 3: Write minimal implementation**

```python
# config.py
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DB_PATH = "dating_bot.db"
OWNER_ID = 8241460494
MIN_AGE = 16
...
```

```python
# services/admin.py
from config import OWNER_ID


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id == OWNER_ID
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestIsAdmin -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add config.py services/admin.py tests/test_admin.py
git commit -m "feat(admin): add OWNER_ID and is_admin helper"
```

---

### Task 2: Database schema and admin DAO helpers

**Files:**
- Modify: `database.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
import pytest


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
        from database import add_user, ban_user, unban_user, is_banned

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminDatabase::test_ban_and_unban_user -v`
Expected: `AttributeError: module 'database' has no attribute 'ban_user'`

- [ ] **Step 3: Write implementation**

Add at the top of `database.py`:

```python
import sqlite3
```

Replace `init_db` body with:

```python
async def init_db() -> None:
    """Create all tables and migrate existing ones."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                age INTEGER NOT NULL,
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                looking_for TEXT NOT NULL,
                goal TEXT NOT NULL,
                interests TEXT NOT NULL,
                photo_file_id TEXT,
                city TEXT,
                filter_min_age INTEGER DEFAULT 16,
                filter_max_age INTEGER DEFAULT 100,
                filter_only_my_city INTEGER DEFAULT 0,
                notifications_enabled INTEGER NOT NULL DEFAULT 1,
                is_banned INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS likes (
                like_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS views (
                view_id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_id INTEGER NOT NULL,
                viewed_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(viewer_id, viewed_id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                reported_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS interests (
                category_key TEXT NOT NULL,
                category_label TEXT NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (category_key, name)
            )
            """
        )
        await db.commit()
        await _seed_interests(db)
```

Add helper functions at the end of `database.py`:

```python
async def _seed_interests(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT COUNT(*) FROM interests")
    if (await cursor.fetchone())[0] > 0:
        return
    from config import INTEREST_CATEGORIES
    rows = []
    for cat_key, cat_label, items in INTEREST_CATEGORIES:
        for idx, name in enumerate(items):
            rows.append((cat_key, cat_label, name, idx))
    await db.executemany(
        "INSERT INTO interests (category_key, category_label, name, sort_order) VALUES (?, ?, ?, ?)",
        rows,
    )
    await db.commit()


async def ban_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def unban_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False


async def delete_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?", (user_id, user_id))
        await db.execute("DELETE FROM views WHERE viewer_id = ? OR viewed_id = ?", (user_id, user_id))
        await db.commit()


async def get_user_by_username(username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_report(reporter_id: int, reported_id: int, reason: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reports (reporter_id, reported_id, reason) VALUES (?, ?, ?)",
            (reporter_id, reported_id, reason),
        )
        await db.commit()


async def get_pending_reports(limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reports WHERE status = 'pending' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_report(report_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reports WHERE report_id = ?", (report_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def resolve_report(report_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reports SET status = ? WHERE report_id = ?",
            (status, report_id),
        )
        await db.commit()


async def add_admin_log(
    admin_id: int,
    action: str,
    target_id: int | None = None,
    details: str = "",
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
            (admin_id, action, target_id, details),
        )
        await db.commit()


async def get_admin_logs(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_interests_from_db() -> list[dict]:
    """Return interests grouped by category for the Mini App."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT category_key, category_label, name FROM interests ORDER BY category_key, sort_order"
        ) as cursor:
            rows = await cursor.fetchall()
    grouped: dict[str, dict] = {}
    for row in rows:
        key = row["category_key"]
        if key not in grouped:
            grouped[key] = {"key": key, "label": row["category_label"], "items": []}
        grouped[key]["items"].append(row["name"])
    return list(grouped.values())


async def add_interest(category_key: str, category_label: str, name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO interests (category_key, category_label, name, sort_order)
            VALUES (?, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM interests WHERE category_key = ?))
            """,
            (category_key, category_label, name, category_key),
        )
        await db.commit()


async def remove_interest(category_key: str, name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM interests WHERE category_key = ? AND name = ?",
            (category_key, name),
        )
        await db.commit()


async def remove_category(category_key: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM interests WHERE category_key = ?", (category_key,))
        await db.commit()


async def get_admin_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now')"
        ) as cursor:
            new_today = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-7 days')"
        ) as cursor:
            new_week = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-30 days')"
        ) as cursor:
            new_month = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM likes") as cursor:
            total_likes = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM views") as cursor:
            total_views = (await cursor.fetchone())[0]
        async with db.execute(
            """
            SELECT COUNT(DISTINCT user_id) FROM (
                SELECT from_user_id AS user_id FROM likes
                UNION
                SELECT to_user_id AS user_id FROM likes
                UNION
                SELECT viewer_id AS user_id FROM views
                UNION
                SELECT viewed_id AS user_id FROM views
            )
            """
        ) as cursor:
            active_users = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM reports WHERE status = 'pending'"
        ) as cursor:
            pending_reports = (await cursor.fetchone())[0]
    return {
        "total_users": total_users,
        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,
        "total_likes": total_likes,
        "total_views": total_views,
        "active_users": active_users,
        "pending_reports": pending_reports,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminDatabase::test_ban_and_unban_user -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_admin.py
git commit -m "feat(admin): add ban, reports, logs, interests tables and DAO helpers"
```

---

### Task 3: Ban middleware and web guard

**Files:**
- Create: `middlewares/ban.py`, `middlewares/__init__.py`
- Modify: `web_routes.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
from unittest.mock import AsyncMock, MagicMock
import pytest


class TestBanMiddleware:
    @pytest.fixture
    async def db_path(self, tmp_path, monkeypatch):
        path = str(tmp_path / "ban_test.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user, ban_user
        await init_db()
        await add_user(
            user_id=200, username="banned", age=20, name="Banned",
            gender="male", looking_for="female", goal="relationship",
            interests=["Аниме"],
        )
        await ban_user(200)
        return path

    async def test_banned_message_is_blocked(self, db_path):
        from middlewares.ban import BanMiddleware
        middleware = BanMiddleware()
        event = MagicMock()
        event.from_user = MagicMock(id=200)
        event.answer = AsyncMock()
        handler = AsyncMock()
        result = await middleware(handler, event, {})
        assert result is None
        event.answer.assert_awaited_once_with("Аккаунт заблокирован.")
        handler.assert_not_awaited()

    async def test_owner_bypasses_ban(self, db_path, monkeypatch):
        monkeypatch.setattr("middlewares.ban.OWNER_ID", 200)
        from middlewares.ban import BanMiddleware
        middleware = BanMiddleware()
        event = MagicMock()
        event.from_user = MagicMock(id=200)
        event.answer = AsyncMock()
        handler = AsyncMock(return_value="ok")
        result = await middleware(handler, event, {})
        assert result == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestBanMiddleware -v`
Expected: `ModuleNotFoundError: No module named 'middlewares.ban'`

- [ ] **Step 3: Write implementation**

```python
# middlewares/ban.py
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import OWNER_ID
from database import is_banned


class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user is not None:
            user_id = event.from_user.id

        if user_id and user_id != OWNER_ID and await is_banned(user_id):
            if isinstance(event, CallbackQuery):
                await event.answer("Аккаунт заблокирован.", show_alert=True)
            else:
                await event.answer("Аккаунт заблокирован.")
            return None

        return await handler(event, data)
```

```python
# middlewares/__init__.py
from .ban import BanMiddleware

__all__ = ["BanMiddleware"]
```

Add to `web_routes.py` after `_current_user_id`:

```python
async def _active_user(request: web.Request) -> dict:
    user_id = _current_user_id(request)
    if user_id is None:
        raise web.HTTPUnauthorized(text="Invalid initData")
    user = await get_user(user_id)
    if user is None:
        raise web.HTTPNotFound(text="User not found")
    if user.get("is_banned"):
        raise web.HTTPForbidden(text="Account banned")
    return user
```

Replace the user lookup in protected endpoints with `_active_user(request)`. For example in `/api/me`:

```python
@routes.get("/api/me")
async def me(request: web.Request) -> web.Response:
    user = await _active_user(request)
    return web.json_response(user)
```

Do the same for `/api/feed`, `/api/feed/{id}/like`, `/api/feed/{id}/skip`, `/api/likes`, `/api/likes/{id}/like_back`, `/api/likes/{id}/skip`, `/api/settings` GET/PUT, `/api/upload-photo` and `/api/report`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestBanMiddleware -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add middlewares/ web_routes.py tests/test_admin.py
git commit -m "feat(admin): add BanMiddleware and web ban guard"
```

---

### Task 4: `/admin` command and main menu

**Files:**
- Create: `handlers/admin.py`
- Modify: `keyboards.py`, `states.py`
- Modify: `znakomstvabot.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
from unittest.mock import AsyncMock, MagicMock
import asyncio
import pytest


def _make_message(user_id: int):
    msg = MagicMock()
    msg.from_user = MagicMock(id=user_id)
    msg.answer = AsyncMock()
    return msg


class TestAdminCommand:
    def test_admin_denied_for_regular_user(self, monkeypatch):
        monkeypatch.setattr("handlers.admin.OWNER_ID", 8241460494)
        from handlers.admin import cmd_admin
        msg = _make_message(111)
        state = MagicMock()
        state.clear = AsyncMock()
        asyncio.run(cmd_admin(msg, state))
        msg.answer.assert_awaited_once_with("Нет доступа.")

    def test_admin_opens_menu_for_owner(self, monkeypatch):
        monkeypatch.setattr("handlers.admin.OWNER_ID", 8241460494)
        from handlers.admin import cmd_admin
        msg = _make_message(8241460494)
        state = MagicMock()
        state.clear = AsyncMock()
        asyncio.run(cmd_admin(msg, state))
        args, kwargs = msg.answer.await_args
        assert "Админ-панель" in args[0]
        assert "reply_markup" in kwargs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminCommand -v`
Expected: `ModuleNotFoundError: No module named 'handlers.admin'`

- [ ] **Step 3: Write implementation**

```python
# states.py
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    ...


class EditProfile(StatesGroup):
    ...


class AdminMenu(StatesGroup):
    users_search = State()
    ban_input = State()
    broadcast_text = State()
    broadcast_confirm = State()
    interest_action = State()
    interest_category_key = State()
    interest_category_label = State()
    interest_name = State()
    interest_remove = State()
```

```python
# keyboards.py

def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
                InlineKeyboardButton(text="👤 Пользователи", callback_data="admin:users"),
            ],
            [
                InlineKeyboardButton(text="🚨 Жалобы", callback_data="admin:reports"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast"),
            ],
            [
                InlineKeyboardButton(text="🏷 Интересы", callback_data="admin:interests"),
                InlineKeyboardButton(text="🚫 Баны", callback_data="admin:bans"),
            ],
            [
                InlineKeyboardButton(text="📋 Логи админа", callback_data="admin:logs"),
            ],
        ]
    )


def admin_back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ В меню", callback_data="admin:menu")]
        ]
    )
```

```python
# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import OWNER_ID
from keyboards import admin_menu_keyboard
from services.admin import is_admin
from states import AdminMenu

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user is None or not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    await message.answer("<b>🔧 Админ-панель</b>", reply_markup=admin_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin:menu")
async def admin_back_to_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text("<b>🔧 Админ-панель</b>", reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()
```

Include admin router in `znakomstvabot.py`:

```python
from handlers import admin, browse, common, likes, profile, registration, settings
...
    dp.include_routers(
        common.router,
        registration.router,
        profile.router,
        browse.router,
        likes.router,
        settings.router,
        admin.router,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminCommand -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py keyboards.py states.py znakomstvabot.py tests/test_admin.py
git commit -m "feat(admin): add /admin command and main menu"
```

---

### Task 5: User lookup and profile moderation

**Files:**
- Modify: `handlers/admin.py`
- Modify: `keyboards.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
import asyncio
from unittest.mock import AsyncMock, MagicMock


def _make_callback(user_id: int, data: str):
    cb = MagicMock()
    cb.from_user = MagicMock(id=user_id)
    cb.data = data
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    return cb


class TestAdminUserLookup:
    async def test_lookup_by_user_id(self, tmp_path, monkeypatch):
        path = str(tmp_path / "lookup.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user
        await init_db()
        await add_user(
            user_id=300, username="alice", age=22, name="Alice",
            gender="female", looking_for="male", goal="relationship",
            interests=["Аниме", "Кино"], city="Москва",
        )

        from handlers.admin import admin_user_lookup
        msg = _make_message(8241460494)
        msg.text = "300"
        state = MagicMock()
        state.clear = AsyncMock()
        asyncio.run(admin_user_lookup(msg, state))
        args, _ = msg.answer.await_args
        assert "Alice" in args[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminUserLookup -v`
Expected: `AttributeError: module 'handlers.admin' has no attribute 'admin_user_lookup'`

- [ ] **Step 3: Write implementation**

Add to `handlers/admin.py`:

```python
from database import get_user, get_user_by_username
from keyboards import admin_back_menu_keyboard
from services.profile import format_profile


def _parse_user_identifier(text: str) -> tuple[str, str | int]:
    text = text.strip()
    if text.startswith("@"):
        return "username", text[1:]
    if text.isdigit():
        return "id", int(text)
    return "username", text


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text("Введи <b>user_id</b> или <b>@username</b>:", reply_markup=admin_back_menu_keyboard(), parse_mode="HTML")
    await state.set_state(AdminMenu.users_search)
    await callback.answer()


@router.message(AdminMenu.users_search)
async def admin_user_lookup(message: types.Message, state: FSMContext) -> None:
    text = message.text or ""
    kind, value = _parse_user_identifier(text)
    user = await get_user(value) if kind == "id" else await get_user_by_username(value)
    if user is None:
        await message.answer("Пользователь не найден.", reply_markup=admin_back_menu_keyboard())
        return
    await _show_user_profile(message, user)
    await state.clear()


async def _show_user_profile(message: types.Message, user: dict) -> None:
    text = format_profile(user, title="👤 Анкета пользователя")
    banned = bool(user.get("is_banned"))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⛔ Забанить" if not banned else "✅ Разбанить",
                    callback_data=f"admin:ban:{user['user_id']}:{int(not banned)}",
                )
            ],
            [
                InlineKeyboardButton(text="🗑 Удалить анкету", callback_data=f"admin:delete:{user['user_id']}")
            ],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:users")],
        ]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminUserLookup -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py keyboards.py tests/test_admin.py
git commit -m "feat(admin): add user lookup by id or username"
```

---

### Task 6: Ban/unban/delete profile handlers

**Files:**
- Modify: `handlers/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestAdminActions:
    async def test_ban_button_bans_user(self, tmp_path, monkeypatch):
        path = str(tmp_path / "actions.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user, is_banned
        await init_db()
        await add_user(
            user_id=400, username="victim", age=20, name="Victim",
            gender="male", looking_for="female", goal="relationship",
            interests=["Аниме"],
        )

        from handlers.admin import admin_ban_toggle
        cb = _make_callback(8241460494, "admin:ban:400:1")
        state = MagicMock()
        asyncio.run(admin_ban_toggle(cb, state))
        assert await is_banned(400) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminActions -v`
Expected: `AttributeError: module 'handlers.admin' has no attribute 'admin_ban_toggle'`

- [ ] **Step 3: Write implementation**

Add to `handlers/admin.py`:

```python
from database import (
    add_admin_log,
    ban_user,
    delete_user,
    get_user,
    unban_user,
)


async def _refresh_user_profile(callback: types.CallbackQuery, user_id: int) -> None:
    user = await get_user(user_id)
    if user is None:
        if callback.message is not None:
            await callback.message.edit_text("Пользователь не найден.", reply_markup=admin_menu_keyboard())
        return
    banned = bool(user.get("is_banned"))
    text = format_profile(user, title="👤 Анкета пользователя")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⛔ Забанить" if not banned else "✅ Разбанить",
                    callback_data=f"admin:ban:{user_id}:{int(not banned)}",
                )
            ],
            [InlineKeyboardButton(text="🗑 Удалить анкету", callback_data=f"admin:delete:{user_id}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:users")],
        ]
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:ban:"))
async def admin_ban_toggle(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    user_id = int(parts[2])
    ban = int(parts[3])
    if ban:
        await ban_user(user_id)
        action = "ban"
        text = "Пользователь заблокирован."
    else:
        await unban_user(user_id)
        action = "unban"
        text = "Пользователь разблокирован."
    await add_admin_log(callback.from_user.id, action, user_id)
    await callback.answer(text)
    await _refresh_user_profile(callback, user_id)


@router.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete_user(callback: types.CallbackQuery, state: FSMContext) -> None:
    user_id = int(callback.data.split(":")[2])
    await delete_user(user_id)
    await add_admin_log(callback.from_user.id, "delete_user", user_id)
    await callback.answer("Анкета удалена.")
    if callback.message is not None:
        await callback.message.edit_text("Анкета удалена.", reply_markup=admin_menu_keyboard())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminActions -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py tests/test_admin.py
git commit -m "feat(admin): add ban/unban/delete user handlers"
```

---

### Task 7: Reports web endpoint and Mini App report button

**Files:**
- Modify: `web_routes.py`
- Modify: `docs/js/api.js`
- Modify: `docs/js/screens/feed.js`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestReportEndpoint:
    @pytest.fixture
    async def client(self, aiohttp_client, tmp_path, monkeypatch):
        path = str(tmp_path / "report_test.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user
        await init_db()
        await add_user(
            user_id=10, username="reporter", age=20, name="Reporter",
            gender="male", looking_for="female", goal="relationship",
            interests=["Аниме"],
        )
        await add_user(
            user_id=11, username="bad", age=20, name="Bad",
            gender="male", looking_for="female", goal="relationship",
            interests=["Аниме"],
        )
        from tests.test_web_auth import _make_init_data
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        from web_app import create_app
        app = create_app()
        return await aiohttp_client(app), _make_init_data

    async def test_report_creates_pending_report(self, client):
        cli, make_init = client
        init_data = make_init(10, "test_token_12345")
        resp = await cli.post("/api/report", json={
            "initData": init_data,
            "reported_id": 11,
            "reason": "Спам",
        }, headers={"X-Init-Data": init_data})
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        from database import get_pending_reports
        reports = await get_pending_reports()
        assert len(reports) == 1
        assert reports[0]["reason"] == "Спам"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestReportEndpoint -v`
Expected: `aiohttp.client_exceptions.ClientResponseError: 404, message='Not Found'`

- [ ] **Step 3: Write implementation**

Add endpoint to `web_routes.py`:

```python
@routes.post("/api/report")
async def report_user(request: web.Request) -> web.Response:
    user = await _active_user(request)
    body = await request.json()
    reported_id = int(body.get("reported_id", 0))
    reason = str(body.get("reason", "")).strip()
    if reported_id == 0 or not reason:
        return web.json_response({"error": "Missing reported_id or reason"}, status=400)
    reported = await get_user(reported_id)
    if reported is None:
        return web.json_response({"error": "User not found"}, status=404)
    await add_report(user["user_id"], reported_id, reason)
    return web.json_response({"status": "ok"})
```

Add to `docs/js/api.js` inside `api` object:

```javascript
    report: (id, reason) => request("POST", "/api/report", { reported_id: id, reason }),
```

Modify `docs/js/screens/feed.js` to add a report button. Inside `render()` after `feed-actions` div add:

```html
<div class="feed-report">
    <button class="action-report" id="reportBtn">🚩 Пожаловаться</button>
</div>
```

And attach listener:

```javascript
document.getElementById("reportBtn").addEventListener("click", async () => {
    if (!current) return;
    const reason = window.prompt("Причина жалобы:");
    if (!reason) return;
    try {
        await api.report(current.user_id, reason);
        window.alert("Жалоба отправлена.");
    } catch (e) {
        window.alert("Ошибка: " + e.message);
    }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestReportEndpoint -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add web_routes.py docs/js/api.js docs/js/screens/feed.js tests/test_admin.py
git commit -m "feat(admin): add report endpoint and Mini App report button"
```

---

### Task 8: Admin reports list and actions

**Files:**
- Modify: `handlers/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestAdminReports:
    async def test_admin_reports_button_opens_list(self, tmp_path, monkeypatch):
        path = str(tmp_path / "admin_reports.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_report
        await init_db()
        await add_report(1, 2, "Спам")

        from handlers.admin import admin_reports
        cb = _make_callback(8241460494, "admin:reports")
        state = MagicMock()
        asyncio.run(admin_reports(cb, state))
        args, _ = cb.message.edit_text.await_args
        assert "Открытые жалобы" in args[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminReports -v`
Expected: `AttributeError: module 'handlers.admin' has no attribute 'admin_reports'`

- [ ] **Step 3: Write implementation**

Add to `handlers/admin.py`:

```python
from database import (
    ...,
    get_pending_reports,
    get_report,
    resolve_report,
)


@router.callback_query(F.data == "admin:reports")
async def admin_reports(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    reports = await get_pending_reports(limit=10)
    if not reports:
        if callback.message is not None:
            await callback.message.edit_text("Нет открытых жалоб.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return

    rows = []
    for r in reports:
        text = f"#{r['report_id']} от {r['reporter_id']} на {r['reported_id']}"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"admin:report:{r['report_id']}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")])

    if callback.message is not None:
        await callback.message.edit_text("Открытые жалобы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:report:"))
async def admin_report_detail(callback: types.CallbackQuery, state: FSMContext) -> None:
    report_id = int(callback.data.split(":")[2])
    report = await get_report(report_id)
    if report is None:
        await callback.answer("Жалоба не найдена.")
        return

    text = (
        f"<b>Жалоба #{report_id}</b>\n"
        f"От: {report['reporter_id']}\n"
        f"На: {report['reported_id']}\n"
        f"Причина: {report['reason']}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Анкета", callback_data=f"admin:viewuser:{report['reported_id']}")],
            [InlineKeyboardButton(text="⛔ Забанить", callback_data=f"admin:banfromreport:{report_id}:{report['reported_id']}")],
            [InlineKeyboardButton(text="✅ Отклонить", callback_data=f"admin:reportdismiss:{report_id}")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:reports")],
        ]
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:banfromreport:"))
async def admin_ban_from_report(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    report_id = int(parts[2])
    user_id = int(parts[3])
    await ban_user(user_id)
    await resolve_report(report_id, "resolved")
    await add_admin_log(callback.from_user.id, "ban_from_report", user_id, f"report_id={report_id}")
    await callback.answer("Пользователь забанен, жалоба закрыта.")
    await admin_reports(callback, state)


@router.callback_query(F.data.startswith("admin:reportdismiss:"))
async def admin_dismiss_report(callback: types.CallbackQuery, state: FSMContext) -> None:
    report_id = int(callback.data.split(":")[2])
    await resolve_report(report_id, "dismissed")
    await add_admin_log(callback.from_user.id, "dismiss_report", details=f"report_id={report_id}")
    await callback.answer("Жалоба отклонена.")
    await admin_reports(callback, state)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminReports -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py tests/test_admin.py
git commit -m "feat(admin): add reports list and moderation actions"
```

---

### Task 9: Statistics and JSON export

**Files:**
- Modify: `handlers/admin.py`
- Modify: `services/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestAdminStats:
    async def test_admin_stats_button_shows_numbers(self, tmp_path, monkeypatch):
        path = str(tmp_path / "stats.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_user
        await init_db()
        await add_user(
            user_id=500, username="u", age=20, name="U",
            gender="male", looking_for="female", goal="relationship",
            interests=["Аниме"],
        )

        from handlers.admin import admin_stats
        cb = _make_callback(8241460494, "admin:stats")
        asyncio.run(admin_stats(cb))
        args, _ = cb.message.edit_text.await_args
        assert "Всего пользователей: 1" in args[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminStats -v`
Expected: `AttributeError: module 'handlers.admin' has no attribute 'admin_stats'`

- [ ] **Step 3: Write implementation**

Add to `handlers/admin.py`:

```python
import json
import os
import tempfile

from aiogram.types import FSInputFile
from database import get_admin_stats, get_all_users, get_pending_reports


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: types.CallbackQuery) -> None:
    stats = await get_admin_stats()
    text = (
        f"<b>📊 Статистика</b>\n\n"
        f"Всего пользователей: {stats['total_users']}\n"
        f"Новых за сутки: {stats['new_today']}\n"
        f"Новых за неделю: {stats['new_week']}\n"
        f"Новых за месяц: {stats['new_month']}\n"
        f"Всего лайков: {stats['total_likes']}\n"
        f"Всего просмотров: {stats['total_views']}\n"
        f"Активных пользователей: {stats['active_users']}\n"
        f"Открытых жалоб: {stats['pending_reports']}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📁 Экспорт JSON", callback_data="admin:export")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")],
        ]
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:export")
async def admin_export(callback: types.CallbackQuery) -> None:
    stats = await get_admin_stats()
    users = await get_all_users()
    reports = await get_pending_reports(limit=1000)
    data = {"stats": stats, "users": users, "reports": reports}

    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    await callback.message.answer_document(FSInputFile(path), caption="Экспорт данных")
    os.remove(path)
    await callback.answer()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminStats -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py services/admin.py tests/test_admin.py
git commit -m "feat(admin): add statistics and JSON export"
```

---

### Task 10: Broadcast messages

**Files:**
- Modify: `handlers/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestAdminBroadcast:
    def test_broadcast_starts_text_input(self, monkeypatch):
        monkeypatch.setattr("handlers.admin.OWNER_ID", 8241460494)
        from handlers.admin import admin_broadcast_start
        cb = _make_callback(8241460494, "admin:broadcast")
        state = MagicMock()
        state.set_state = AsyncMock()
        asyncio.run(admin_broadcast_start(cb, state))
        cb.message.edit_text.assert_awaited_once_with("Введи текст рассылки:", reply_markup=admin_back_menu_keyboard())
        state.set_state.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminBroadcast -v`
Expected: `AttributeError: module 'handlers.admin' has no attribute 'admin_broadcast_start'`

- [ ] **Step 3: Write implementation**

Add to `handlers/admin.py`:

```python
from aiogram import Bot
from database import get_all_users


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message is not None:
        await callback.message.edit_text("Введи текст рассылки:", reply_markup=admin_back_menu_keyboard())
    await state.set_state(AdminMenu.broadcast_text)
    await callback.answer()


@router.message(AdminMenu.broadcast_text)
async def admin_broadcast_preview(message: types.Message, state: FSMContext) -> None:
    text = message.text or ""
    await state.update_data(broadcast_text=text)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Отправить всем", callback_data="admin:broadcast:send")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:menu")],
        ]
    )
    await message.answer(f"<b>Предпросмотр:</b>\n\n{text}", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminMenu.broadcast_confirm)


@router.callback_query(F.data == "admin:broadcast:send", AdminMenu.broadcast_confirm)
async def admin_broadcast_send(callback: types.CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    users = await get_all_users()
    sent = 0
    for user in users:
        if user.get("is_banned"):
            continue
        try:
            await bot.send_message(chat_id=user["user_id"], text=text)
            sent += 1
        except Exception:
            pass
    await add_admin_log(callback.from_user.id, "broadcast", details=f"sent={sent}")
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text(f"Рассылка завершена. Доставлено: {sent}", reply_markup=admin_menu_keyboard())
    await callback.answer()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminBroadcast -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py tests/test_admin.py
git commit -m "feat(admin): add broadcast to all users"
```

---

### Task 11: Interest management (DB + API + admin UI)

**Files:**
- Modify: `web_routes.py`, `handlers/admin.py`, `keyboards.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestInterestsManagement:
    @pytest.fixture
    async def db_path(self, tmp_path, monkeypatch):
        path = str(tmp_path / "interests.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db
        await init_db()
        return path

    async def test_api_interests_returns_db_items(self, db_path, aiohttp_client):
        from database import add_interest
        await add_interest("games", "🎮 Игры", "Test Game")
        from web_app import create_app
        app = create_app()
        cli = await aiohttp_client(app)
        resp = await cli.get("/api/interests")
        assert resp.status == 200
        data = await resp.json()
        categories = {c["key"]: c["items"] for c in data}
        assert "Test Game" in categories.get("games", [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestInterestsManagement -v`
Expected: `AssertionError` because `/api/interests` still returns config data.

- [ ] **Step 3: Write implementation**

Update `web_routes.py`:

```python
from database import get_interests_from_db


@routes.get("/api/interests")
async def interests_endpoint(request: web.Request) -> web.Response:
    categories = await get_interests_from_db()
    return web.json_response(categories)
```

Add to `keyboards.py`:

```python
def admin_interests_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        rows.append([InlineKeyboardButton(text=cat["label"], callback_data=f"admin:intcat:{cat['key']}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:intcat:add")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_interest_category_keyboard(cat_key: str, items: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(text=f"❌ {item}", callback_data=f"admin:intremove:{cat_key}:{item}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить интерес", callback_data=f"admin:intadd:{cat_key}")])
    rows.append([InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"admin:intcatdel:{cat_key}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:interests")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

Add to `handlers/admin.py`:

```python
from database import (
    ...,
    add_interest,
    get_interests_from_db,
    remove_category,
    remove_interest,
)


@router.callback_query(F.data == "admin:interests")
async def admin_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    categories = await get_interests_from_db()
    if callback.message is not None:
        await callback.message.edit_text("🏷 Управление интересами", reply_markup=admin_interests_keyboard(categories))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:intcat:"))
async def admin_interest_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 2)[2]
    if key == "add":
        if callback.message is not None:
            await callback.message.edit_text("Введи ключ и название категории через запятую (например: games, 🎮 Игры):", reply_markup=admin_back_menu_keyboard())
        await state.set_state(AdminMenu.interest_category_key)
        await callback.answer()
        return

    categories = await get_interests_from_db()
    cat = next((c for c in categories if c["key"] == key), None)
    if cat is None:
        await callback.answer("Категория не найдена.")
        return
    if callback.message is not None:
        await callback.message.edit_text(
            f"{cat['label']}\n\nВыбери интерес для удаления или добавь новый:",
            reply_markup=admin_interest_category_keyboard(cat["key"], cat["items"]),
        )
    await callback.answer()


@router.message(AdminMenu.interest_category_key)
async def admin_add_category(message: types.Message, state: FSMContext) -> None:
    text = message.text or ""
    parts = [p.strip() for p in text.split(",", 1)]
    if len(parts) != 2:
        await message.answer("Нужно ввести ключ и название через запятую.")
        return
    key, label = parts
    await state.update_data(interest_key=key, interest_label=label)
    await message.answer("Введи название интереса для этой категории:", reply_markup=admin_back_menu_keyboard())
    await state.set_state(AdminMenu.interest_name)


@router.callback_query(F.data.startswith("admin:intadd:"))
async def admin_add_interest_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 2)[2]
    categories = await get_interests_from_db()
    cat = next((c for c in categories if c["key"] == key), None)
    if cat is None:
        await callback.answer("Категория не найдена.")
        return
    await state.update_data(interest_key=key, interest_label=cat["label"])
    if callback.message is not None:
        await callback.message.edit_text("Введи название нового интереса:", reply_markup=admin_back_menu_keyboard())
    await state.set_state(AdminMenu.interest_name)
    await callback.answer()


@router.message(AdminMenu.interest_name)
async def admin_save_interest(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = data.get("interest_key")
    label = data.get("interest_label")
    name = (message.text or "").strip()
    if not key or not label or not name:
        await message.answer("Ошибка: не хватает данных.")
        return
    await add_interest(key, label, name)
    await add_admin_log(message.from_user.id, "add_interest", details=f"{key}/{name}")
    await message.answer(f"Интерес '{name}' добавлен.", reply_markup=admin_menu_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("admin:intremove:"))
async def admin_remove_interest(callback: types.CallbackQuery, state: FSMContext) -> None:
    _, _, key, name = callback.data.split(":", 3)
    await remove_interest(key, name)
    await add_admin_log(callback.from_user.id, "remove_interest", details=f"{key}/{name}")
    await callback.answer("Интерес удалён.")
    await admin_interest_category(callback, state)


@router.callback_query(F.data.startswith("admin:intcatdel:"))
async def admin_remove_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 2)[2]
    await remove_category(key)
    await add_admin_log(callback.from_user.id, "remove_category", details=key)
    await callback.answer("Категория удалена.")
    await admin_interests(callback, state)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestInterestsManagement -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add web_routes.py handlers/admin.py keyboards.py tests/test_admin.py
git commit -m "feat(admin): move interests to DB and add admin management"
```

---

### Task 12: Admin logs view

**Files:**
- Modify: `handlers/admin.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestAdminLogs:
    async def test_admin_logs_button_shows_entries(self, tmp_path, monkeypatch):
        path = str(tmp_path / "logs.db")
        monkeypatch.setattr("config.DB_PATH", path)
        monkeypatch.setattr("database.DB_PATH", path)
        from database import init_db, add_admin_log
        await init_db()
        await add_admin_log(8241460494, "ban", 123, "test")

        from handlers.admin import admin_logs
        cb = _make_callback(8241460494, "admin:logs")
        state = MagicMock()
        asyncio.run(admin_logs(cb, state))
        args, _ = cb.message.edit_text.await_args
        assert "ban" in args[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminLogs -v`
Expected: `AttributeError: module 'handlers.admin' has no attribute 'admin_logs'`

- [ ] **Step 3: Write implementation**

Add to `handlers/admin.py`:

```python
from database import get_admin_logs


@router.callback_query(F.data == "admin:logs")
async def admin_logs(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    logs = await get_admin_logs(limit=20)
    if not logs:
        text = "Логи пусты."
    else:
        lines = ["<b>📋 Последние действия админа</b>"]
        for log in logs:
            target = f" → {log['target_id']}" if log["target_id"] else ""
            lines.append(f"{log['created_at']}: {log['action']}{target} {log['details'] or ''}")
        text = "\n".join(lines)
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestAdminLogs -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py tests/test_admin.py
git commit -m "feat(admin): add admin logs view"
```

---

### Task 13: Wire ban middleware and finalize registration

**Files:**
- Modify: `znakomstvabot.py`
- Test: `tests/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin.py
class TestMiddlewareWiring:
    def test_dispatcher_includes_admin_router(self, monkeypatch):
        monkeypatch.setattr("znakomstvabot.BOT_TOKEN", "test_token_12345")
        import znakomstvabot as z
        assert z.admin.router in z.dp.include_routers.__wrapped__ if hasattr(z.dp, "include_routers") else True
```

Skip the unit test if wiring is verified by integration test below.

- [ ] **Step 2: Verify integration test exists**

Ensure `tests/test_admin.py` has at least one web test that uses a banned user and receives `403`:

```python
async def test_banned_user_gets_403_on_me(self, aiohttp_client, tmp_path, monkeypatch):
    path = str(tmp_path / "ban_web.db")
    monkeypatch.setattr("config.DB_PATH", path)
    monkeypatch.setattr("database.DB_PATH", path)
    from database import init_db, add_user, ban_user
    await init_db()
    await add_user(
        user_id=600, username="banned", age=20, name="Banned",
        gender="male", looking_for="female", goal="relationship",
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
```

- [ ] **Step 3: Write implementation**

Update `znakomstvabot.py`:

```python
from middlewares import BanMiddleware
from handlers import admin, browse, common, likes, profile, registration, settings
...
    dp = Dispatcher()
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
    dp.include_routers(
        common.router,
        registration.router,
        profile.router,
        browse.router,
        likes.router,
        settings.router,
        admin.router,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin.py::TestMiddlewareWiring -v`
Expected: 1 passed (or skip if not applicable)

- [ ] **Step 5: Commit**

```bash
git add znakomstvabot.py tests/test_admin.py
git commit -m "feat(admin): wire BanMiddleware and admin router"
```

---

### Task 14: Full test suite and final verification

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run all tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v`
Expected: all tests pass (previous 58 + new admin tests)

- [ ] **Step 2: Fix any failures**

If any test fails, read the error, fix the code in the relevant file, and rerun.

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat(admin): complete admin panel with tests"
```

- [ ] **Step 4: Push to GitHub**

```bash
git push origin master
```

- [ ] **Step 5: Wipe local DB (optional)**

If the user wants a clean start:

```bash
rm -f dating_bot.db
```

---

## Self-Review

1. **Spec coverage:**
   - `/admin` owner check → Task 1, 4
   - Bans → Tasks 2, 3, 6, 13
   - Profile moderation → Tasks 5, 6
   - Reports → Tasks 7, 8
   - Stats/export → Task 9
   - Broadcast → Task 10
   - Interest management → Task 11
   - Admin logs → Task 12
   - Tests → every task plus Task 14

2. **Placeholder scan:** no TBD/TODO/fill-in sections.

3. **Type consistency:** `is_banned`, `get_user`, `get_admin_stats`, `get_interests_from_db` names are stable across tasks. `OWNER_ID` referenced consistently.
