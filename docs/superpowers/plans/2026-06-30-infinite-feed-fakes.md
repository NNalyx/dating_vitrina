# Infinite Feed: Fake Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the real-user feed is empty, generate realistic fake profiles on demand so the feed never ends. Likes/skips on fakes are visually normal but do not create matches, notifications, or stats.

**Architecture:** A pre-uploaded pool of synthetic avatars is stored under `data/fake_avatars/` with a `file_ids.json` cache of Telegram `file_id`s. A new generator service assembles fake names, cities, interests, bios, and avatars that match the current user's filters, inserts them as `is_fake=1` users with negative IDs, and the existing feed pipeline treats them like ordinary candidates.

**Tech Stack:** Python aiogram/aiohttp, SQLite, vanilla JS (no frontend changes required).

---

### File Structure

- `database.py` — add `bio` column; pass `bio` through `add_user`/`add_fake_user`/`update_user`.
- `services/fake_profile_generator.py` — name/city/interest/bio pools, avatar file-id picker, and batch generator.
- `scripts/prepare_fake_avatars.py` — one-time script to download synthetic faces and cache their Telegram `file_id`s.
- `data/fake_avatars/male/`, `female/`, `neutral/` — avatar image storage (ignored by git).
- `data/fake_avatars/file_ids.json` — cached Telegram file IDs (ignored by git).
- `web_routes.py` — feed fallback, fake-aware like/skip, exclude fakes from likes list.
- `tests/test_fake_feed.py` — tests for fallback generation, filters, like/skip behavior.

---

### Task 1: Add `bio` column and update DB helpers

**Files:**
- Modify: `database.py`
- Test: `tests/test_database_filters.py`

- [ ] **Step 1: Add `bio` column to schema and migration**

Add the column in the `CREATE TABLE` statement and add a standalone migration:

```python
# In init_db(), inside CREATE TABLE users add:
# bio TEXT,

# After the integer column migration loop, add:
try:
    await db.execute("ALTER TABLE users ADD COLUMN bio TEXT")
except sqlite3.OperationalError:
    pass
```

- [ ] **Step 2: Add `bio` to `add_user`**

Update the signature and SQL:

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
    is_fake: bool = False,
    bio: str | None = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users
            (user_id, username, age, name, gender, looking_for, goal, interests,
             photo_file_id, city, notifications_enabled, is_fake, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
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
                1 if is_fake else 0,
                bio,
            ),
        )
        await db.commit()
```

- [ ] **Step 3: Add `bio` to `update_user`**

Insert after the `filter_interests` block:

```python
if bio is not None:
    fields.append("bio = ?")
    values.append(bio)
```

And update the signature: `bio: str | None = None`.

- [ ] **Step 4: Add `bio` to `add_fake_user`**

Update signature and the call to `add_user`:

```python
async def add_fake_user(
    *,
    name: str,
    age: int,
    gender: str,
    looking_for: str,
    goal: str,
    interests: list[str],
    city: str | None = None,
    photo_file_id: str | None = None,
    bio: str | None = None,
) -> int:
    user_id = await get_next_fake_user_id()
    await add_user(
        user_id=user_id,
        username=None,
        age=age,
        name=name,
        gender=gender,
        looking_for=looking_for,
        goal=goal,
        interests=interests,
        photo_file_id=photo_file_id,
        city=city,
        is_fake=True,
        bio=bio,
    )
    return user_id
```

- [ ] **Step 5: Write the failing test**

Append to `tests/test_database_filters.py`:

```python
def test_add_user_stores_bio():
    _setup()
    try:
        asyncio.run(_add_sample_user(42))
        asyncio.run(update_user(42, bio="Люблю кофе и кино"))
        user = asyncio.run(get_user(42))
        assert user["bio"] == "Люблю кофе и кино"
    finally:
        _teardown()
```

- [ ] **Step 6: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_database_filters.py::test_add_user_stores_bio -v`
Expected: FAIL with an error about `bio` parameter or column.

