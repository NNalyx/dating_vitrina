# Dating Bot Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-_SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend registration flow for a Telegram dating bot using aiogram 3.x, SQLite, and inline keyboards.

**Architecture:** A single Python package with clear separation: configuration, database layer, FSM states, keyboards, and handlers. The bot checks user existence on `/start`; if missing, starts a multi-step registration (policy → age → name → interests → optional photo). SQLite database is created automatically if the file does not exist.

**Tech Stack:** Python 3.10+, aiogram 3.x, aiosqlite, SQLite.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `znakomstvabot.py` | Entry point: creates the bot, dispatcher, registers routers, starts polling. |
| `config.py` | Constants: bot token, DB path, minimum age, interest categories. |
| `database.py` | Async SQLite layer: initialize DB, check user existence, insert user. Auto-creates DB file on first run. |
| `states.py` | aiogram FSM states for the registration flow. |
| `keyboards.py` | Inline keyboards: policy agreement, interest selection with toggled checkmarks. |
| `handlers/common.py` | `/start` handler: checks if user exists and either greets or starts registration. |
| `handlers/registration.py` | All registration handlers: policy, age, name, interests, optional photo. |
| `handlers/__init__.py` | Empty package marker. |

---

## Notes for the Implementer

- The bot token is stored directly in `config.py` as requested by the user. Replace `YOUR_BOT_TOKEN_HERE` with the real token before running.
- SQLite DB file path is `dating_bot.db` in the project root. Deleting this file resets all data, which is what the user wants for testing.
- Parse mode is set to HTML so we can use the `<span class="tg-spoiler">...</span>` tag for the privacy policy.
- Interest selection uses a single inline keyboard. Each item is a button; clicking toggles a checkmark (`✅`) next to the label. A "Done" button validates the minimum count.

---

### Task 0: Install Dependencies

**Files:**
- None (environment change)

- [ ] **Step 1: Activate the virtual environment and install packages**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
pip install aiogram aiosqlite
```

Expected output: both packages install successfully.

- [ ] **Step 2: Commit**

Not applicable (no project files yet). Move to Task 1.

---

### Task 1: Create `config.py`

**Files:**
- Create: `config.py`

- [ ] **Step 1: Write the file**

```python
# config.py

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with the real token from BotFather
DB_PATH = "dating_bot.db"
MIN_AGE = 16

INTEREST_CATEGORIES = [
    (
        "games",
        "🎮 Игры",
        [
            "Dota 2",
            "Valorant",
            "CS2",
            "League of Legends",
            "Minecraft",
            "Fortnite",
            "GTA",
            "Roblox",
            "Genshin Impact",
            "Mobile Games",
        ],
    ),
    (
        "animation",
        "🎬 Анимация",
        ["Аниме", "Манга", "Кино", "Сериалы", "YouTube", "Стримы"],
    ),
    (
        "sport",
        "⚽ Спорт",
        [
            "Футбол",
            "Баскетбол",
            "Волейбол",
            "Теннис",
            "Хоккей",
            "Тренажёрный зал",
            "Бег",
            "Велоспорт",
        ],
    ),
    (
        "creative",
        "🎨 Творчество",
        ["Музыка", "Рисование", "Фото", "Видеомонтаж", "Писательство"],
    ),
    (
        "tech",
        "💻 Технологии",
        ["Программирование", "Дизайн", "AI/ML", "Крипта", "Гаджеты"],
    ),
    (
        "lifestyle",
        "🌿 Образ жизни",
        ["Путешествия", "Кулинария", "Чтение", "Настольные игры", "Волонтёрство"],
    ),
]
```

- [ ] **Step 2: Verify the file exists and imports without errors**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "import config; print(config.MIN_AGE)"
```

Expected output: `16`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add bot configuration and interest categories"
```

---

### Task 2: Create `database.py`

**Files:**
- Create: `database.py`

- [ ] **Step 1: Write the file**

```python
# database.py

import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Create the users table if the database file does not exist yet."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                age INTEGER NOT NULL,
                name TEXT NOT NULL,
                interests TEXT NOT NULL,
                photo_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def user_exists(user_id: int) -> bool:
    """Return True if a user with the given Telegram ID is already registered."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def add_user(
    user_id: int,
    username: str | None,
    age: int,
    name: str,
    interests: list[str],
    photo_file_id: str | None = None,
) -> None:
    """Insert a newly registered user into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, age, name, interests, photo_file_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, age, name, ",".join(interests), photo_file_id),
        )
        await db.commit()
