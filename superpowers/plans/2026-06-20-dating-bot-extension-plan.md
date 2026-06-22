# Расширение Telegram-бота знакомств — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в существующего aiogram-бота знакомств главное меню, просмотр/редактирование анкеты, ленту анкет с алгоритмом совместимости в процентах и систему лайков с взаимными лайками.

**Architecture:** Модульный подход: чистые CRUD-функции в `database.py`, бизнес-логика совместимости в `services/matching.py`, форматирование анкет в `services/profile.py`, Telegram-интерфейс разбит по `handlers/*.py`. Каждый файл отвечает за одну зону ответственности.

**Tech Stack:** Python 3.11+, aiogram 3.29.0, aiosqlite 0.22.1, SQLite.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `config.py` | Константы: токен, путь к БД, минимальный возраст, категории интересов, гендерные/целевые опции |
| `database.py` | CRUD: users, likes, views, получение статистики |
| `states.py` | FSM-состояния регистрации и редактирования профиля |
| `keyboards.py` | Все inline/reply клавиатуры |
| `services/profile.py` | Форматирование карточки анкеты |
| `services/matching.py` | Фильтрация кандидатов и расчёт совместимости |
| `handlers/common.py` | `/start`, политика конфиденциальности |
| `handlers/registration.py` | Полный флоу регистрации |
| `handlers/menu.py` | Главное меню со статистикой |
| `handlers/profile.py` | Просмотр и редактирование анкеты |
| `handlers/browse.py` | Лента анкет, лайк, пропуск |
| `handlers/likes.py` | Входящие лайки, лайк в ответ, взаимные лайки |
| `znakomstvabot.py` | Точка входа, подключение роутеров |
| `tests/test_matching.py` | Unit-тесты алгоритма совместимости |

---

### Task 1: Reset Database and Create New Schema

**Files:**
- Delete: `dating_bot.db`
- Modify: `database.py`

- [ ] **Step 1: Remove old database file**

Run:

```bash
rm /c/Users/antpl/PycharmProjects/PythonProject/dating_bot.db
```

Expected: file removed, no output.

- [ ] **Step 2: Replace `database.py` with new schema and CRUD functions**

```python
# database.py

import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Create all tables if they do not exist."""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
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
    gender: str,
    looking_for: str,
    goal: str,
    interests: list[str],
    photo_file_id: str | None = None,
) -> None:
    """Insert a newly registered user into the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users
            (user_id, username, age, name, gender, looking_for, goal, interests, photo_file_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                age,
                name,
                gender,
                looking_for,
                goal,
                ",".join(sorted(interests)),
                photo_file_id,
            ),
        )
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    """Return user row as a dict or None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_user(
    user_id: int,
    *,
    age: int | None = None,
    name: str | None = None,
    looking_for: str | None = None,
    goal: str | None = None,
    interests: list[str] | None = None,
    photo_file_id: str | None = None,
) -> None:
    """Update one or more user fields."""
    fields = []
    values = []
    if age is not None:
        fields.append("age = ?")
        values.append(age)
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if looking_for is not None:
        fields.append("looking_for = ?")
        values.append(looking_for)
    if goal is not None:
        fields.append("goal = ?")
        values.append(goal)
    if interests is not None:
        fields.append("interests = ?")
        values.append(",".join(sorted(interests)))
    if photo_file_id is not None:
        fields.append("photo_file_id = ?")
        values.append(photo_file_id)

    if not fields:
        return

    values.append(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?",
            values,
        )
        await db.commit()


async def get_all_users() -> list[dict]:
    """Return all users as a list of dicts."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_like(from_user_id: int, to_user_id: int) -> None:
    """Record a like, ignoring duplicates."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO likes (from_user_id, to_user_id)
            VALUES (?, ?)
            """,
            (from_user_id, to_user_id),
        )
        await db.commit()


async def has_like(from_user_id: int, to_user_id: int) -> bool:
    """Return True if from_user_id has liked to_user_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM likes WHERE from_user_id = ? AND to_user_id = ?",
            (from_user_id, to_user_id),
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_like_stats(user_id: int) -> tuple[int, int]:
    """Return (sent_likes, received_likes)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM likes WHERE from_user_id = ?", (user_id,)
        ) as cursor:
            sent = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM likes WHERE to_user_id = ?", (user_id,)
        ) as cursor:
            received = (await cursor.fetchone())[0]
        return sent, received


async def add_view(viewer_id: int, viewed_id: int) -> None:
    """Mark a profile as viewed, ignoring duplicates."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO views (viewer_id, viewed_id)
            VALUES (?, ?)
            """,
            (viewer_id, viewed_id),
        )
        await db.commit()


async def get_viewed_ids(viewer_id: int) -> set[int]:
    """Return set of user IDs already viewed by viewer_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT viewed_id FROM views WHERE viewer_id = ?", (viewer_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
```

