# Город, фильтры ленты и улучшение алгоритма — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в бота знакомств поле города при регистрации, фильтры возраста/города в настройках и небольшой бонус совместимости за совпадение города.

**Architecture:** Новые поля хранятся в SQLite-таблице `users`. Валидация города вынесена в отдельный сервис. Фильтры применяются в `services/matching.py`, а UI фильтров — в `handlers/settings.py` с inline-клавиатурой. Скоринг дополняется городским бонусом без изменения текущих весов.

**Tech Stack:** Python 3.11+, aiogram 3.x, aiosqlite, pytest.

---

## File structure

| File | Responsibility |
|------|----------------|
| `database.py` | Схема БД, `add_user`, `update_user`, новые функции фильтров/города. |
| `states.py` | Новое состояние `Registration.city`. |
| `services/city_validation.py` | Мягкая валидация и нормализация названия города. |
| `services/matching.py` | Применение фильтров и бонус за совпадение города. |
| `services/profile.py` | Отображение города в анкете. |
| `handlers/registration.py` | Шаг ввода города в регистрации. |
| `handlers/settings.py` | Экран и управление фильтрами ленты. |
| `keyboards.py` | Клавиатуры для фильтров и обновлённое меню настроек. |
| `tests/test_city_validation.py` | Тесты валидации города. |
| `tests/test_matching.py` | Тесты фильтров и скоринга. |
| `tests/test_registration.py` | Обновлённый тест регистрации. |

---

### Task 1: Add database schema and accessor functions

**Files:**
- Modify: `database.py:12-24`
- Modify: `database.py:62-93`
- Modify: `database.py:107-152`
- Create: `tests/test_database_filters.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_database_filters.py`:

```python
import asyncio
import os

import database
from database import init_db, add_user, get_user, update_user_filters, get_user_filters

TEST_DB = "test_filters.db"
ORIGINAL_DB_PATH = database.DB_PATH


def _setup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    database.DB_PATH = TEST_DB
    asyncio.run(init_db())


def _teardown():
    database.DB_PATH = ORIGINAL_DB_PATH
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


async def _add_sample_user(user_id: int, city: str | None = None):
    await add_user(
        user_id=user_id,
        username=None,
        age=25,
        name="Alice",
        gender="female",
        looking_for="male",
        goal="relationship",
        interests=["Dota 2", "Аниме"],
        photo_file_id=None,
        city=city,
    )


def test_user_stores_city():
    _setup()
    try:
        asyncio.run(_add_sample_user(1, "Москва"))
        user = asyncio.run(get_user(1))
        assert user["city"] == "Москва"
    finally:
        _teardown()


def test_update_user_filters():
    _setup()
    try:
        asyncio.run(_add_sample_user(2))
        asyncio.run(update_user_filters(2, min_age=20, max_age=30, only_my_city=True))
        filters = asyncio.run(get_user_filters(2))
        assert filters == {"min_age": 20, "max_age": 30, "only_my_city": True}
    finally:
        _teardown()
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_database_filters.py -v`

Expected: FAIL with `ImportError: cannot import name 'update_user_city'`.

- [ ] **Step 2: Update the schema**

Edit `database.py` — в `init_db` заменить определение `users`:

```python
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

- [ ] **Step 3: Add `city` parameter to `add_user`**

В сигнатуру `add_user` добавить `city: str | None = None`. В `INSERT` добавить `city`:

```python
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
    city: str | None = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users
            (user_id, username, age, name, gender, looking_for, goal, interests, photo_file_id, city, notifications_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
                city,
            ),
        )
        await db.commit()
```

- [ ] **Step 4: Extend `update_user` with city and filters**

В `update_user` добавить параметры:

```python
async def update_user(
    user_id: int,
    *,
    age: int | None = None,
    name: str | None = None,
    looking_for: str | None = None,
    goal: str | None = None,
    interests: list[str] | None = None,
    photo_file_id: str | None = None,
    notifications_enabled: bool | None = None,
    city: str | None = None,
    filter_min_age: int | None = None,
    filter_max_age: int | None = None,
    filter_only_my_city: bool | None = None,
) -> None:
```

Добавить в тело:

```python
if city is not None:
    fields.append("city = ?")
    values.append(city)
if filter_min_age is not None:
    fields.append("filter_min_age = ?")
    values.append(filter_min_age)
if filter_max_age is not None:
    fields.append("filter_max_age = ?")
    values.append(filter_max_age)