- [ ] **Step 7: Run all DB tests to verify no regressions**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_database_filters.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add database.py tests/test_database_filters.py
git commit -m "feat(db): add bio column and pass it through user helpers"
```

---

### Task 2: Create avatar download/upload script

**Files:**
- Create: `scripts/prepare_fake_avatars.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create directory placeholders and gitignore**

Run:

```bash
mkdir -p data/fake_avatars/male data/fake_avatars/female data/fake_avatars/neutral
```

Add to `.gitignore`:

```gitignore
data/fake_avatars/**/*.jpg
data/fake_avatars/**/*.jpeg
data/fake_avatars/**/*.png
data/fake_avatars/file_ids.json
```

Create `data/fake_avatars/.gitkeep` so the folder structure is tracked:

```bash
touch data/fake_avatars/male/.gitkeep data/fake_avatars/female/.gitkeep data/fake_avatars/neutral/.gitkeep
```

Add exception to `.gitignore`:

```gitignore
!data/fake_avatars/**/.gitkeep
```

- [ ] **Step 2: Write the script**

Create `scripts/prepare_fake_avatars.py`:

```python
import asyncio
import json
import time
from pathlib import Path

import aiohttp
from aiogram import Bot

from config import BOT_TOKEN, OWNER_ID

AVATARS_DIR = Path("data/fake_avatars/neutral")
FILE_IDS_PATH = Path("data/fake_avatars/file_ids.json")
COUNT = 30


async def download_image(session: aiohttp.ClientSession, dest: Path) -> None:
    url = "https://thispersondoesnotexist.com/"
    async with session.get(url) as resp:
        resp.raise_for_status()
        dest.write_bytes(await resp.read())


async def upload_and_record(bot: Bot, path: Path, gender: str, records: list[dict]) -> None:
    with open(path, "rb") as f:
        msg = await bot.send_photo(chat_id=OWNER_ID, photo=f, disable_notification=True)
    file_id = msg.photo[-1].file_id
    records.append({"path": str(path), "gender": gender, "file_id": file_id})
    await asyncio.sleep(0.5)


async def main() -> None:
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    bot = Bot(token=BOT_TOKEN)
    records = []
    if FILE_IDS_PATH.exists():
        records = json.loads(FILE_IDS_PATH.read_text(encoding="utf-8"))
    existing_paths = {r["path"] for r in records}

    async with aiohttp.ClientSession() as session:
        for i in range(COUNT):
            dest = AVATARS_DIR / f"{i + 1:03d}.jpg"
            if str(dest) in existing_paths:
                continue
            await download_image(session, dest)
            await upload_and_record(bot, dest, "neutral", records)
            print(f"Uploaded {dest} -> {records[-1]['file_id']}")

    FILE_IDS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Commit script and folder structure**

```bash
git add scripts/prepare_fake_avatars.py .gitignore data/fake_avatars/.gitkeep
git commit -m "chore: add fake avatar download/upload script and storage layout"
```

---

### Task 3: Build fake profile generator service

**Files:**
- Create: `services/fake_profile_generator.py`
- Test: `tests/test_fake_generator.py`

- [ ] **Step 1: Create the generator module**

Create `services/fake_profile_generator.py`:

```python
import json
import random
from pathlib import Path

from config import INTEREST_CATEGORIES
from database import add_fake_user, get_user

AVATARS_DIR = Path("data/fake_avatars")
FILE_IDS_PATH = AVATARS_DIR / "file_ids.json"

ALL_INTERESTS = [item for _, _, items in INTEREST_CATEGORIES for item in items]

MALE_NAMES = [
    "Александр", "Максим", "Дмитрий", "Артём", "Иван", "Кирилл", "Никита", "Михаил",
    "Егор", "Матвей", "Андрей", "Илья", "Алексей", "Роман", "Владимир", "Павел",
]

FEMALE_NAMES = [
    "Анастасия", "Мария", "Анна", "Виктория", "Екатерина", "София", "Дарья", "Алиса",
    "Вероника", "Полина", "Елизавета", "Ксения", "Александра", "Ольга", "Татьяна", "Юлия",
]

CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Уфа", "Ростов-на-Дону",
    "Красноярск", "Воронеж", "Пермь", "Волгоград", "Краснодар",
]