- [ ] **Step 3: Verify imports and basic function signatures**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import database; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add database.py && git commit -m "feat(db): reset schema, add users/likes/views CRUD"
```

---

### Task 2: Update config.py with New Constants

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Replace `config.py` content**

Keep the existing `BOT_TOKEN` value (do not change it). Replace everything else with:

```python
# config.py

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Do not change the real token
DB_PATH = "dating_bot.db"
MIN_AGE = 16

GENDER_OPTIONS = [
    ("male", "Парень"),
    ("female", "Девушка"),
    ("other", "Другое"),
]

LOOKING_FOR_OPTIONS = [
    ("male", "Парней"),
    ("female", "Девушек"),
    ("all", "Всех"),
]

GOAL_OPTIONS = [
    ("relationship", "Отношения"),
    ("friendship", "Дружба"),
    ("flirt", "Флирт"),
]

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

- [ ] **Step 2: Verify config imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import config; print(config.GOAL_OPTIONS)"
```

Expected: `[('relationship', 'Отношения'), ('friendship', 'Дружба'), ('flirt', 'Флирт')]`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add config.py && git commit -m "feat(config): add gender, looking_for, goal options"
```

---

### Task 3: Update states.py

**Files:**
- Modify: `states.py`

- [ ] **Step 1: Replace `states.py` content**

```python
# states.py

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    policy = State()
    age = State()
    name = State()
    gender = State()
    looking_for = State()
    goal = State()
    interests = State()
    photo = State()


class EditProfile(StatesGroup):
    choosing_field = State()
    age = State()
    name = State()
    looking_for = State()
    goal = State()
    interests = State()
    photo = State()
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import states; print(list(states.Registration.__states_names__))"
```

Expected: list of state names including `policy`, `age`, `name`, `gender`, `looking_for`, `goal`, `interests`, `photo`.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add states.py && git commit -m "feat(states): add gender, goal, looking_for and edit states"
```

---

### Task 4: Update keyboards.py

**Files:**
- Modify: `keyboards.py`

- [ ] **Step 1: Replace `keyboards.py` content**

```python
# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import INTEREST_CATEGORIES, GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS


def policy_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown with the privacy policy."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="policy_agree")]
        ]
    )


def gender_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting user's gender."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"gender:{key}")]
        for key, label in GENDER_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def looking_for_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting who the user is looking for."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"looking_for:{key}")]
        for key, label in LOOKING_FOR_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def goal_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting the dating goal."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"goal:{key}")]
        for key, label in GOAL_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


def skip_photo_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when asking for an optional photo."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="photo_skip")]
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Моя анкета")],
            [KeyboardButton(text="🔍 Смотреть анкеты")],
            [KeyboardButton(text="❤️ Мои лайки")],
        ],
        resize_keyboard=True,
    )


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for profile editing options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Имя", callback_data="edit:name")],
            [InlineKeyboardButton(text="✏️ Возраст", callback_data="edit:age")],
            [InlineKeyboardButton(text="✏️ Кого ищу", callback_data="edit:looking_for")],
            [InlineKeyboardButton(text="✏️ Цель", callback_data="edit:goal")],
            [InlineKeyboardButton(text="✏️ Интересы", callback_data="edit:interests")],
            [InlineKeyboardButton(text="✏️ Фото", callback_data="edit:photo")],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )


def browse_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for browsing profiles."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Лайк", callback_data="browse:like"),
                InlineKeyboardButton(text="👎 Пропустить", callback_data="browse:skip"),
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )


def like_response_keyboard(liker_id: int) -> InlineKeyboardMarkup:
    """Keyboard for responding to an incoming like."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Лайк в ответ", callback_data=f"like_back:{liker_id}"),
                InlineKeyboardButton(text="👎 Пропустить", callback_data=f"like_skip:{liker_id}"),
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )


def write_link_keyboard(username: str | None, user_id: int) -> InlineKeyboardMarkup:
    """Keyboard with a link to start a private chat."""
    if username:
        url = f"https://t.me/{username}"
    else:
        url = f"tg://user?id={user_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать", url=url)],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import keyboards; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add keyboards.py && git commit -m "feat(keyboards): add menu, gender, goal, edit and browse keyboards"
```

---

### Task 5: Update common.py with Expandable Privacy Policy

**Files:**
- Modify: `handlers/common.py`

- [ ] **Step 1: Replace `handlers/common.py` content**

```python
# handlers/common.py

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import user_exists
from handlers.menu import show_main_menu
from keyboards import policy_keyboard
from states import Registration

router = Router()

PRIVACY_POLICY_TEXT = (
    "<b>Политика конфиденциальности</b>\n\n"
    "<blockquote expandable>\n"
    "1. Мы храним: возраст, имя, пол, цель знакомства, увлечения и фото.\n"
    "2. Данные используются только для подбора анкет внутри бота.\n"
    "3. Бот предназначен для пользователей 16+.\n"
    "4. Мы не передаём данные третьим лицам.\n"
    "5. Администрация не отвечает за поведение других пользователей.\n"
    "</blockquote>\n\n"
    "Для продолжения регистрации нажми кнопку ниже."
)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()

    if message.from_user is None:
        return

    if await user_exists(message.from_user.id):
        await show_main_menu(message, state)
        return

    await message.answer(
        "Добро пожаловать! Для начала работы нужно пройти регистрацию.\n\n"
        + PRIVACY_POLICY_TEXT,
        reply_markup=policy_keyboard(),
    )
    await state.set_state(Registration.policy)
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import handlers.common; print('ok')"
```

Expected: `ok` (ignore circular import warnings for now; will be resolved once menu.py exists).

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add handlers/common.py && git commit -m "feat(common): switch privacy policy to expandable blockquote"
```

---

### Task 6: Rewrite registration.py with New Fields and Menu Transition

**Files:**
- Modify: `handlers/registration.py`

- [ ] **Step 1: Replace `handlers/registration.py` content**

```python
# handlers/registration.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MIN_AGE
from database import add_user
from handlers.menu import show_main_menu
from keyboards import (
    build_interests_keyboard,
    gender_keyboard,
    goal_keyboard,
    looking_for_keyboard,
    skip_photo_keyboard,
)
from states import Registration

router = Router()


@router.callback_query(F.data == "policy_agree", Registration.policy)
async def process_policy(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User agreed to the privacy policy."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
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


@router.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext) -> None:
    """Save the user's display name and move to gender selection."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи хотя бы 2 символа.")
        return

    await state.update_data(name=name)
    await message.answer(
        "Укажи свой пол:",
        reply_markup=gender_keyboard(),
    )
    await state.set_state(Registration.gender)