if filter_only_my_city is not None:
    fields.append("filter_only_my_city = ?")
    values.append(1 if filter_only_my_city else 0)
```

- [ ] **Step 5: Add dedicated filter functions**

В конец `database.py` добавить:

```python
async def update_user_city(user_id: int, city: str | None) -> None:
    await update_user(user_id, city=city)


async def update_user_filters(
    user_id: int, *, min_age: int, max_age: int, only_my_city: bool
) -> None:
    await update_user(
        user_id,
        filter_min_age=min_age,
        filter_max_age=max_age,
        filter_only_my_city=only_my_city,
    )


async def get_user_filters(user_id: int) -> dict:
    user = await get_user(user_id)
    if not user:
        return {"min_age": 16, "max_age": 100, "only_my_city": False}
    return {
        "min_age": user.get("filter_min_age", 16),
        "max_age": user.get("filter_max_age", 100),
        "only_my_city": bool(user.get("filter_only_my_city", 0)),
    }
```

- [ ] **Step 6: Run the new tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_database_filters.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add database.py tests/test_database_filters.py
git commit -m "feat(db): add city and feed filters columns"
```

---

### Task 2: Implement city validation utility

**Files:**
- Create: `services/city_validation.py`
- Create: `tests/test_city_validation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_city_validation.py`:

```python
import pytest

from services.city_validation import is_valid_city, normalize_city


def test_normalize_city():
    assert normalize_city("  москва ") == "Москва"
    assert normalize_city("САНКТ-ПЕТЕРБУРГ") == "Санкт-Петербург"


def test_valid_city():
    assert is_valid_city("Москва") is True
    assert is_valid_city("Санкт-Петербург") is True
    assert is_valid_city("Нижний Новгород") is True


def test_invalid_city_too_short():
    assert is_valid_city("Аб") is False


def test_invalid_city_numbers():
    assert is_valid_city("Москва123") is False


def test_invalid_city_spam():
    assert is_valid_city("фффф") is False
    assert is_valid_city("asdf") is False


def test_invalid_city_only_symbols():
    assert is_valid_city("---") is False
    assert is_valid_city("   ") is False
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_city_validation.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.city_validation'`.

- [ ] **Step 2: Implement the validator**

Create `services/city_validation.py`:

```python
import re

_SPAM_WORDS = {"asdf", "ffff", "фффф", "qwerty", "йцукен", "abc", "xyz"}
_CITY_RE = re.compile(r"^[A-Za-zА-Яа-яЁё\s\-]+$")


def normalize_city(raw: str) -> str:
    """Trim, collapse spaces, strip edge hyphens and title-case."""
    cleaned = " ".join(raw.split()).strip("- ")
    return cleaned.title()


def is_valid_city(raw: str) -> bool:
    """Soft validation: reject obvious garbage but accept any real-looking city name."""
    if not raw:
        return False
    cleaned = normalize_city(raw)
    if len(cleaned) < 3 or len(cleaned) > 50:
        return False
    if not _CITY_RE.match(cleaned):
        return False
    if cleaned.lower() in _SPAM_WORDS:
        return False
    if not re.search(r"[A-Za-zА-Яа-яЁё]", cleaned):
        return False
    return True
```

- [ ] **Step 3: Run tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_city_validation.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/city_validation.py tests/test_city_validation.py
git commit -m "feat(services): add city validation utility"
```

---

### Task 3: Add city step to registration

**Files:**
- Modify: `states.py:6-15`
- Modify: `handlers/registration.py:138-159`
- Modify: `handlers/registration.py:203-240`
- Modify: `tests/test_registration.py:31-59`

- [ ] **Step 1: Add the state**

Edit `states.py`:

```python
class Registration(StatesGroup):
    policy = State()
    age = State()
    name = State()
    gender = State()
    looking_for = State()
    goal = State()
    interests = State()
    city = State()
    photo = State()
```

- [ ] **Step 2: Update registration test**

Edit `tests/test_registration.py`:

```python
state.get_data = AsyncMock(
    return_value={
        "age": 20,
        "name": "Alice",
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": ["Dota 2", "Аниме", "Кино"],
        "city": "Москва",
    }
)
```

Add assertion:

```python
assert captured["city"] == "Москва"
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_registration.py -v`

Expected: FAIL because `add_user` receives unexpected `city` keyword.

- [ ] **Step 3: Insert city step after interests**

Edit `handlers/registration.py`. В `finish_interests` заменить переход на фото:

```python
@router.callback_query(F.data == "interest_done", Registration.interests)
async def finish_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
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
        "🏙️ Введи свой город (Россия):"
    )
    await state.set_state(Registration.city)
    await callback.answer()