GOAL_LABELS = {
    "relationship": "отношения",
    "friendship": "дружбу",
    "flirt": "флирт",
}

BIO_TEMPLATES = [
    "{name}, {age}. Живу в {city}. Увлекаюсь {interest1} и {interest2}. Ищу {goal}.",
    "Привет! Я из {city}. Люблю {interest1} и не представляю жизни без {interest2}. Хочу {goal}.",
    "{city}, {age} лет. Главные увлечения: {interest1}, {interest2}. Цель — {goal}.",
    "Люблю {interest1}, {interest2} и новые знакомства. Живу в {city}, ищу {goal}.",
    "{name}, {age}. Мой город — {city}. Увлекаюсь {interest1} и {interest2}. Ищу {goal}.",
    "Из {city}. Свободное время провожу за {interest1} и {interest2}. Хочу {goal}.",
    "{age} лет, {city}. Интересы: {interest1}, {interest2}. Ищу {goal}.",
    "Живу в {city}, увлекаюсь {interest1}. Также нравится {interest2}. Ищу {goal}.",
    "{name}. Люблю {interest1} и {interest2}. Из {city}, {age} лет. Цель — {goal}.",
    "{city}. {age} лет. {interest1} и {interest2} — то, что меня заводит. Ищу {goal}.",
]


def _load_file_ids() -> list[dict]:
    if not FILE_IDS_PATH.exists():
        return []
    return json.loads(FILE_IDS_PATH.read_text(encoding="utf-8"))


def pick_avatar_file_id(gender: str) -> str | None:
    file_ids = _load_file_ids()
    if not file_ids:
        return None
    gender_key = gender if gender in ("male", "female") else "neutral"
    candidates = [r for r in file_ids if r.get("gender") == gender_key]
    if not candidates:
        candidates = [r for r in file_ids if r.get("gender") == "neutral"]
    if not candidates:
        candidates = file_ids
    return random.choice(candidates)["file_id"]


def _pick_name(gender: str) -> str:
    pool = MALE_NAMES if gender == "male" else FEMALE_NAMES if gender == "female" else (MALE_NAMES + FEMALE_NAMES)
    return random.choice(pool)


def _choose_gender_and_looking_for(viewer: dict) -> tuple[str, str]:
    viewer_gender = viewer.get("gender", "other")
    viewer_looking = viewer.get("looking_for", "all")

    if viewer_looking == "male":
        gender = "male"
    elif viewer_looking == "female":
        gender = "female"
    else:
        gender = random.choice(["male", "female"])

    if viewer_gender in ("male", "female"):
        looking_for = viewer_gender
    else:
        looking_for = "all"

    return gender, looking_for


def _pick_age(viewer: dict) -> int:
    min_age = max(viewer.get("filter_min_age", 18), 18)
    max_age = min(viewer.get("filter_max_age", 35), 45)
    if min_age > max_age:
        max_age = min_age
    return random.randint(min_age, max_age)


def _pick_city(viewer: dict) -> str:
    only_my_city = bool(viewer.get("filter_only_my_city", 0))
    user_city = viewer.get("city")
    if only_my_city and user_city:
        return user_city
    if user_city and random.random() < 0.5:
        return user_city
    return random.choice(CITIES)


def _pick_goal(viewer: dict) -> str:
    user_goal = viewer.get("goal")
    if user_goal and random.random() < 0.7:
        return user_goal
    return random.choice(["relationship", "friendship", "flirt"])


def _pick_interests(viewer: dict) -> list[str]:
    filter_interests = bool(viewer.get("filter_interests", 0))
    user_interests = {i.strip() for i in (viewer.get("interests") or "").split(",") if i.strip()}

    if filter_interests and user_interests:
        overlap = random.sample(list(user_interests), min(2, len(user_interests)))
        extras = random.sample(ALL_INTERESTS, k=min(3, len(ALL_INTERESTS)))
        interests = list(dict.fromkeys(overlap + extras))
    else:
        interests = random.sample(ALL_INTERESTS, k=min(5, len(ALL_INTERESTS)))

    return interests[:5]