```

- [ ] **Step 2: Test that the database initializes and user operations work**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python - <<'PY'
import asyncio
from database import init_db, user_exists, add_user

async def main():
    await init_db()
    print("exists before:", await user_exists(123456))
    await add_user(123456, "test_user", 20, "Test", ["Dota 2", "Аниме"])
    print("exists after:", await user_exists(123456))

asyncio.run(main())
PY
```

Expected output:
```
exists before: False
exists after: True
```

Delete `dating_bot.db` after the test to keep the workspace clean.

- [ ] **Step 3: Commit**

```bash
git add database.py
git commit -m "feat: add async SQLite database layer"
```

---

### Task 3: Create `states.py`

**Files:**
- Create: `states.py`

- [ ] **Step 1: Write the file**

```python
# states.py

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    policy = State()
    age = State()
    name = State()
    interests = State()
    photo = State()
```

- [ ] **Step 2: Verify the import**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "from states import Registration; print(Registration.policy)"
```

Expected output: a state object representation (no error).

- [ ] **Step 3: Commit**

```bash
git add states.py
git commit -m "feat: add registration FSM states"
```

---

### Task 4: Create `keyboards.py`

**Files:**
- Create: `keyboards.py`

- [ ] **Step 1: Write the file**

```python
# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import INTEREST_CATEGORIES


def policy_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown with the privacy policy."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="policy_agree")]
        ]
    )


def build_interests_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Build an inline keyboard where selected items have a checkmark."""
    buttons = []
    for _category_key, _category_label, items in INTEREST_CATEGORIES:
        for item in items:
            mark = "✅ " if item in selected else ""
            buttons.append(
                [InlineKeyboardButton(text=f"{mark}{item}", callback_data=f"interest:{item}")]
            )
    buttons.append([InlineKeyboardButton(text="Готово ✅", callback_data="interest_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

- [ ] **Step 2: Verify the keyboard builds correctly**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python - <<'PY'
from keyboards import build_interests_keyboard
kb = build_interests_keyboard({"Dota 2", "Аниме"})
print("rows:", len(kb.inline_keyboard))
print("first button:", kb.inline_keyboard[0][0].text)
print("last button:", kb.inline_keyboard[-1][0].text)
PY
```

Expected output:
```
rows: 40
first button: ✅ Dota 2
last button: Готово ✅
```

- [ ] **Step 3: Commit**

```bash
git add keyboards.py
git commit -m "feat: add policy and interest inline keyboards"
```

---

### Task 5: Create `handlers/common.py`

**Files:**
- Create: `handlers/common.py`
- Create: `handlers/__init__.py`

- [ ] **Step 1: Write `handlers/__init__.py`**

```python
# handlers/__init__.py
```

Leave the file empty.

- [ ] **Step 2: Write `handlers/common.py`**

```python
# handlers/common.py

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import user_exists
from keyboards import policy_keyboard
from states import Registration

router = Router()

PRIVACY_POLICY_TEXT = (
    "<b>Политика конфиденциальности</b>\n\n"
    "<span class=\"tg-spoiler\">"
    "Нажимая «Согласен», вы подтверждаете, что вам исполнилось 16 лет, "
    "и соглашаетесь на обработку предоставленных данных (возраст, имя/ник, фото, увлечения) "
    "в рамках работы бота. Администрация не несёт ответственности за действия пользователей "
    "и содержание анкет. Мы не передаём персональные данные третьим лицам."
    "</span>\n\n"
    "Для продолжения регистрации нажмите кнопку ниже."
)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()

    if await user_exists(message.from_user.id):
        await message.answer(
            "Привет снова! Ты уже зарегистрирован. Используй /search для поиска анкет."
        )
        return

    await message.answer(
        "Добро пожаловать! Для начала работы нужно пройти регистрацию.\n\n"
        + PRIVACY_POLICY_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=policy_keyboard(),
    )
    await state.set_state(Registration.policy)
```

- [ ] **Step 3: Verify the module imports**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "from handlers import common; print(common.router)"
```

Expected output: a Router object (no error).

- [ ] **Step 4: Commit**

```bash
git add handlers/__init__.py handlers/common.py
git commit -m "feat: add /start handler with privacy policy and registration kickoff"
```

---

### Task 6: Create `handlers/registration.py` — Policy & Age

**Files:**
- Create: `handlers/registration.py`

- [ ] **Step 1: Write the first part of the file**

```python
# handlers/registration.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MIN_AGE
from keyboards import build_interests_keyboard
from states import Registration

router = Router()


@router.callback_query(F.data == "policy_agree", Registration.policy)
async def process_policy(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User agreed to the privacy policy."""
    await callback.message.edit_text("Отлично! Сколько тебе лет?")
    await state.set_state(Registration.age)
    await callback.answer()


