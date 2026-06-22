# City Visibility in Browse Card and Profanity Moderation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the user's city in the browse feed card and reject profane/offensive words in display names and cities during registration.

**Architecture:** Add a small `services/moderation.py` service with a built-in word list and word-boundary regex checks. Wire it into the existing registration handlers for the name and city steps. Extend `services/profile.py` to conditionally render the city line in the browse card.

**Tech Stack:** Python 3.12, pytest, aiogram, aiosqlite.

---

## File map

| File | Responsibility |
|------|----------------|
| `services/moderation.py` | New module: normalize input and check for profanity using a built-in word list. |
| `services/profile.py` | Modify `format_browse_card` to include the city line. |
| `handlers/registration.py` | Add profanity checks in `process_name` and `process_city`. |
| `tests/test_moderation.py` | New tests for the moderation service. |
| `tests/test_profile.py` | Update tests for `format_browse_card` with and without city. |
| `tests/test_registration.py` | Add tests rejecting profane names/cities during registration. |

---

## Task 1: Create moderation service

**Files:**
- Create: `services/moderation.py`
- Test: `tests/test_moderation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_moderation.py`:

```python
import pytest

from services.moderation import contains_profanity, is_clean_city, is_clean_name


class TestContainsProfanity:
    def test_clean_text_returns_false(self):
        assert contains_profanity("Анна") is False
        assert contains_profanity("Москва") is False
        assert contains_profanity("Ivan") is False
        assert contains_profanity("London") is False

    def test_russian_profanity_detected(self):
        assert contains_profanity("блядь") is True

    def test_english_profanity_detected(self):
        assert contains_profanity("fuck") is True

    def test_case_insensitive(self):
        assert contains_profanity("БЛЯДЬ") is True
        assert contains_profanity("Fuck") is True

    def test_surrounding_whitespace_normalized(self):
        assert contains_profanity("  блядь  ") is True
        assert contains_profanity("Fuck ") is True

    def test_word_boundary_avoids_false_positives(self):
        # Assuming 'dick' is in the English list, Dickens should be allowed.
        assert contains_profanity("Dickens") is False


class TestIsCleanName:
    def test_clean_name(self):
        assert is_clean_name("Анна") is True

    def test_dirty_name(self):
        assert is_clean_name("блядь") is False


class TestIsCleanCity:
    def test_clean_city(self):
        assert is_clean_city("Москва") is True

    def test_dirty_city(self):
        assert is_clean_city("хуйгород") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_moderation.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.moderation'`.

- [ ] **Step 3: Write minimal implementation**

Create `services/moderation.py`:

```python
import re

# Built-in profanity list (Russian + English). Extend as needed.
_PROFANITY_WORDS = {
    # Russian
    "блядь", "блять", "сука", "суки", "хуй", "хуи", "хуёвый", "хуевый",
    "хуесос", "пизда", "пиздец", "ебать", "ебал", "ебёт", "ебет",
    "ёбарь", "ебарь", "ёбан", "ебан", "ебанутый", "ёбнутый", "пидор",
    "пидорас", "пидарас", "гандон", "гондон", "мудак", "мудила",
    "ублюдок", "тварь", "скотина", "шлюха", "проститутка", "курва",
    "член", "залупа", "дрочить", "дрочер",
    # English
    "fuck", "fucking", "fucker", "fucked", "shit", "shitty", "bitch",
    "whore", "slut", "cunt", "dick", "cock", "pussy", "asshole",
    "bastard",
}

# Pre-compile a single regex with word boundaries. Sort words by length descending
# so longer expressions are tried before shorter ones that they may contain.
_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(w) for w in sorted(_PROFANITY_WORDS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace/hyphens for consistent matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-+", "-", text)
    return text.strip(" -")


def contains_profanity(text: str) -> bool:
    """Return True if text contains a profane word as a whole word."""
    if not text:
        return False
    return bool(_PATTERN.search(_normalize(text)))


def is_clean_name(text: str) -> bool:
    """Return True if the display name is free of profanity."""
    return not contains_profanity(text)


def is_clean_city(text: str) -> bool:
    """Return True if the city name is free of profanity."""
    return not contains_profanity(text)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_moderation.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/moderation.py tests/test_moderation.py
git commit -m "feat: add profanity moderation service"
```

---

## Task 2: Show city in browse card

**Files:**
- Modify: `services/profile.py`
- Test: `tests/test_profile.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_profile.py` and append:

```python
from services.profile import format_browse_card


def test_browse_card_includes_city():
    user = {
        "name": "Анна",
        "age": 25,
        "goal": "relationship",
        "interests": "музыка, спорт",
        "city": "Москва",
    }
    text = format_browse_card(user, compatibility=80)
    assert "📍 Город: Москва" in text


def test_browse_card_omits_city_when_missing():
    user = {
        "name": "Анна",
        "age": 25,
        "goal": "relationship",
        "interests": "музыка, спорт",
        "city": None,
    }
    text = format_browse_card(user, compatibility=80)
    assert "📍 Город" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_profile.py::test_browse_card_includes_city tests/test_profile.py::test_browse_card_omits_city_when_missing -v
```

Expected: FAIL — "📍 Город: Москва" not found.

- [ ] **Step 3: Write minimal implementation**

Modify `services/profile.py` function `format_browse_card`:

```python
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

    city = user.get("city")
    if city:
        lines.append(f"📍 <b>Город:</b> {city}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_profile.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/profile.py tests/test_profile.py
git commit -m "feat: show city in browse card"
```

---

## Task 3: Wire moderation into registration

**Files:**
- Modify: `handlers/registration.py`
- Test: `tests/test_registration.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_registration.py` and append:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

from handlers.registration import process_city, process_name


def _make_state_with_data(data: dict):
    state = MagicMock()
    state.get_data = AsyncMock(return_value=data)
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    return state


def test_process_name_rejects_profanity():
    message = MagicMock()
    message.text = "блядь"
    message.answer = AsyncMock()

    state = MagicMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    asyncio.run(process_name(message, state))

    state.update_data.assert_not_called()
    message.answer.assert_awaited_once_with(
        "⚠️ Имя содержит недопустимые слова. Введи другое имя."
    )


def test_process_city_rejects_profanity():
    message = MagicMock()
    message.text = "хуйгород"
    message.answer = AsyncMock()

    state = _make_state_with_data(
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["music", "sport", "travel"],
        }
    )

    asyncio.run(process_city(message, state))

    state.update_data.assert_not_called()
    message.answer.assert_awaited_once_with(
        "⚠️ Название города содержит недопустимые слова. Введи город ещё раз."
    )
```

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_registration.py::test_process_name_rejects_profanity tests/test_registration.py::test_process_city_rejects_profanity -v
```

Expected: FAIL because the handlers do not yet return the profanity error messages.

- [ ] **Step 2: Implement moderation checks**

Modify `handlers/registration.py`:

Add import:
```python
from services.moderation import is_clean_city, is_clean_name
```

Update `process_name`:

```python
@router.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext) -> None:
    """Save the user's display name and move to gender selection."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи хотя бы 2 символа.")
        return

    if not is_clean_name(name):
        await message.answer("⚠️ Имя содержит недопустимые слова. Введи другое имя.")
        return

    await state.update_data(name=name)
    await message.answer(
        "Укажи свой пол:",
        reply_markup=gender_keyboard(),
    )
    await state.set_state(Registration.gender)
```

Update `process_city`:

```python
@router.message(Registration.city)
async def process_city(message: types.Message, state: FSMContext) -> None:
    """Validate city and move to the photo step."""
    raw = message.text.strip() if message.text else ""
    if not is_valid_city(raw):
        await message.answer(
            "⚠️ Название города не похоже на настоящее. "
            "Введи город ещё раз (только буквы)."
        )
        return

    normalized = normalize_city(raw)
    if not is_clean_city(normalized):
        await message.answer(
            "⚠️ Название города содержит недопустимые слова. Введи город ещё раз."
        )
        return

    await state.update_data(city=normalized)
    await message.answer(
        "Отправь свою фотографию. Это повысит количество лайков. "
        "Если не хочешь — нажми «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )
    await state.set_state(Registration.photo)
```

- [ ] **Step 3: Run test to verify it passes**

Run:
```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_registration.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add handlers/registration.py tests/test_registration.py
git commit -m "feat: wire profanity moderation into registration"
```

---

## Task 4: Full test run and final commit

- [ ] **Step 1: Run the full test suite**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat: city visibility in browse card and profanity moderation"
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Show city in `format_browse_card` | Task 2 |
| Built-in profanity list, word boundaries | Task 1 |
| Moderate name at registration | Task 3 |
| Moderate city at registration | Task 3 |
| Unit tests for moderation | Task 1 |
| Unit tests for browse card city | Task 2 |
| Unit tests for registration rejection | Task 3 |

No gaps identified.

## Placeholder scan

No TBD/TODO/fill-in-details found. All code and commands are concrete.

## Type consistency check

- `contains_profanity(text: str) -> bool` used in `is_clean_name` and `is_clean_city`.
- `is_clean_name(name: str) -> bool` and `is_clean_city(city: str) -> bool` match call sites.
- `format_browse_card(user: dict, compatibility: int) -> str` signature unchanged.
