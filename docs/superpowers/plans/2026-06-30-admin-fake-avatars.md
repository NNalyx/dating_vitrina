# Admin Fake Avatars + Names + Age Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins upload fake profile avatars directly in the Telegram admin panel by gender, diversify fake names with nicknames, and bias fake ages toward the viewing user's age.

**Architecture:** Add a `fake_avatars` DB table to store Telegram `file_id`s by gender. Replace the file-based avatar picker in `services/fake_profile_generator.py` with a DB query. Add new admin handlers and states for a gender → upload → counter flow. Update name pools and age logic in the generator.

**Tech Stack:** Python aiogram, SQLite, pytest.

---

### File Structure

- `database.py` — new `fake_avatars` table and helpers.
- `services/fake_profile_generator.py` — DB-based avatar picker, nickname pools, age bias.
- `states.py` — new states for avatar upload.
- `keyboards.py` — keyboards for avatar gender selection and upload session.
- `handlers/admin.py` — admin handlers for avatar upload flow.
- `tests/test_fake_avatars.py` — DB helper tests.
- `tests/test_fake_generator.py` — updated generator tests.
- `tests/test_admin_fakes.py` — admin upload handler tests.

---

### Task 1: Add `fake_avatars` table and DB helpers

**Files:**
- Modify: `database.py`
- Test: `tests/test_fake_avatars.py`

- [ ] **Step 1: Create table and helpers**

In `database.py`, in `init_db()` add:

```python
await db.execute(
    """
    CREATE TABLE IF NOT EXISTS fake_avatars (
        avatar_id INTEGER PRIMARY KEY AUTOINCREMENT,
        gender TEXT NOT NULL,
        file_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)
```

Add helper functions:

```python
async def add_fake_avatar(gender: str, file_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO fake_avatars (gender, file_id) VALUES (?, ?)",
            (gender, file_id),
        )
        await db.commit()


async def get_random_fake_avatar_file_id(gender: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for g in (gender, "neutral"):
            async with db.execute(
                "SELECT file_id FROM fake_avatars WHERE gender = ? ORDER BY RANDOM() LIMIT 1",
                (g,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row["file_id"]
        async with db.execute(
            "SELECT file_id FROM fake_avatars ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return row["file_id"] if row else None


async def count_fake_avatars(gender: str | None = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        if gender:
            async with db.execute(
                "SELECT COUNT(*) FROM fake_avatars WHERE gender = ?", (gender,)
            ) as cursor:
                return (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM fake_avatars") as cursor:
            return (await cursor.fetchone())[0]
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_fake_avatars.py`:

```python
import asyncio
import os

import pytest

import database
from database import init_db, add_fake_avatar, get_random_fake_avatar_file_id, count_fake_avatars

TEST_DB = "test_fake_avatars.db"
ORIGINAL_DB_PATH = database.DB_PATH


@pytest.fixture(autouse=True)
def _db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    database.DB_PATH = TEST_DB
    asyncio.run(init_db())
    yield
    database.DB_PATH = ORIGINAL_DB_PATH
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.mark.asyncio
async def test_add_and_retrieve_avatar():
    await add_fake_avatar("male", "file_id_123")
    assert await count_fake_avatars("male") == 1
    file_id = await get_random_fake_avatar_file_id("male")
    assert file_id == "file_id_123"


@pytest.mark.asyncio
async def test_fallback_to_neutral():
    await add_fake_avatar("neutral", "neutral_id")
    assert await get_random_fake_avatar_file_id("male") == "neutral_id"


@pytest.mark.asyncio
async def test_returns_none_when_empty():
    assert await get_random_fake_avatar_file_id("female") is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_avatars.py -v`
Expected: FAIL — functions/tables missing.

- [ ] **Step 4: Implement helpers and rerun tests**

Apply the code from Step 1.

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_avatars.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_fake_avatars.py
git commit -m "feat(db): fake_avatars table and helpers"
```

---

### Task 2: Update fake profile generator

**Files:**
- Modify: `services/fake_profile_generator.py`
- Test: `tests/test_fake_generator.py`

- [ ] **Step 1: Replace avatar picker with DB helper**

Remove the JSON/file-based functions and import the new helper:

```python
from database import add_fake_user, get_user, get_random_fake_avatar_file_id

# Remove: AVATARS_DIR, FILE_IDS_PATH, _load_file_ids, and old pick_avatar_file_id.
```

Replace `pick_avatar_file_id`:

```python
async def pick_avatar_file_id(gender: str) -> str | None:
    return await get_random_fake_avatar_file_id(gender)
```

Since this is now async, update `generate_fake_profiles_batch`:

```python
photo_file_id = await pick_avatar_file_id(gender)
```

- [ ] **Step 2: Add nickname pools and name mixing**

Add after `FEMALE_NAMES`:

```python
MALE_NICKNAMES = [
    "Некит", "Саня", "Димон", "Лёха", "Пашка", "Макс", "Артёмка",
    "Кирюха", "Миша", "Ваня", "Егорка", "Матвей", "Тёма", "Рома",
    "Влад", "Павлуша", "Стас", "Глеб", "Тимоха", "Ярик",
]