def _generate_bio(name: str, age: int, city: str, interests: list[str], goal: str) -> str:
    i1, i2 = random.sample(interests, min(2, len(interests)))
    goal_label = GOAL_LABELS.get(goal, goal)
    template = random.choice(BIO_TEMPLATES)
    return template.format(name=name, age=age, city=city, interest1=i1, interest2=i2, goal=goal_label)


async def generate_fake_profiles_batch(viewer: dict, count: int = 3) -> list[dict]:
    fakes = []
    for _ in range(count):
        gender, looking_for = _choose_gender_and_looking_for(viewer)
        name = _pick_name(gender)
        age = _pick_age(viewer)
        city = _pick_city(viewer)
        goal = _pick_goal(viewer)
        interests = _pick_interests(viewer)
        bio = _generate_bio(name, age, city, interests, goal)
        photo_file_id = pick_avatar_file_id(gender)

        user_id = await add_fake_user(
            name=name,
            age=age,
            gender=gender,
            looking_for=looking_for,
            goal=goal,
            interests=interests,
            city=city,
            photo_file_id=photo_file_id,
            bio=bio,
        )
        fakes.append(await get_user(user_id))
    return fakes
```

- [ ] **Step 2: Write tests for the generator**

Create `tests/test_fake_generator.py`:

```python
import asyncio
import os

import pytest

import database
from database import init_db, add_user
from services.fake_profile_generator import (
    _choose_gender_and_looking_for,
    _generate_bio,
    _pick_age,
    _pick_city,
    _pick_interests,
    generate_fake_profiles_batch,
)

TEST_DB = "test_fake_generator.db"
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


async def _add_viewer(user_id: int = 1):
    await add_user(
        user_id=user_id,
        username=None,
        age=22,
        name="Оля",
        gender="female",
        looking_for="male",
        goal="relationship",
        interests=["Аниме", "Dota 2", "Музыка"],
        city="Москва",
    )


def test_gender_matches_viewer_preference():
    viewer = {"gender": "female", "looking_for": "male"}
    gender, looking_for = _choose_gender_and_looking_for(viewer)
    assert gender == "male"
    assert looking_for == "female"


def test_age_respects_viewer_filters():
    viewer = {"filter_min_age": 20, "filter_max_age": 25}
    age = _pick_age(viewer)
    assert 20 <= age <= 25


def test_city_respects_only_my_city():
    viewer = {"filter_only_my_city": 1, "city": "Казань"}
    assert _pick_city(viewer) == "Казань"


def test_interests_overlap_when_filter_enabled():
    viewer = {
        "filter_interests": 1,
        "interests": "Аниме,Dota 2,Музыка",
    }
    interests = _pick_interests(viewer)
    assert any(i in {"Аниме", "Dota 2", "Музыка"} for i in interests)


def test_bio_is_uniqueish():
    bios = {
        _generate_bio("Аня", 22, "Москва", ["Аниме", "Dota 2", "Музыка"], "relationship")
        for _ in range(20)
    }
    assert len(bios) > 1