@router.callback_query(F.data.startswith("gender:"), Registration.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save gender and ask who the user is looking for."""
    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text("Кого ты ищешь?", reply_markup=looking_for_keyboard())
    await state.set_state(Registration.looking_for)
    await callback.answer()


@router.callback_query(F.data.startswith("looking_for:"), Registration.looking_for)
async def process_looking_for(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save looking_for preference and ask for the dating goal."""
    looking_for = callback.data.split(":", 1)[1]
    await state.update_data(looking_for=looking_for)
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text(
        "Что ты ищешь?", reply_markup=goal_keyboard()
    )
    await state.set_state(Registration.goal)
    await callback.answer()


@router.callback_query(F.data.startswith("goal:"), Registration.goal)
async def process_goal(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save goal and move to interest selection."""
    goal = callback.data.split(":", 1)[1]
    await state.update_data(goal=goal)
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text(
        "Выбери свои увлечения. Нужно выбрать минимум 3. Нажми «Готово», когда закончишь.",
        reply_markup=build_interests_keyboard(set()),
    )
    await state.set_state(Registration.interests)
    await callback.answer()


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

    await state.update_data(interests=list(selected))
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_reply_markup(
        reply_markup=build_interests_keyboard(selected)
    )
    await callback.answer()


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

    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text(
        "Отправь свою фотографию. Это повысит количество лайков. "
        "Если не хочешь — нажми «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )
    await state.set_state(Registration.photo)
    await callback.answer()


@router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext) -> None:
    """Save the largest photo variant and finish registration."""
    photo_id = message.photo[-1].file_id
    await _save_profile(message, state, photo_id)


@router.callback_query(F.data == "photo_skip", Registration.photo)
async def skip_photo(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip the photo step with a warning, then finish registration."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    await callback.message.edit_text(
        "Фото не добавлено. Пользователи без фото обычно получают меньше лайков."
    )
    await _save_profile(callback.message, state, photo_id=None)
    await callback.answer()


@router.message(Registration.photo)
async def wrong_photo_input(message: types.Message) -> None:
    """Handle any non-photo input during the photo step."""
    await message.answer(
        "Пожалуйста, отправь фотографию или нажми кнопку «Пропустить»."
    )


async def _save_profile(
    message: types.Message, state: FSMContext, photo_id: str | None
) -> None:
    """Persist the user and show the main menu."""
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    data = await state.get_data()
    required_fields = ("age", "name", "gender", "looking_for", "goal", "interests")
    missing = [field for field in required_fields if field not in data]
    if missing:
        await message.answer(
            "Что-то пошло не так с регистрацией. Попробуй начать сначала с /start."
        )
        await state.clear()
        return

    try:
        await add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            age=data["age"],
            name=data["name"],
            gender=data["gender"],
            looking_for=data["looking_for"],
            goal=data["goal"],
            interests=sorted(data["interests"]),
            photo_file_id=photo_id,
        )
    except Exception:
        await message.answer(
            "Не удалось сохранить анкету. Попробуй ещё раз позже."
        )
        return

    await message.answer("🎉 Регистрация завершена!")
    await show_main_menu(message, state)
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import handlers.registration; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add handlers/registration.py && git commit -m "feat(registration): add gender, looking_for, goal and route to main menu"
```

---

### Task 7: Create services/profile.py

**Files:**
- Create: `services/profile.py`
- Create: `services/__init__.py`

- [ ] **Step 1: Create `services/__init__.py`**

```python
# services/__init__.py
```

Leave it empty.

- [ ] **Step 2: Create `services/profile.py`**

```python
# services/profile.py

from config import GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS


_LABEL_MAP = {}
for _options in (GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS):
    _LABEL_MAP.update(dict(_options))


def _label(key: str) -> str:
    return _LABEL_MAP.get(key, key)


def format_profile(user: dict, *, title: str = "📋 Анкета") -> str:
    """Format a user dict into a profile card text."""
    interests = user.get("interests") or ""
    interests_list = [i.strip() for i in interests.split(",") if i.strip()]
    interests_text = ", ".join(interests_list) if interests_list else "—"

    lines = [
        f"<b>{title}</b>",
        "",
        f"<b>Имя:</b> {user['name']}",
        f"<b>Возраст:</b> {user['age']}",
        f"<b>Пол:</b> {_label(user['gender'])}",
        f"<b>Ищу:</b> {_label(user['looking_for'])}",
        f"<b>Цель:</b> {_label(user['goal'])}",
        f"<b>Увлечения:</b> {interests_text}",
    ]
    return "\n".join(lines)


def format_browse_card(user: dict, compatibility: int) -> str:
    """Format a candidate card for the browse feed."""
    interests = user.get("interests") or ""
    interests_list = [i.strip() for i in interests.split(",") if i.strip()]
    interests_text = ", ".join(interests_list) if interests_list else "—"

    lines = [
        f"<b>{user['name']}, {user['age']}</b>",
        f"<b>Совместимость:</b> {compatibility}% ❤️",
        "",
        f"🎯 <b>Цель:</b> {_label(user['goal'])}",
        f"⭐ <b>Увлечения:</b> {interests_text}",
    ]
    return "\n".join(lines)
```

- [ ] **Step 3: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "from services.profile import format_profile; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add services/__init__.py services/profile.py && git commit -m "feat(profile): add profile card formatting"
```

---

### Task 8: Create services/matching.py with Unit Tests

**Files:**
- Create: `services/matching.py`
- Create: `tests/test_matching.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `tests/__init__.py`**

Leave it empty.

- [ ] **Step 2: Write failing test for compatibility function**

Create `tests/test_matching.py`:

```python
# tests/test_matching.py

import pytest
from services.matching import calculate_compatibility, gender_match


def test_calculate_compatibility_perfect_match():
    me = {"age": 20, "goal": "relationship", "interests": "Dota 2,Аниме"}
    candidate = {"age": 20, "goal": "relationship", "interests": "Dota 2,Аниме"}
    assert calculate_compatibility(me, candidate) == 100


def test_calculate_compatibility_no_common_interests():
    me = {"age": 20, "goal": "relationship", "interests": "Dota 2,Аниме"}
    candidate = {"age": 20, "goal": "relationship", "interests": "Футбол,Кулинария"}
    assert calculate_compatibility(me, candidate) == 60


def test_calculate_compatibility_different_goal():
    me = {"age": 20, "goal": "relationship", "interests": "Dota 2"}
    candidate = {"age": 20, "goal": "friendship", "interests": "Dota 2"}
    assert calculate_compatibility(me, candidate) == 70


def test_gender_match_both_all():
    assert gender_match("male", "all", "female", "all") is True


def test_gender_match_unidirectional():
    assert gender_match("male", "female", "female", "male") is True


def test_gender_match_no_match():
    assert gender_match("male", "female", "male", "female") is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -m pytest tests/test_matching.py -v
```

Expected: failures because `services/matching.py` does not exist.

- [ ] **Step 4: Create `services/matching.py`**

```python
# services/matching.py

from config import MIN_AGE


INTEREST_WEIGHT = 40
AGE_WEIGHT = 30
GOAL_WEIGHT = 30
AGE_DIFF_MAX = 10


def _parse_interests(interests: str | None) -> set[str]:
    if not interests:
        return set()
    return {item.strip() for item in interests.split(",") if item.strip()}


def gender_match(
    my_gender: str, my_looking_for: str, their_gender: str, their_looking_for: str
) -> bool:
    """Return True if both users fit each other's gender preferences."""
    i_like_them = my_looking_for == "all" or my_looking_for == their_gender
    they_like_me = their_looking_for == "all" or their_looking_for == my_gender
    return i_like_them and they_like_me


def calculate_compatibility(me: dict, candidate: dict) -> int:
    """Return compatibility percentage (0-100)."""
    my_interests = _parse_interests(me.get("interests"))
    their_interests = _parse_interests(candidate.get("interests"))

    union = my_interests | their_interests
    if union:
        intersection = my_interests & their_interests
        interest_score = len(intersection) / len(union) * INTEREST_WEIGHT
    else:
        interest_score = 0

    age_diff = abs(me["age"] - candidate["age"])
    age_score = max(0, 1 - age_diff / AGE_DIFF_MAX) * AGE_WEIGHT

    goal_score = GOAL_WEIGHT if me["goal"] == candidate["goal"] else 0

    return round(interest_score + age_score + goal_score)


def filter_candidates(me: dict, candidates: list[dict], viewed_ids: set[int]) -> list[dict]:
    """Return candidates matching filters, excluding self and already viewed."""
    results = []
    for candidate in candidates:
        cid = candidate["user_id"]
        if cid == me["user_id"] or cid in viewed_ids:
            continue
        if not gender_match(
            me["gender"],
            me["looking_for"],
            candidate["gender"],
            candidate["looking_for"],
        ):
            continue
        if me["goal"] != candidate["goal"]:
            continue
        age_diff = abs(me["age"] - candidate["age"])
        if age_diff > 5:
            continue
        results.append(candidate)
    return results


def score_candidates(me: dict, candidates: list[dict]) -> list[tuple[dict, int]]:
    """Return candidates sorted by compatibility descending."""
    scored = [(c, calculate_compatibility(me, c)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -m pytest tests/test_matching.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add services/matching.py tests/__init__.py tests/test_matching.py && git commit -m "feat(matching): add compatibility algorithm and unit tests"
```

---

### Task 9: Create handlers/menu.py

**Files:**
- Create: `handlers/menu.py`

- [ ] **Step 1: Create `handlers/menu.py`**

```python
# handlers/menu.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from database import get_like_stats
from keyboards import main_menu_keyboard

router = Router()


async def show_main_menu(message: types.Message, state: FSMContext) -> None:
    """Display the main menu with like statistics."""
    await state.clear()
    if message.from_user is None:
        return

    sent, received = await get_like_stats(message.from_user.id)
    text = (
        "<b>Главное меню</b>\n\n"
        f"❤️ Отправлено лайков: {sent}\n"
        f"💌 Получено лайков: {received}"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu")
async def callback_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Return to main menu from inline callbacks."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import handlers.menu; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add handlers/menu.py && git commit -m "feat(menu): add main menu with like stats"
```

---

### Task 10: Create handlers/profile.py

**Files:**
- Create: `handlers/profile.py`

- [ ] **Step 1: Create `handlers/profile.py`**

```python
# handlers/profile.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MIN_AGE
from database import get_user, update_user
from handlers.menu import show_main_menu
from keyboards import (
    build_interests_keyboard,
    goal_keyboard,
    looking_for_keyboard,
    profile_edit_keyboard,
)
from services.profile import format_profile
from states import EditProfile

router = Router()


@router.message(F.text == "📋 Моя анкета")
async def show_my_profile(message: types.Message, state: FSMContext) -> None:
    """Show the user's own profile with edit options."""
    await state.clear()
    if message.from_user is None:
        return

    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Анкета не найдена. Начни регистрацию с /start.")
        return

    text = format_profile(user, title="📋 Твоя анкета")
    await message.answer(
        text,
        reply_markup=profile_edit_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("edit:"))
async def start_edit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start editing a specific profile field."""
    if callback.message is None or callback.from_user is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    field = callback.data.split(":", 1)[1]

    if field == "age":
        await callback.message.edit_text("Введи новый возраст:")
        await state.set_state(EditProfile.age)
    elif field == "name":
        await callback.message.edit_text("Введи новое имя:")
        await state.set_state(EditProfile.name)
    elif field == "looking_for":
        await callback.message.edit_text(
            "Кого ты ищешь?", reply_markup=looking_for_keyboard()
        )
        await state.set_state(EditProfile.looking_for)
    elif field == "goal":
        await callback.message.edit_text("Что ты ищешь?", reply_markup=goal_keyboard())
        await state.set_state(EditProfile.goal)
    elif field == "interests":
        user = await get_user(callback.from_user.id)
        selected = set()
        if user and user.get("interests"):
            selected = {i.strip() for i in user["interests"].split(",") if i.strip()}
        await state.update_data(interests=list(selected))
        await callback.message.edit_text(
            "Выбери новые увлечения (минимум 3):",
            reply_markup=build_interests_keyboard(selected),
        )
        await state.set_state(EditProfile.interests)
    elif field == "photo":
        await callback.message.edit_text("Отправь новое фото:")
        await state.set_state(EditProfile.photo)
    else:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return

    await callback.answer()


@router.message(EditProfile.age)
async def edit_age(message: types.Message, state: FSMContext) -> None:
    """Validate and save new age."""
    if not message.text or not message.text.isdigit():
        await message.answer("Введи возраст числом.")
        return
    age = int(message.text)
    if age < MIN_AGE:
        await message.answer(f"Минимальный возраст — {MIN_AGE} лет.")
        return

    if message.from_user is None:
        return
    await update_user(message.from_user.id, age=age)
    await message.answer("Возраст обновлён.")
    await show_main_menu(message, state)


@router.message(EditProfile.name)
async def edit_name(message: types.Message, state: FSMContext) -> None:
    """Save new name."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое.")
        return

    if message.from_user is None:
        return
    await update_user(message.from_user.id, name=name)
    await message.answer("Имя обновлено.")
    await show_main_menu(message, state)


@router.callback_query(F.data.startswith("looking_for:"), EditProfile.looking_for)
async def edit_looking_for(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save new looking_for preference."""
    if callback.from_user is None:
        await callback.answer("Ошибка: пользователь не определён.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    await update_user(callback.from_user.id, looking_for=value)
    await callback.answer("Кого ищешь — обновлено.")
    await show_main_menu(callback.message, state)


@router.callback_query(F.data.startswith("goal:"), EditProfile.goal)
async def edit_goal(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save new goal."""
    if callback.from_user is None:
        await callback.answer("Ошибка: пользователь не определён.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    await update_user(callback.from_user.id, goal=value)
    await callback.answer("Цель обновлена.")
    await show_main_menu(callback.message, state)


@router.callback_query(F.data.startswith("interest:"), EditProfile.interests)
async def edit_toggle_interest(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle interest selection while editing."""
    item = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("interests", []))

    if item in selected:
        selected.remove(item)
    else:
        selected.add(item)

    await state.update_data(interests=list(selected))
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_reply_markup(
        reply_markup=build_interests_keyboard(selected)
    )
    await callback.answer()


@router.callback_query(F.data == "interest_done", EditProfile.interests)
async def edit_finish_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Validate and save edited interests."""
    data = await state.get_data()
    selected = data.get("interests", [])
    if len(selected) < 3:
        await callback.answer("Выбери минимум 3 увлечения.", show_alert=True)
        return

    if callback.from_user is None:
        await callback.answer("Ошибка: пользователь не определён.", show_alert=True)
        return
    await update_user(callback.from_user.id, interests=selected)
    await callback.answer("Интересы обновлены.")
    await show_main_menu(callback.message, state)


@router.message(EditProfile.photo, F.photo)
async def edit_photo(message: types.Message, state: FSMContext) -> None:
    """Save new photo."""
    if message.from_user is None:
        return
    photo_id = message.photo[-1].file_id
    await update_user(message.from_user.id, photo_file_id=photo_id)
    await message.answer("Фото обновлено.")
    await show_main_menu(message, state)


@router.message(EditProfile.photo)
async def edit_photo_wrong(message: types.Message) -> None:
    """Handle non-photo input while editing photo."""
    await message.answer("Пожалуйста, отправь фотографию.")
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import handlers.profile; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add handlers/profile.py && git commit -m "feat(profile): add view and edit profile handlers"
```

---

### Task 11: Create handlers/browse.py

**Files:**
- Create: `handlers/browse.py`

- [ ] **Step 1: Create `handlers/browse.py`**

```python
# handlers/browse.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from database import (
    add_like,
    add_view,
    get_all_users,
    get_user,
    get_viewed_ids,
    has_like,
)
from handlers.menu import show_main_menu
from keyboards import browse_keyboard, write_link_keyboard
from services.matching import filter_candidates, score_candidates
from services.profile import format_browse_card, format_profile

router = Router()


async def _show_next_profile(message: types.Message, state: FSMContext) -> None:
    """Show the next candidate from the feed."""
    if message.from_user is None:
        return

    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала пройди регистрацию: /start")
        return

    candidates = await get_all_users()
    viewed_ids = await get_viewed_ids(message.from_user.id)
    filtered = filter_candidates(user, candidates, viewed_ids)
    scored = score_candidates(user, filtered)

    if not scored:
        await message.answer(
            "Пока нет подходящих анкет. Попробуй позже.",
            reply_markup=browse_keyboard(),
        )
        await state.clear()
        return

    candidate, compatibility = scored[0]
    await state.update_data(
        current_candidate_id=candidate["user_id"],
        current_compatibility=compatibility,
    )

    text = format_browse_card(candidate, compatibility)
    photo_id = candidate.get("photo_file_id")

    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=browse_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=browse_keyboard(),
            parse_mode="HTML",
        )


@router.message(F.text == "🔍 Смотреть анкеты")
async def start_browse(message: types.Message, state: FSMContext) -> None:
    """Start browsing profiles."""
    await state.clear()
    await _show_next_profile(message, state)


@router.callback_query(F.data == "browse:skip")
async def browse_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip current profile and show the next one."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    data = await state.get_data()
    candidate_id = data.get("current_candidate_id")
    if candidate_id:
        await add_view(callback.from_user.id, candidate_id)

    await callback.message.delete()
    await _show_next_profile(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "browse:like")
async def browse_like(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Like current profile and handle mutual match."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    data = await state.get_data()
    candidate_id = data.get("current_candidate_id")
    compatibility = data.get("current_compatibility", 0)
    if candidate_id is None:
        await callback.answer("Ошибка: анкета не выбрана.", show_alert=True)
        return

    await add_view(callback.from_user.id, candidate_id)
    await add_like(callback.from_user.id, candidate_id)

    is_mutual = await has_like(candidate_id, callback.from_user.id)
    if is_mutual:
        await _notify_mutual_match(
            callback.message,
            liker_id=callback.from_user.id,
            liked_id=candidate_id,
        )
    else:
        await callback.answer("Лайк отправлен! ❤️")

    await callback.message.delete()
    await _show_next_profile(callback.message, state)


async def _notify_mutual_match(
    message: types.Message, liker_id: int, liked_id: int
) -> None:
    """Send mutual match notifications to both users."""
    liker = await get_user(liker_id)
    liked = await get_user(liked_id)
    if not liker or not liked:
        return

    liker_text = (
        "<b>💞 Взаимный лайк!</b>\n\n"
        + format_profile(liked, title="📋 Анкета")
    )
    liked_text = (
        "<b>💞 Взаимный лайк!</b>\n\n"
        + format_profile(liker, title="📋 Анкета")
    )

    await message.bot.send_message(
        chat_id=liker_id,
        text=liker_text,
        reply_markup=write_link_keyboard(liked.get("username"), liked_id),
        parse_mode="HTML",
    )
    await message.bot.send_message(
        chat_id=liked_id,
        text=liked_text,
        reply_markup=write_link_keyboard(liker.get("username"), liker_id),
        parse_mode="HTML",
    )
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import handlers.browse; print('ok')"
```

Expected: `ok` (may warn about circular import with profile; resolved by import order in main).

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add handlers/browse.py && git commit -m "feat(browse): add profile feed with like/skip and mutual match"
```

---

### Task 12: Create handlers/likes.py

**Files:**
- Create: `handlers/likes.py`

- [ ] **Step 1: Create `handlers/likes.py`**

```python
# handlers/likes.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from database import add_like, get_user
from handlers.browse import _notify_mutual_match
from handlers.menu import show_main_menu
from keyboards import like_response_keyboard
from services.profile import format_profile

router = Router()


@router.message(F.text == "❤️ Мои лайки")
async def show_likes(message: types.Message, state: FSMContext) -> None:
    """Show the most recent incoming like."""
    await state.clear()
    if message.from_user is None:
        return

    from database import has_like

    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала пройди регистрацию: /start")
        return

    # Find one incoming like not yet reciprocated or skipped.
    all_users = await get_all_users()
    liker_id = None
    for candidate in all_users:
        cid = candidate["user_id"]
        if cid == message.from_user.id:
            continue
        if await has_like(cid, message.from_user.id):
            if not await has_like(message.from_user.id, cid):
                liker_id = cid
                break

    if liker_id is None:
        await message.answer("У тебя пока нет новых лайков.")
        return

    liker = await get_user(liker_id)
    if liker is None:
        await message.answer("Анкета лайкнувшего не найдена.")
        return

    text = "<b>💌 Тебя лайкнули!</b>\n\n" + format_profile(liker, title="📋 Анкета")
    photo_id = liker.get("photo_file_id")
    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=like_response_keyboard(liker_id),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=like_response_keyboard(liker_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("like_back:"))
async def like_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Reciprocate a like."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    liker_id = int(callback.data.split(":", 1)[1])
    await add_like(callback.from_user.id, liker_id)
    await _notify_mutual_match(
        callback.message,
        liker_id=callback.from_user.id,
        liked_id=liker_id,
    )
    await callback.message.delete()
    await show_main_menu(callback.message, state)


@router.callback_query(F.data.startswith("like_skip:"))
async def like_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip an incoming like."""
    if callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()
```

- [ ] **Step 2: Verify imports**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import handlers.likes; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add handlers/likes.py && git commit -m "feat(likes): add incoming likes and like-back flow"
```

---

### Task 13: Update Entry Point and Wire Routers

**Files:**
- Modify: `znakomstvabot.py`

- [ ] **Step 1: Replace `znakomstvabot.py` content**

```python
# znakomstvabot.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import browse, common, likes, menu, profile, registration


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_routers(
        common.router,
        registration.router,
        menu.router,
        profile.router,
        browse.router,
        likes.router,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify the bot starts without errors (will wait for network)**

Run a quick import check first:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import znakomstvabot; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git add znakomstvabot.py && git commit -m "feat(bot): wire all routers in entry point"
```

---

### Task 14: Final Import and Syntax Checks

**Files:**
- All project files

- [ ] **Step 1: Run full import check**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "
import config
import database
import states
import keyboards
import services.profile
import services.matching
import handlers.common
import handlers.registration
import handlers.menu
import handlers.profile
import handlers.browse
import handlers.likes
import znakomstvabot
print('all imports ok')
"
```

Expected: `all imports ok`

- [ ] **Step 2: Run unit tests**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -m pytest tests/test_matching.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && git commit -m "chore: verify imports and tests"
```

---

### Task 15: End-to-End Test in Telegram

**Files:**
- `config.py` (ensure token is present)

- [ ] **Step 1: Confirm the real bot token is in `config.py`**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import config; print('token length:', len(config.BOT_TOKEN))"
```

Expected: token length > 10 (do not print the token itself).

- [ ] **Step 2: Start the bot in background**

Run:

```bash
cd /c/Users/antpl/PycharmProjects/PythonProject && .venv/Scripts/python.exe znakomstvabot.py
```

Leave it running. If needed, use `Bash(run_in_background=true)`.

- [ ] **Step 3: Test registration flow in Telegram**

1. Send `/start` to the bot.
2. Expand the policy block, press «Согласен».
3. Enter age ≥ 16.
4. Enter name.
5. Select gender.
6. Select who you are looking for.
7. Select goal.
8. Select at least 3 interests, press «Готово».
9. Send photo or skip.
10. Verify main menu appears with like stats.

- [ ] **Step 4: Test profile editing**

1. Press «📋 Моя анкета».
2. Press «✏️ Цель» and change it.
3. Verify main menu reappears.

- [ ] **Step 5: Test browsing and likes**

1. Register a second test account.
2. From first account press «🔍 Смотреть анкеты».
3. Like the second account.
4. From second account press «❤️ Мои лайки».
5. Press «Лайк в ответ».
6. Both accounts should receive mutual match messages with «Написать» button.

- [ ] **Step 6: Stop the bot**

Use Ctrl+C or `TaskStop` if running in background.

- [ ] **Step 7: Commit test notes (optional)**

If any fixes were needed during testing, commit them.

---

## Self-Review

**Spec coverage:**
- ✅ Reset DB and new schema — Task 1
- ✅ Expandable privacy policy — Task 5
- ✅ Registration with gender/looking_for/goal — Task 6
- ✅ Main menu with stats — Task 9
- ✅ My profile view/edit — Task 10
- ✅ Browse feed with compatibility — Tasks 8, 11
- ✅ Likes and mutual likes — Tasks 11, 12
- ✅ UI formatting — Tasks 7, 10, 11, 12

**Placeholder scan:** No TBD/TODO/"implement later" found.

**Type consistency:**
- `user_id` is always `int`.
- `interests` stored as comma-separated string, parsed with `_parse_interests`.
- `calculate_compatibility` expects dicts with keys `age`, `goal`, `interests`.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-20-dating-bot-extension-plan.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach do you prefer?