```

- [ ] **Step 4: Add city handler**

В `handlers/registration.py` после `finish_interests` добавить:

```python
@router.message(Registration.city)
async def process_city(message: types.Message, state: FSMContext) -> None:
    """Validate city and move to the photo step."""
    from services.city_validation import is_valid_city, normalize_city

    raw = message.text.strip() if message.text else ""
    if not is_valid_city(raw):
        await message.answer(
            "⚠️ Название города не похоже на настоящее. "
            "Введи город ещё раз (только буквы)."
        )
        return

    await state.update_data(city=normalize_city(raw))
    await message.answer(
        "Отправь свою фотографию. Это повысит количество лайков. "
        "Если не хочешь — нажми «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )
    await state.set_state(Registration.photo)
```

- [ ] **Step 5: Pass city to `_save_profile` and `add_user`**

В `_save_profile`:

```python
required_fields = ("age", "name", "gender", "looking_for", "goal", "interests", "city")
```

И в вызов `add_user`:

```python
await add_user(
    user_id=user_id,
    username=username,
    age=data["age"],
    name=data["name"],
    gender=data["gender"],
    looking_for=data["looking_for"],
    goal=data["goal"],
    interests=sorted(data["interests"]),
    photo_file_id=photo_id,
    city=data["city"],
)
```

- [ ] **Step 6: Run registration tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_registration.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add states.py handlers/registration.py tests/test_registration.py
git commit -m "feat(registration): add city step"
```

---

### Task 4: Add filters UI to settings

**Files:**
- Modify: `keyboards.py:156-167`
- Modify: `handlers/settings.py`
- Create: `tests/test_settings_filters.py`

- [ ] **Step 1: Write the failing test for filter keyboard**

Create `tests/test_settings_filters.py`:

```python
from keyboards import filters_keyboard, settings_keyboard


def test_settings_keyboard_has_filters_button():
    kb = settings_keyboard(True)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🔍 Фильтры ленты" in texts


def test_filters_keyboard_structure():
    kb = filters_keyboard(min_age=20, max_age=30, only_my_city=True)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("20" in t and "30" in t for t in texts)
    assert any("Только мой город" in t for t in texts)
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_settings_filters.py -v`

Expected: FAIL with `ImportError: cannot import name 'filters_keyboard'`.

- [ ] **Step 2: Update `settings_keyboard`**

В `keyboards.py` заменить `settings_keyboard`:

```python
def settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Keyboard for the settings screen."""
    if notifications_enabled:
        toggle_text = "🔔 Уведомления о лайках: включены (выключить)"
    else:
        toggle_text = "🔕 Уведомления о лайках: выключены (включить)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data="settings:toggle")],
            [InlineKeyboardButton(text="🔍 Фильтры ленты", callback_data="settings:filters")],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )
```

- [ ] **Step 3: Add `filters_keyboard`**

В `keyboards.py` после `settings_keyboard` добавить:

```python
def filters_keyboard(min_age: int, max_age: int, only_my_city: bool) -> InlineKeyboardMarkup:
    """Keyboard for configuring feed filters."""
    city_text = "🏙️ Только мой город" if only_my_city else "🌍 Любой город"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖ Мин", callback_data="filter:min_age:-1"),
                InlineKeyboardButton(text=f"Возраст: от {min_age} до {max_age}", callback_data="noop"),
                InlineKeyboardButton(text="➕ Мин", callback_data="filter:min_age:+1"),
            ],
            [
                InlineKeyboardButton(text="➖ Макс", callback_data="filter:max_age:-1"),
                InlineKeyboardButton(text="➕ Макс", callback_data="filter:max_age:+1"),
            ],
            [InlineKeyboardButton(text=city_text, callback_data="filter:toggle_city")],
            [InlineKeyboardButton(text="↩️ Сбросить", callback_data="filter:reset")],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="menu:settings")],
        ]
    )
```

- [ ] **Step 4: Run keyboard tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_settings_filters.py -v`

Expected: PASS.

- [ ] **Step 5: Add filter handlers in settings.py**

В `handlers/settings.py` обновить импорты:

```python
from database import (
    get_notifications_enabled,
    set_notifications_enabled,
    get_user_filters,
    update_user_filters,
)
from keyboards import filters_keyboard, settings_keyboard
from config import MIN_AGE, MAX_AGE
```

Добавить вспомогательную функцию:

```python
def _clamp_age(value: int) -> int:
    return max(MIN_AGE, min(MAX_AGE, value))
```

Добавить обработчики:

```python
@router.callback_query(F.data == "settings:filters")
async def open_filters(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Open the feed filters screen."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    await state.clear()
    filters = await get_user_filters(callback.from_user.id)
    text = (
        "<b>🔍 Фильтры ленты</b>\n\n"
        f"Возраст: от {filters['min_age']} до {filters['max_age']}\n"
        f"Город: {'только мой' if filters['only_my_city'] else 'любой'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=filters_keyboard(
            filters["min_age"], filters["max_age"], filters["only_my_city"]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter:"))
async def adjust_filter(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle filter adjustment buttons."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    user_id = callback.from_user.id
    filters = await get_user_filters(user_id)
    min_age = filters["min_age"]
    max_age = filters["max_age"]
    only_my_city = filters["only_my_city"]

    action = callback.data.split(":", 1)[1]

    if action == "toggle_city":
        only_my_city = not only_my_city
    elif action == "reset":
        min_age = MIN_AGE
        max_age = MAX_AGE
        only_my_city = False
    elif action.startswith("min_age:"):
        delta = 1 if action.endswith("+1") else -1
        min_age = _clamp_age(min_age + delta)
        if min_age > max_age:
            max_age = min_age
    elif action.startswith("max_age:"):
        delta = 1 if action.endswith("+1") else -1
        max_age = _clamp_age(max_age + delta)
        if max_age < min_age:
            min_age = max_age

    await update_user_filters(
        user_id,
        min_age=min_age,
        max_age=max_age,
        only_my_city=only_my_city,
    )

    text = (
        "<b>🔍 Фильтры ленты</b>\n\n"
        f"Возраст: от {min_age} до {max_age}\n"
        f"Город: {'только мой' if only_my_city else 'любой'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=filters_keyboard(min_age, max_age, only_my_city),
        parse_mode="HTML",
    )
    await callback.answer("Фильтры обновлены.")
```

- [ ] **Step 6: Run settings tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_settings_filters.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add keyboards.py handlers/settings.py tests/test_settings_filters.py
git commit -m "feat(settings): add feed filters UI"
```

---

### Task 5: Update matching algorithm

**Files:**
- Modify: `services/matching.py`
- Modify: `tests/test_matching.py`

- [ ] **Step 1: Write failing tests for filters and city bonus**

Append to `tests/test_matching.py`:

```python
from services.matching import filter_candidates


def test_filter_by_age_range():
    me = {"user_id": 1, "age": 25, "gender": "male", "looking_for": "female",
          "filter_min_age": 22, "filter_max_age": 28, "filter_only_my_city": 0, "city": "Москва"}
    candidates = [
        {"user_id": 2, "age": 21, "gender": "female", "looking_for": "male", "city": "Москва"},
        {"user_id": 3, "age": 24, "gender": "female", "looking_for": "male", "city": "Москва"},
        {"user_id": 4, "age": 30, "gender": "female", "looking_for": "male", "city": "Москва"},
    ]
    result = filter_candidates(me, candidates, set())
    assert [c["user_id"] for c in result] == [3]


def test_filter_only_my_city():
    me = {"user_id": 1, "age": 25, "gender": "male", "looking_for": "female",
          "filter_min_age": 16, "filter_max_age": 100, "filter_only_my_city": 1, "city": "Москва"}
    candidates = [
        {"user_id": 2, "age": 24, "gender": "female", "looking_for": "male", "city": "СПб"},
        {"user_id": 3, "age": 24, "gender": "female", "looking_for": "male", "city": "Москва"},
    ]
    result = filter_candidates(me, candidates, set())
    assert [c["user_id"] for c in result] == [3]


def test_city_bonus_in_compatibility():
    base = {"age": 25, "goal": "relationship", "interests": "Dota 2", "city": "Москва"}
    same_city = {"age": 25, "goal": "relationship", "interests": "Dota 2", "city": "москва"}
    other_city = {"age": 25, "goal": "relationship", "interests": "Dota 2", "city": "СПб"}
    same_score = calculate_compatibility(base, same_city)
    other_score = calculate_compatibility(base, other_city)
    assert same_score - other_score == 10
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_matching.py -v`

Expected: FAIL because `filter_candidates` does not use filter fields yet and `calculate_compatibility` has no city bonus.

- [ ] **Step 2: Update `filter_candidates`**

Edit `services/matching.py`:

```python
def filter_candidates(me: dict, candidates: list[dict], viewed_ids: set[int]) -> list[dict]:
    """Return candidates matching filters, excluding self and already viewed."""
    min_age = me.get("filter_min_age", 16)
    max_age = me.get("filter_max_age", 100)
    only_my_city = bool(me.get("filter_only_my_city", 0))
    my_city = me.get("city")

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
        if candidate["age"] < min_age or candidate["age"] > max_age:
            continue
        if only_my_city and my_city and candidate.get("city", "").lower() != my_city.lower():
            continue
        results.append(candidate)
    return results
```

- [ ] **Step 3: Add city bonus to `calculate_compatibility`**

Edit `services/matching.py`:

```python
CITY_BONUS = 10


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

    goal_score = GOAL_WEIGHT if me["goal"] == candidate["goal"] else GOAL_MISMATCH_WEIGHT

    score = round(interest_score + age_score + goal_score)

    my_city = me.get("city")
    their_city = candidate.get("city")
    if my_city and their_city and my_city.lower() == their_city.lower():
        score = min(100, score + CITY_BONUS)

    return score
```

- [ ] **Step 4: Run matching tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_matching.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/matching.py tests/test_matching.py
git commit -m "feat(matching): apply feed filters and city compatibility bonus"
```

---

### Task 6: Show city in profile cards

**Files:**
- Modify: `services/profile.py:15-31`
- Create: `tests/test_profile.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_profile.py`:

```python
from services.profile import format_profile


def test_format_profile_shows_city():
    user = {
        "name": "Alice",
        "age": 25,
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": "Dota 2,Аниме",
        "city": "Москва",
    }
    text = format_profile(user)
    assert "📍 Город: Москва" in text


def test_format_profile_hides_missing_city():
    user = {
        "name": "Alice",
        "age": 25,
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": "Dota 2",
    }
    text = format_profile(user)
    assert "Город" not in text
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_profile.py -v`

Expected: FAIL because city line is not present.

- [ ] **Step 2: Update `format_profile`**

Edit `services/profile.py`:

```python
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

    city = user.get("city")
    if city:
        lines.append(f"<b>📍 Город:</b> {city}")

    return "\n".join(lines)
```

- [ ] **Step 3: Run profile tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_profile.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/profile.py tests/test_profile.py
git commit -m "feat(profile): display city in profile card"
```

---

### Task 7: Full test run and cleanup

- [ ] **Step 1: Run all tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v`

Expected: ALL PASS.

- [ ] **Step 2: Run lint/type check if configured**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m py_compile main.py znakomstvabot.py handlers/*.py services/*.py database.py states.py keyboards.py`

Expected: no syntax errors.

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "test: all tests pass for city and filters feature"
```

---

## Self-review

### Spec coverage

| Spec requirement | Task |
|------------------|------|
| Поле `city` в БД | Task 1 |
| Фильтры `filter_min_age`, `filter_max_age`, `filter_only_my_city` | Task 1 |
| Шаг ввода города в регистрации с валидацией | Task 2 + Task 3 |
| Фильтры в настройках | Task 4 |
| Применение фильтров в ленте | Task 5 |
| Бонус за совпадение города (+10) | Task 5 |
| Отображение города в анкете | Task 6 |
| Тесты | All tasks |

### Placeholder scan

No TBD/TODO/fill-in placeholders. Every step contains concrete code, file paths, and commands.

### Type consistency

- `city: str | None` used consistently in `add_user`, `update_user`, `_save_profile`.
- Filter field names (`filter_min_age`, `filter_max_age`, `filter_only_my_city`) match between DB schema, `update_user`, `get_user_filters`, and `filter_candidates`.
- `only_my_city` is a `bool` in Python, stored as `0/1` in SQLite.

### Potential gotchas

- The hardcoded age-diff ≤ 5 filter is intentionally removed and replaced by user's `filter_min_age`/`filter_max_age` defaults (16–100).
- `filter_only_my_city` only applies when the viewing user has a non-empty `city`.
- City comparison is case-insensitive and ignores leading/trailing whitespace.
- The `Registration.city` state is inserted before `Registration.photo`, so the existing photo skip path still works.