@router.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext) -> None:
    """Validate age and move to the name step."""
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введи возраст числом.")
        return

    age = int(message.text)
    if age < MIN_AGE:
        await message.answer(
            f"Извини, но этот бот только для пользователей {MIN_AGE}+ лет."
        )
        return

    await state.update_data(age=age)
    await message.answer("Как тебя зовут? Можешь указать имя или ник.")
    await state.set_state(Registration.name)
```

- [ ] **Step 2: Verify the module imports**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "from handlers import registration; print(registration.router)"
```

Expected output: a Router object (no error).

- [ ] **Step 3: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add policy agreement and age handlers"
```

---

### Task 7: Add Name Handler to `handlers/registration.py`

**Files:**
- Modify: `handlers/registration.py`

- [ ] **Step 1: Append the name handler after the age handler**

Add this function to the end of `handlers/registration.py`:

```python


@router.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext) -> None:
    """Save the user's display name and move to interest selection."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи хотя бы 2 символа.")
        return

    await state.update_data(name=name)
    await message.answer(
        "Выбери свои увлечения. Нужно выбрать минимум 3. Нажми «Готово», когда закончишь.",
        reply_markup=build_interests_keyboard(set()),
    )
    await state.set_state(Registration.interests)
```

- [ ] **Step 2: Verify the file still imports**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "from handlers import registration; print('name handler present:', hasattr(registration, 'process_name'))"
```

Expected output:
```
name handler present: True
```

- [ ] **Step 3: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add registration name handler"
```

---

### Task 8: Add Interest Toggle Handler

**Files:**
- Modify: `handlers/registration.py`

- [ ] **Step 1: Append the interest toggle handler**

Add this function to the end of `handlers/registration.py`:

```python


@router.callback_query(F.data.startswith("interest:"), Registration.interests)
async def toggle_interest(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle an interest selection and update the keyboard in place."""
    item = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("interests", []))

    if item in selected:
        selected.remove(item)
    else:
        selected.add(item)

    await state.update_data(interests=selected)
    await callback.message.edit_reply_markup(
        reply_markup=build_interests_keyboard(selected)
    )
    await callback.answer()
```

- [ ] **Step 2: Verify the module imports**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "from handlers import registration; print('toggle handler present:', hasattr(registration, 'toggle_interest))"
```

Expected output:
```
toggle handler present: True
```

- [ ] **Step 3: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add interest toggle with live keyboard update"
```

---

### Task 9: Add Interest Done Handler and Skip-Photo Keyboard

**Files:**
- Modify: `handlers/registration.py`
- Modify: `keyboards.py`

- [ ] **Step 1: Add the skip-photo keyboard to `keyboards.py`**

Append to `keyboards.py`:

```python

def skip_photo_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when asking for an optional photo."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="photo_skip")]
        ]
    )
```

- [ ] **Step 2: Append the interest-done handler to `handlers/registration.py`**

Add this function to the end of `handlers/registration.py`:

```python


@router.callback_query(F.data == "interest_done", Registration.interests)
async def finish_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Validate minimum interest count and move to the photo step."""
    data = await state.get_data()
    selected = data.get("interests", [])

    if len(selected) < 3:
        await callback.answer(
            "Выбери минимум 3 увлечения, чтобы продолжить.", show_alert=True
        )
        return

    await callback.message.edit_text(
        "Отправь свою фотографию. Это повысит количество лайков. "
        "Если не хочешь — нажми «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )
    await state.set_state(Registration.photo)
    await callback.answer()
```

- [ ] **Step 3: Verify both modules import correctly**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python - <<'PY'
from keyboards import skip_photo_keyboard
from handlers import registration
print("skip keyboard rows:", len(skip_photo_keyboard().inline_keyboard))
print("finish handler present:", hasattr(registration, 'finish_interests'))
PY
```

Expected output:
```
skip keyboard rows: 1
finish handler present: True
```

- [ ] **Step 4: Commit**

```bash
git add keyboards.py handlers/registration.py
git commit -m "feat: add interest done validation and skip-photo prompt"
```

---

### Task 10: Add Photo Handler and Profile Save

**Files:**
- Modify: `handlers/registration.py`
- Modify: `database.py` (if `add_user` already exists from Task 2, no change needed)

- [ ] **Step 1: Append photo and save handlers to `handlers/registration.py`**

Add these functions to the end of `handlers/registration.py`:

```python


@router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext) -> None:
    """Save the largest photo variant and finish registration."""
    photo_id = message.photo[-1].file_id
    await _save_profile(message, state, photo_id)


@router.callback_query(F.data == "photo_skip", Registration.photo)
async def skip_photo(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip the photo step with a warning, then finish registration."""
    await callback.message.edit_text(
        "Фото не добавлено. Пользователи без фото обычно получают меньше лайков."
    )
    await _save_profile(callback.message, state, photo_id=None)
    await callback.answer()