FEMALE_NICKNAMES = [
    "Лиска", "Машка", "Настюха", "Вика", "Катя", "Соня", "Даша",
    "Алиса", "Вероника", "Поля", "Лиза", "Ксюша", "Саша", "Оля",
    "Таня", "Юля", "Иришка", "Женька", "Алёнка", "Надюша",
]
```

Update `_pick_name`:

```python
def _pick_name(gender: str) -> str:
    if gender == "male":
        pool = MALE_NAMES if random.random() > 0.4 else MALE_NICKNAMES
    elif gender == "female":
        pool = FEMALE_NAMES if random.random() > 0.4 else FEMALE_NICKNAMES
    else:
        pool = MALE_NAMES + FEMALE_NAMES + MALE_NICKNAMES + FEMALE_NICKNAMES
    return random.choice(pool)
```

- [ ] **Step 3: Bias age toward viewer age**

Update `_pick_age`:

```python
def _pick_age(viewer: dict) -> int:
    user_age = viewer.get("age")
    min_age = max(viewer.get("filter_min_age", 16), 16)
    max_age = min(viewer.get("filter_max_age", 100), 100)

    if user_age is not None:
        delta = random.randint(-3, 3)
        target = user_age + delta
    else:
        target = random.randint(min_age, max_age)

    return max(min_age, min(max_age, target))
```

- [ ] **Step 4: Update generator tests**

Replace the existing `test_age_respects_viewer_filters` in `tests/test_fake_generator.py` with:

```python
def test_age_is_close_to_viewer_age():
    viewer = {"age": 22, "filter_min_age": 16, "filter_max_age": 100}
    for _ in range(50):
        age = _pick_age(viewer)
        assert 19 <= age <= 25


def test_age_respects_filters():
    viewer = {"age": 22, "filter_min_age": 23, "filter_max_age": 25}
    for _ in range(50):
        age = _pick_age(viewer)
        assert 23 <= age <= 25
```

Add a nickname test:

```python
def test_name_can_be_nickname():
    names = {_pick_name("male") for _ in range(100)}
    assert len(names) > 10
```

Update the batch test to monkeypatch the async picker:

```python
@pytest.mark.asyncio
async def test_generate_batch_creates_fake_users(monkeypatch):
    monkeypatch.setattr(
        "services.fake_profile_generator.pick_avatar_file_id",
        lambda _gender: None,
    )
    await _add_viewer()
    viewer = await database.get_user(1)
    fakes = await generate_fake_profiles_batch(viewer, count=2)
    assert len(fakes) == 2
    for fake in fakes:
        assert fake["is_fake"] == 1
        assert fake["user_id"] < 0
        assert fake["bio"]
```

- [ ] **Step 5: Run tests to verify changes**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_generator.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/fake_profile_generator.py tests/test_fake_generator.py
git commit -m "feat(generator): DB avatar picker, nicknames, age bias"
```

---

### Task 3: Remove obsolete avatar script and storage

**Files:**
- Delete: `scripts/prepare_fake_avatars.py`
- Delete: `data/fake_avatars/` directories and `.gitkeep` files
- Modify: `.gitignore`

- [ ] **Step 1: Delete files**

```bash
rm -rf data/fake_avatars
rm scripts/prepare_fake_avatars.py
```

- [ ] **Step 2: Clean `.gitignore`**

Remove these lines from `.gitignore`:

```gitignore
# Fake avatars (AI-generated faces and cached Telegram file_ids)
data/fake_avatars/**/*.jpg
data/fake_avatars/**/*.jpeg
data/fake_avatars/**/*.png
data/fake_avatars/file_ids.json
!data/fake_avatars/**/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git rm -r data/fake_avatars scripts/prepare_fake_avatars.py
git commit -m "chore: remove obsolete fake avatar script and folders"
```

---

### Task 4: Admin panel avatar upload flow

**Files:**
- Modify: `states.py`
- Modify: `keyboards.py`
- Modify: `handlers/admin.py`
- Test: `tests/test_admin_fakes.py`

- [ ] **Step 1: Add states**

In `states.py`, inside `AdminMenu` add:

```python
fake_avatar_gender = State()
fake_avatar_upload = State()
```

- [ ] **Step 2: Add keyboards**

In `keyboards.py` add:

```python
def admin_fake_avatars_gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мужские", callback_data="admin:fakeavatar:gender:male")],
            [InlineKeyboardButton(text="Женские", callback_data="admin:fakeavatar:gender:female")],
            [InlineKeyboardButton(text="Нейтральные", callback_data="admin:fakeavatar:gender:neutral")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:fakes")],
        ]
    )


def admin_fake_avatar_upload_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Готово", callback_data="admin:fakeavatar:done"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin:fakes"),
            ]
        ]
    )
```

Update `admin_fakes_keyboard` to include the new button:

```python
def admin_fakes_keyboard(fake_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить фейк", callback_data="admin:fakes:add")],
            [InlineKeyboardButton(text="🖼 Аватарки фейков", callback_data="admin:fakes:avatars")],
            [InlineKeyboardButton(text=f"🗑 Сбросить все фейки ({fake_count})", callback_data="admin:fakes:reset")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")],
        ]
    )
```

- [ ] **Step 3: Add admin handlers**

In `handlers/admin.py`, add imports:

```python
from database import (
    ...,
    add_fake_avatar,
    count_fake_avatars,
)
```

Also import new keyboards:

```python
from keyboards import (
    ...,
    admin_fake_avatar_upload_keyboard,
    admin_fake_avatars_gender_keyboard,
)
```

Add handlers:

```python
@router.callback_query(F.data == "admin:fakes:avatars")
async def admin_fake_avatars_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    counts = {
        "male": await count_fake_avatars("male"),
        "female": await count_fake_avatars("female"),
        "neutral": await count_fake_avatars("neutral"),
    }
    text = (
        "<b>🖼 Аватарки фейков</b>\n\n"
        f"Мужские: {counts['male']}\n"
        f"Женские: {counts['female']}\n"
        f"Нейтральные: {counts['neutral']}\n\n"
        "Выбери категорию и отправляй фото."
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_fake_avatars_gender_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:fakeavatar:gender:"))
async def admin_fake_avatar_select_gender(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    gender = callback.data.split(":", 3)[3]
    await state.set_state(AdminMenu.fake_avatar_upload)
    await state.update_data(fake_avatar_gender=gender, fake_avatar_count=0)
    if callback.message is not None:
        await callback.message.edit_text(
            "Отправляй фото. Добавлено: 0. Когда закончишь, нажми Готово.",
            reply_markup=admin_fake_avatar_upload_keyboard(),
        )
    await callback.answer()


@router.message(AdminMenu.fake_avatar_upload)
async def admin_fake_avatar_upload(message: types.Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Отправь фото.")
        return

    data = await state.get_data()
    gender = data.get("fake_avatar_gender", "neutral")
    count = data.get("fake_avatar_count", 0) + 1

    file_id = message.photo[-1].file_id
    await add_fake_avatar(gender, file_id)
    await state.update_data(fake_avatar_count=count)

    await message.answer(
        f"Добавлено: {count}",
        reply_markup=admin_fake_avatar_upload_keyboard(),
    )


@router.callback_query(F.data == "admin:fakeavatar:done")
async def admin_fake_avatar_done(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    count = data.get("fake_avatar_count", 0)
    await state.clear()
    await callback.answer(f"Сохранено фото: {count}")
    await admin_fakes_menu(callback, state)
```

- [ ] **Step 4: Write admin upload tests**

Create `tests/test_admin_fakes.py`:

```python
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, PhotoSize, User

from handlers.admin import admin_fake_avatar_upload
from states import AdminMenu


@pytest.fixture
def state():
    storage = MemoryStorage()
    return FSMContext(storage=storage, key="test")


@pytest.fixture
def message():
    msg = AsyncMock(spec=Message)
    msg.photo = [PhotoSize(file_id="photo_123", width=100, height=100, file_unique_id="uniq")]
    msg.from_user = User(id=1, is_bot=False, first_name="Admin")
    return msg


@pytest.mark.asyncio
async def test_admin_upload_photo_saves_avatar(state, message, monkeypatch):
    from database import count_fake_avatars

    monkeypatch.setattr("database.count_fake_avatars", AsyncMock(return_value=0))
    monkeypatch.setattr("database.add_fake_avatar", AsyncMock())

    await state.set_state(AdminMenu.fake_avatar_upload)
    await state.update_data(fake_avatar_gender="male", fake_avatar_count=0)

    await admin_fake_avatar_upload(message, state)

    message.answer.assert_awaited_once()
    args = message.answer.await_args
    assert "Добавлено: 1" in args[0][0]
```

- [ ] **Step 5: Run tests to verify**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_admin_fakes.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add states.py keyboards.py handlers/admin.py tests/test_admin_fakes.py
git commit -m "feat(admin): upload fake avatars by gender in Telegram panel"
```

---

### Task 5: Wipe DB and run full test suite

- [ ] **Step 1: Delete local database**

```bash
rm -f dating_bot.db
```

- [ ] **Step 2: Run full tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v`
Expected: PASS.

- [ ] **Step 3: Commit if test fixes were needed**

```bash
git commit -m "test: verify admin fake avatars integration" || true
```

---

## Plan Self-Review

**Spec coverage:**
- DB table for avatars — Task 1.
- Admin upload flow — Task 4.
- DB-based avatar picker in generator — Task 2.
- Nickname pools — Task 2.
- Age bias ±3 years — Task 2.
- DB wipe — Task 5.

**Placeholder scan:** No TBD/TODO/vague instructions. Every step has file paths, code, commands.

**Type consistency:** `add_fake_avatar(gender, file_id)`, `get_random_fake_avatar_file_id(gender)`, `count_fake_avatars(gender=None)` used consistently. `pick_avatar_file_id` is async in generator. States `fake_avatar_gender` / `fake_avatar_upload` used everywhere.