@pytest.mark.asyncio
async def test_generate_batch_creates_fake_users():
    await _add_viewer()
    viewer = await database.get_user(1)
    fakes = await generate_fake_profiles_batch(viewer, count=2)
    assert len(fakes) == 2
    for fake in fakes:
        assert fake["is_fake"] == 1
        assert fake["user_id"] < 0
        assert fake["bio"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_generator.py -v`
Expected: FAIL because module/file does not exist or functions missing.

- [ ] **Step 4: Implement module and run tests**

Create `services/fake_profile_generator.py` as shown.

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_generator.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/fake_profile_generator.py tests/test_fake_generator.py
git commit -m "feat: fake profile generator service"
```

---

### Task 4: Wire fake fallback into the feed endpoint

**Files:**
- Modify: `web_routes.py`
- Test: `tests/test_fake_feed.py`

- [ ] **Step 1: Modify `/api/feed` to fall back to fake generation**

In `web_routes.py` import the generator:

```python
from services.fake_profile_generator import generate_fake_profiles_batch
```

Update the feed endpoint:

```python
@routes.get("/api/feed")
async def feed(request: web.Request) -> web.Response:
    user = await _active_user(request)
    user_id = user["user_id"]

    candidates = await get_all_users()
    viewed_ids = await get_viewed_ids(user_id)
    filtered = filter_candidates(user, candidates, viewed_ids)
    scored = score_candidates(user, filtered)

    if not scored:
        await generate_fake_profiles_batch(user, count=3)
        candidates = await get_all_users()
        viewed_ids = await get_viewed_ids(user_id)
        filtered = filter_candidates(user, candidates, viewed_ids)
        scored = score_candidates(user, filtered)

    if not scored:
        return web.json_response({"done": True})

    candidate, compatibility = scored[0]
    return web.json_response({**candidate, "compatibility": compatibility})
```

- [ ] **Step 2: Write the failing feed fallback test**

Create `tests/test_fake_feed.py`:

```python
import re

import pytest

from tests.test_web_auth import _make_init_data


def _solve_captcha(question: str) -> str:
    match = re.match(r"(\d+)\s*([+\-])\s*(\d+)", question)
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    return str(a + b if op == "+" else a - b)


@pytest.fixture
async def client(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("database.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("config.BOT_TOKEN", "test_token_12345")
    monkeypatch.setattr("web_routes.BOT_TOKEN", "test_token_12345")
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    from database import init_db

    await init_db()
    from web_app import create_app

    app = create_app()
    return await aiohttp_client(app)


async def _register(client, user_id: int, gender: str, looking_for: str, city: str):
    from database import update_user

    captcha = await (await client.get("/api/captcha")).json()
    init_data = _make_init_data(user_id, "test_token_12345")
    payload = {
        "initData": init_data,
        "age": 22,
        "name": "Test",
        "gender": gender,
        "looking_for": looking_for,
        "goal": "relationship",
        "interests": ["Аниме", "Dota 2", "Музыка"],
        "city": city,
        "photo_file_id": None,
        "captcha_token": captcha["token"],
        "captcha_answer": _solve_captcha(captcha["question"]),
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 201, await resp.json()


async def test_feed_returns_fake_when_no_real_candidates(client, monkeypatch):
    monkeypatch.setattr(
        "services.fake_profile_generator.pick_avatar_file_id",
        lambda _gender: None,
    )
    await _register(client, 100, "female", "male", "Москва")

    init_data = _make_init_data(100, "test_token_12345")
    resp = await client.get("/api/feed", headers={"X-Init-Data": init_data})
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    assert data["is_fake"] == 1
    assert data["user_id"] < 0
    assert data["gender"] == "male"
    assert data["looking_for"] == "female"
    assert data["city"] == "Москва"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_feed.py::test_feed_returns_fake_when_no_real_candidates -v`
Expected: FAIL — feed returns `{"done": true}` because no fallback yet.

- [ ] **Step 4: Implement the fallback and run tests**

Apply the feed changes from Step 1.

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_feed.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web_routes.py tests/test_fake_feed.py
git commit -m "feat(feed): generate fake profiles when real feed is empty"
```

---

### Task 5: Make like/skip fake-aware

**Files:**
- Modify: `web_routes.py`
- Test: `tests/test_fake_feed.py`

- [ ] **Step 1: Update `feed_like` to ignore fake targets**

```python
@routes.post("/api/feed/{id}/like")
async def feed_like(request: web.Request) -> web.Response:
    user = await _active_user(request)
    user_id = user["user_id"]

    candidate_id = int(request.match_info["id"])
    candidate = await get_user(candidate_id)
    if candidate and candidate.get("is_fake"):
        await add_view(user_id, candidate_id)
        return web.json_response({"status": "ok", "mutual": False})

    await add_view(user_id, candidate_id)
    await add_like(user_id, candidate_id)

    is_mutual = await has_like(candidate_id, user_id)
    bot: Bot | None = request.app.get("bot")

    if is_mutual and bot:
        liker = await get_user(user_id)
        liked = await get_user(candidate_id)
        if liker and liked:
            await _send_match_notifications(bot, liker, liked)
    elif bot and await get_notifications_enabled(candidate_id):
        liker = await get_user(user_id)
        if liker:
            await _send_incoming_like(bot, liker, candidate_id)

    return web.json_response({"status": "ok", "mutual": is_mutual})
```

- [ ] **Step 2: Exclude fakes from the incoming likes list**

Update `/api/likes`:

```python
@routes.get("/api/likes")
async def likes(request: web.Request) -> web.Response:
    user = await _active_user(request)
    user_id = user["user_id"]

    result = []
    for candidate in await get_all_users():
        cid = candidate["user_id"]
        if cid == user_id or candidate.get("is_fake"):
            continue
        if await has_like(cid, user_id) and not await has_like(user_id, cid):
            result.append(candidate)
    return web.json_response(result)
```

- [ ] **Step 3: Add tests for fake like/skip behavior**

Append to `tests/test_fake_feed.py`:

```python
async def test_like_on_fake_does_not_create_match(client, monkeypatch):
    monkeypatch.setattr(
        "services.fake_profile_generator.pick_avatar_file_id",
        lambda _gender: None,
    )
    await _register(client, 101, "female", "male", "Москва")

    init_data = _make_init_data(101, "test_token_12345")
    feed_resp = await client.get("/api/feed", headers={"X-Init-Data": init_data})
    fake = await feed_resp.json()

    like_resp = await client.post(
        f"/api/feed/{fake['user_id']}/like",
        headers={"X-Init-Data": init_data},
    )
    data = await like_resp.json()
    assert data["status"] == "ok"
    assert data["mutual"] is False

    likes_resp = await client.get("/api/likes", headers={"X-Init-Data": init_data})
    assert await likes_resp.json() == []


async def test_skip_on_fake_records_view(client, monkeypatch):
    monkeypatch.setattr(
        "services.fake_profile_generator.pick_avatar_file_id",
        lambda _gender: None,
    )
    await _register(client, 102, "female", "male", "Москва")

    init_data = _make_init_data(102, "test_token_12345")
    feed_resp = await client.get("/api/feed", headers={"X-Init-Data": init_data})
    fake = await feed_resp.json()

    skip_resp = await client.post(
        f"/api/feed/{fake['user_id']}/skip",
        headers={"X-Init-Data": init_data},
    )
    assert skip_resp.status == 200

    second_resp = await client.get("/api/feed", headers={"X-Init-Data": init_data})
    second_fake = await second_resp.json()
    assert second_fake["user_id"] != fake["user_id"]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_feed.py::test_like_on_fake_does_not_create_match tests/test_fake_feed.py::test_skip_on_fake_records_view -v`
Expected: FAIL — likes are recorded and matches attempted.

- [ ] **Step 5: Apply changes and run all fake feed tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_fake_feed.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web_routes.py tests/test_fake_feed.py
git commit -m "feat(feed): fake profiles do not create likes, matches or notifications"
```

---

### Task 6: Run full test suite and final review

- [ ] **Step 1: Run all tests**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v`
Expected: PASS (no regressions).

- [ ] **Step 2: Lint/format check (optional)**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python -m py_compile web_routes.py database.py services/fake_profile_generator.py scripts/prepare_fake_avatars.py`
Expected: no syntax errors.

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git commit -m "test: verify fake feed integration has no regressions" || true
```

---

## Plan Self-Review

**Spec coverage:**
- Pre-uploaded AI avatar pool — Task 2 script + Task 3 picker.
- Fake profiles match user filters — Task 3 generator uses viewer filters.
- Bio/description generation with variety — Task 3 templates + test.
- Like/skip visually normal but no side effects — Task 5.
- Infinite feed via on-demand generation — Task 4 fallback.
- No photo when pool exhausted — Task 3 `pick_avatar_file_id` returns `None`.
- Fakes excluded from likes/matches — Task 5 `likes` endpoint filter.

**Placeholder scan:** No TBD/TODO/fill-in details. Every step has file paths, code, and commands.

**Type consistency:** `bio` is `str | None` everywhere. `generate_fake_profiles_batch` returns `list[dict]`. `pick_avatar_file_id` returns `str | None`. Avatar records use `"file_id"` key consistently.