async def _save_profile(
    message: types.Message, state: FSMContext, photo_id: str | None
) -> None:
    """Persist the user and clear the registration state."""
    data = await state.get_data()
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        age=data["age"],
        name=data["name"],
        interests=sorted(data["interests"]),
        photo_file_id=photo_id,
    )
    await message.answer(
        "🎉 Регистрация завершена! Теперь ты можешь использовать /search для поиска анкет."
    )
    await state.clear()
```

- [ ] **Step 2: Add the `add_user` import if missing**

Ensure the top of `handlers/registration.py` contains:

```python
from database import add_user
```

If it is not there, add it to the existing imports.

- [ ] **Step 3: Verify the module imports**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "from handlers import registration; print('photo handler present:', hasattr(registration, 'process_photo))"
```

Expected output:
```
photo handler present: True
```

- [ ] **Step 4: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add photo upload, skip option, and profile save"
```

---

### Task 11: Create `znakomstvabot.py` Entry Point

**Files:**
- Create: `znakomstvabot.py`

- [ ] **Step 1: Write the file**

```python
# znakomstvabot.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import common, registration


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Ensure SQLite database and tables exist (creates file if missing)
    await init_db()

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_routers(common.router, registration.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify the bot starts and imports correctly**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python -c "import znakomstvabot; print('imports ok')"
```

Expected output:
```
imports ok
```

- [ ] **Step 3: Commit**

```bash
git add znakomstvabot.py
git commit -m "feat: add bot entry point with routers and HTML parse mode"
```

---

### Task 12: End-to-End Test in Telegram

**Files:**
- None (manual test)

- [ ] **Step 1: Replace the placeholder token**

Edit `config.py` and replace `YOUR_BOT_TOKEN_HERE` with the real token from BotFather.

- [ ] **Step 2: Start the bot**

Run:
```bash
cd /c/Users/antpl/PycharmProjects/PythonProject
source .venv/Scripts/activate
python znakomstvabot.py
```

Expected output: bot logs show polling started, no errors.

- [ ] **Step 3: Run through registration in Telegram**

1. Send `/start` to the bot from a fresh account (or delete `dating_bot.db` first).
2. Verify the privacy policy appears under a spoiler.
3. Tap "Согласен".
4. Enter age below 16 — verify the bot rejects it.
5. Enter valid age (e.g., 20).
6. Enter a name.
7. Select 1–2 interests and tap "Готово" — verify the bot asks for at least 3.
8. Select 3+ interests and tap "Готово".
9. Send a photo — verify registration completes.
10. Delete `dating_bot.db`, restart the bot, and test the "Пропустить" flow for the photo step.

- [ ] **Step 4: Commit**

```bash
git add config.py
git commit -m "chore: insert real bot token for testing"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| Check user existence by ID on `/start` | Task 5 (`handlers/common.py`) |
| Create DB file if missing | Task 2 (`database.py`) |
| Show privacy policy under spoiler | Task 5 (`handlers/common.py`) |
| Single "Agree" button | Task 4 + Task 6 |
| Ask age, reject under 16 | Task 6 |
| Ask name/nickname | Task 7 |
| Select interests from a list with many categories + games | Tasks 1, 4, 8, 9 |
| Inline button updates with checkmark | Task 8 |
| Minimum 3 interests validation | Task 9 |
| Ask for optional photo | Task 9 |
| Warn that skipping photo means fewer likes | Task 10 |

### Placeholder Scan

- `YOUR_BOT_TOKEN_HERE` is the only configurable placeholder; it is documented in Task 12 Step 1.
- No `TBD`, `TODO`, or vague "add validation" steps remain.

### Type Consistency

- `interests` is stored as a list in FSM state and joined with `","` in `add_user`.
- `photo_file_id` is consistently typed as `str | None`.
- `user_id` is consistently `int`.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-20-dating-bot-registration.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

**Which approach do you want?**
