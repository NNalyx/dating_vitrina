# Telegram Mini App Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dark-themed Telegram Mini App skeleton with registration, served from GitHub Pages and backed by an aiohttp server running in the same process as the bot.

**Architecture:** Static frontend in `miniapp/` calls a small aiohttp API. The API validates Telegram `initData` and reuses existing `database.py` functions. Bot and web server start together in `znakomstvabot.py`.

**Tech Stack:** Python 3.12, aiogram, aiohttp, pytest; frontend: plain HTML/CSS/JS.

---

## File map

| File | Responsibility |
|------|----------------|
| `miniapp/index.html` | Mini App entry point. |
| `miniapp/css/style.css` | Dark minimalist theme. |
| `miniapp/js/config.js` | API base URL and constants. |
| `miniapp/js/api.js` | Fetch wrapper that sends `initData`. |
| `miniapp/js/app.js` | Router: welcome → registration → home. |
| `miniapp/js/screens/welcome.js` | Welcome screen. |
| `miniapp/js/screens/registration.js` | Multi-step registration form. |
| `miniapp/js/screens/home.js` | Post-registration placeholder. |
| `services/init_data.py` | Validate Telegram `initData` HMAC. |
| `web_app.py` | aiohttp application factory + middleware. |
| `web_routes.py` | API route handlers. |
| `znakomstvabot.py` | Start bot and web server together. |
| `tests/test_web_auth.py` | Tests for initData validation and auth endpoint. |
| `tests/test_web_register.py` | Tests for registration endpoint. |

---

## Task 1: Install aiohttp and add initData validation service

**Files:**
- Create: `services/init_data.py`
- Test: `tests/test_web_auth.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_web_auth.py`:

```python
import urllib.parse

import pytest

from services.init_data import validate_init_data


def _make_init_data(user_id: int, bot_token: str) -> str:
    """Build a valid Telegram initData string for tests."""
    from hmac import HMAC
    from hashlib import sha256

    user = urllib.parse.quote(f'{{"id":{user_id},"first_name":"Test"}}')
    pairs = [
        ("auth_date", "1690000000"),
        ("query_id", "test_query_id"),
        ("user", user),
    ]
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs))
    secret_key = HMAC(bot_token.encode(), b"WebAppData", sha256).digest()
    hash_value = HMAC(data_check_string.encode(), secret_key, sha256).hexdigest()
    pairs.append(("hash", hash_value))
    return "&".join(f"{k}={v}" for k, v in pairs)


class TestValidateInitData:
    def test_valid_init_data_returns_user_id(self, monkeypatch):
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        init_data = _make_init_data(123456, "test_token_12345")
        result = validate_init_data(init_data)
        assert result == 123456

    def test_invalid_hash_returns_none(self, monkeypatch):
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        result = validate_init_data("user=%7B%22id%22%3A123%7D&hash=wrong")
        assert result is None

    def test_missing_user_returns_none(self, monkeypatch):
        monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
        from hmac import HMAC
        from hashlib import sha256

        pairs = [("auth_date", "1690000000")]
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs))
        secret_key = HMAC(b"test_token_12345", b"WebAppData", sha256).digest()
        hash_value = HMAC(data_check_string.encode(), secret_key, sha256).hexdigest()
        init_data = f"auth_date=1690000000&hash={hash_value}"
        result = validate_init_data(init_data)
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_web_auth.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.init_data'`.

- [ ] **Step 3: Install aiohttp**

```bash
cd PycharmProjects/PythonProject
.venv/Scripts/pip install aiohttp
```

- [ ] **Step 4: Write minimal implementation**

Create `services/init_data.py`:

```python
import hmac
import json
import urllib.parse
from hashlib import sha256

from config import BOT_TOKEN


def _constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def validate_init_data(init_data: str) -> int | None:
    """Validate Telegram WebApp initData and return user_id or None."""
    if not init_data:
        return None

    parsed = urllib.parse.parse_qs(init_data)
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        return None

    data_check_string = "\n".join(
        f"{k}={v}"
        for k, values in sorted(parsed.items())
        for v in values
    )

    secret_key = hmac.new(BOT_TOKEN.encode(), b"WebAppData", sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()

    if not _constant_time_compare(received_hash, expected_hash):
        return None

    user_json = parsed.get("user", [None])[0]
    if not user_json:
        return None

    try:
        user = json.loads(user_json)
        return int(user.get("id"))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
```

- [ ] **Step 5: Run test to verify it passes**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_web_auth.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add services/init_data.py tests/test_web_auth.py
pip freeze > requirements.txt  # if requirements.txt exists and is tracked
if [ -f requirements.txt ]; then git add requirements.txt; fi
git commit -m "feat: add Telegram initData validation service"
```

---

## Task 2: Add aiohttp API routes

**Files:**
- Create: `web_routes.py`
- Create: `web_app.py`
- Modify: `database.py` (if `user_exists` already exists; verify)
- Test: `tests/test_web_auth.py`, `tests/test_web_register.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_web_auth.py`:

```python
from aiohttp.test_utils import TestClient, TestServer
from aiohttp import web

from web_app import create_app
from web_routes import routes


@pytest.fixture
async def client(aiohttp_client):
    app = create_app()
    return await aiohttp_client(app)


async def test_auth_valid_init_data(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    init_data = _make_init_data(123456, "test_token_12345")
    resp = await client.post("/api/auth", json={"initData": init_data})
    assert resp.status == 200
    data = await resp.json()
    assert data["user_id"] == 123456
    assert data["is_registered"] is False


async def test_auth_invalid_init_data(client):
    resp = await client.post("/api/auth", json={"initData": "bad"})
    assert resp.status == 401
```

Create `tests/test_web_register.py`:

```python
import pytest

from aiohttp.test_utils import TestClient

from database import init_db, get_user
from web_app import create_app


@pytest.fixture
async def client(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    app = create_app()
    return await aiohttp_client(app)


async def test_register_new_user(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    from tests.test_web_auth import _make_init_data

    init_data = _make_init_data(111, "test_token_12345")
    payload = {
        "initData": init_data,
        "age": 25,
        "name": "Анна",
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": ["Музыка", "Спорт"],
        "city": "Москва",
        "photo_file_id": None,
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 201
    user = await get_user(111)
    assert user["name"] == "Анна"


async def test_register_profanity_name_returns_400(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    from tests.test_web_auth import _make_init_data

    init_data = _make_init_data(222, "test_token_12345")
    payload = {
        "initData": init_data,
        "age": 25,
        "name": "блядь",
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": ["Музыка"],
        "city": "Москва",
        "photo_file_id": None,
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_web_auth.py tests/test_web_register.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `web_app` / `web_routes`.

- [ ] **Step 3: Write minimal implementation**

Create `web_routes.py`:

```python
from aiohttp import web

from database import add_user, get_user, user_exists
from services.city_validation import is_valid_city, normalize_city
from services.init_data import validate_init_data
from services.moderation import is_clean_city, is_clean_name

routes = web.RouteTableDef()


def _get_init_data(request: web.Request) -> str | None:
    if request.method == "GET":
        return request.headers.get("X-Init-Data")
    data = request.get("initData")
    if data:
        return data
    body = request.get("body")
    if body and "initData" in body:
        return body["initData"]
    return None


async def _get_user_id(request: web.Request) -> int | None:
    body = await request.json() if request.can_read_body else {}
    request["body"] = body
    init_data = body.get("initData") or request.headers.get("X-Init-Data")
    return validate_init_data(init_data) if init_data else None


@routes.post("/api/auth")
async def auth(request: web.Request) -> web.Response:
    body = await request.json()
    user_id = validate_init_data(body.get("initData", ""))
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)
    exists = await user_exists(user_id)
    return web.json_response({"user_id": user_id, "is_registered": exists})


@routes.post("/api/register")
async def register(request: web.Request) -> web.Response:
    body = await request.json()
    user_id = validate_init_data(body.get("initData", ""))
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    name = str(body.get("name", "")).strip()
    city = str(body.get("city", "")).strip()

    if len(name) < 2:
        return web.json_response({"error": "Name too short"}, status=400)
    if not is_clean_name(name):
        return web.json_response({"error": "Name contains profanity"}, status=400)
    if not is_valid_city(city):
        return web.json_response({"error": "Invalid city"}, status=400)
    normalized_city = normalize_city(city)
    if not is_clean_city(normalized_city):
        return web.json_response({"error": "City contains profanity"}, status=400)

    try:
        await add_user(
            user_id=user_id,
            username=None,
            age=int(body["age"]),
            name=name,
            gender=str(body["gender"]),
            looking_for=str(body["looking_for"]),
            goal=str(body["goal"]),
            interests=list(body.get("interests", [])),
            photo_file_id=body.get("photo_file_id"),
            city=normalized_city,
        )
    except Exception as exc:
        return web.json_response({"error": str(exc)}, status=500)

    return web.json_response({"status": "ok"}, status=201)


@routes.get("/api/me")
async def me(request: web.Request) -> web.Response:
    init_data = request.headers.get("X-Init-Data", "")
    user_id = validate_init_data(init_data)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)
    user = await get_user(user_id)
    if user is None:
        return web.json_response({"error": "User not found"}, status=404)
    return web.json_response(user)
```

Create `web_app.py`:

```python
from aiohttp import web

from web_routes import routes


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    return app
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_web_auth.py tests/test_web_register.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web_routes.py web_app.py tests/test_web_auth.py tests/test_web_register.py
git commit -m "feat: add aiohttp API for mini app auth and registration"
```

---

## Task 3: Start bot and web server together

**Files:**
- Modify: `znakomstvabot.py`
- Test: manual run

- [ ] **Step 1: Modify entry point**

Edit `znakomstvabot.py`:

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN
from database import init_db
from handlers import browse, common, likes, menu, profile, registration, settings
from web_app import create_app


async def start_bot(bot: Bot, dp: Dispatcher):
    await dp.start_polling(bot)


async def start_web(app: web.Application):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()


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
        settings.router,
    )

    app = create_app()

    await asyncio.gather(
        start_bot(bot, dp),
        start_web(app),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run the bot and web server**

```bash
cd PycharmProjects/PythonProject
PYTHONIOENCODING=utf-8 .venv/Scripts/python znakomstvabot.py
```

Expected: logs show both polling and web server started.

- [ ] **Step 3: Quick smoke test**

In another terminal:

```bash
curl -X POST http://localhost:8080/api/auth -H "Content-Type: application/json" -d '{"initData":"bad"}'
```

Expected: `{"error": "Invalid initData"}` with HTTP 401.

- [ ] **Step 4: Commit**

```bash
git add znakomstvabot.py
git commit -m "feat: run bot and aiohttp web server together"
```

---

## Task 4: Build static Mini App frontend

**Files:**
- Create: `miniapp/index.html`
- Create: `miniapp/css/style.css`
- Create: `miniapp/js/config.js`
- Create: `miniapp/js/api.js`
- Create: `miniapp/js/app.js`
- Create: `miniapp/js/screens/welcome.js`
- Create: `miniapp/js/screens/registration.js`
- Create: `miniapp/js/screens/home.js`

- [ ] **Step 1: Create HTML shell**

Create `miniapp/index.html`:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Dating App</title>
    <link rel="stylesheet" href="css/style.css">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
    <div id="app"></div>
    <script type="module" src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create dark theme CSS**

Create `miniapp/css/style.css`:

```css
:root {
    --bg: #0f0f0f;
    --surface: #1c1c1e;
    --text: #ffffff;
    --text-secondary: #8e8e93;
    --accent: #ff2d55;
    --accent-2: #8b5cf6;
    --radius: 16px;
    --gap: 16px;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

#app {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: var(--gap);
    max-width: 480px;
    width: 100%;
    margin: 0 auto;
}

.screen {
    display: none;
    flex-direction: column;
    flex: 1;
    gap: var(--gap);
}

.screen.active {
    display: flex;
}

h1, h2, p {
    margin: 0;
}

h1 {
    font-size: 28px;
    font-weight: 700;
}

p {
    color: var(--text-secondary);
    line-height: 1.5;
}

button, .btn {
    border: none;
    border-radius: var(--radius);
    padding: 16px 20px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: var(--text);
    text-align: center;
    transition: opacity 0.2s;
}

button:disabled, .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

button.secondary {
    background: var(--surface);
    color: var(--text);
}

input, select {
    background: var(--surface);
    border: 1px solid transparent;
    border-radius: var(--radius);
    color: var(--text);
    padding: 16px;
    font-size: 16px;
    outline: none;
}

input:focus, select:focus {
    border-color: var(--accent);
}

.chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.chip {
    background: var(--surface);
    color: var(--text-secondary);
    border-radius: 20px;
    padding: 8px 14px;
    font-size: 14px;
    cursor: pointer;
    user-select: none;
}

.chip.selected {
    background: var(--accent);
    color: var(--text);
}

.step-counter {
    color: var(--text-secondary);
    font-size: 14px;
}

.error {
    color: #ff453a;
    font-size: 14px;
}
```

- [ ] **Step 3: Create JS modules**

Create `miniapp/js/config.js`:

```javascript
export const API_BASE_URL = "http://localhost:8080"; // change for production
```

Create `miniapp/js/api.js`:

```javascript
import { API_BASE_URL } from "./config.js";

const initData = window.Telegram?.WebApp?.initData || "";

async function request(method, path, body = null) {
    const options = {
        method,
        headers: {
            "Content-Type": "application/json",
            "X-Init-Data": initData,
        },
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    const resp = await fetch(`${API_BASE_URL}${path}`, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
}

export const api = {
    auth: () => request("POST", "/api/auth", { initData }),
    register: (profile) => request("POST", "/api/register", { initData, ...profile }),
    me: () => request("GET", "/api/me"),
};
```

Create `miniapp/js/screens/welcome.js`:

```javascript
export function renderWelcome(app, onStart) {
    app.innerHTML = `
        <div class="screen active" id="welcome">
            <h1>Добро пожаловать</h1>
            <p>Знакомься с интересными людьми рядом. Красиво, быстро, безопасно.</p>
            <div style="flex:1"></div>
            <button id="startBtn">Начать</button>
        </div>
    `;
    document.getElementById("startBtn").addEventListener("click", onStart);
}
```

Create `miniapp/js/screens/registration.js`:

```javascript
const GENDER_OPTIONS = [
    { value: "male", label: "Парень" },
    { value: "female", label: "Девушка" },
    { value: "other", label: "Другое" },
];

const LOOKING_OPTIONS = [
    { value: "male", label: "Парней" },
    { value: "female", label: "Девушек" },
    { value: "all", label: "Всех" },
];

const GOAL_OPTIONS = [
    { value: "relationship", label: "Отношения" },
    { value: "friendship", label: "Дружба" },
    { value: "flirt", label: "Флирт" },
];

const INTERESTS = [
    "Музыка", "Спорт", "Кино", "Игры", "Путешествия",
    "Книги", "Технологии", "Фото", "Рисование", "Кулинария",
];

const STEPS = [
    { id: "age", title: "Сколько тебе лет?" },
    { id: "name", title: "Как тебя зовут?" },
    { id: "gender", title: "Твой пол" },
    { id: "looking_for", title: "Кого ты ищешь?" },
    { id: "goal", title: "Что ищешь?" },
    { id: "interests", title: "Выбери интересы (минимум 3)" },
    { id: "city", title: "Твой город" },
    { id: "photo", title: "Фото профиля" },
];

export function renderRegistration(app, api, onComplete) {
    let step = 0;
    const profile = {
        age: "",
        name: "",
        gender: "",
        looking_for: "",
        goal: "",
        interests: new Set(),
        city: "",
        photo_file_id: null,
    };

    function render() {
        const current = STEPS[step];
        app.innerHTML = `
            <div class="screen active" id="registration">
                <div class="step-counter">Шаг ${step + 1} из ${STEPS.length}</div>
                <h2>${current.title}</h2>
                <div id="step-content"></div>
                <div id="error" class="error"></div>
                <div style="flex:1"></div>
                <button id="nextBtn">Далее</button>
            </div>
        `;
        renderStepContent(current.id);
        document.getElementById("nextBtn").addEventListener("click", handleNext);
    }

    function renderStepContent(id) {
        const container = document.getElementById("step-content");
        if (id === "age") {
            container.innerHTML = `<input type="number" id="input" placeholder="Возраст" value="${profile.age}">`;
        } else if (id === "name") {
            container.innerHTML = `<input type="text" id="input" placeholder="Имя" value="${profile.name}">`;
        } else if (id === "gender") {
            container.innerHTML = GENDER_OPTIONS.map(o =>
                `<button class="secondary option" data-value="${o.value}">${o.label}</button>`
            ).join("<br><br>");
        } else if (id === "looking_for") {
            container.innerHTML = LOOKING_OPTIONS.map(o =>
                `<button class="secondary option" data-value="${o.value}">${o.label}</button>`
            ).join("<br><br>");
        } else if (id === "goal") {
            container.innerHTML = GOAL_OPTIONS.map(o =>
                `<button class="secondary option" data-value="${o.value}">${o.label}</button>`
            ).join("<br><br>");
        } else if (id === "interests") {
            container.innerHTML = `<div class="chips">${INTERESTS.map(i =>
                `<span class="chip ${profile.interests.has(i) ? "selected" : ""}" data-value="${i}">${i}</span>`
            ).join("")}</div>`;
        } else if (id === "city") {
            container.innerHTML = `<input type="text" id="input" placeholder="Город" value="${profile.city}">`;
        } else if (id === "photo") {
            container.innerHTML = `
                <p>Фото повышает количество лайков. Пока можешь пропустить.</p>
                <button class="secondary" id="skipPhoto">Пропустить</button>
            `;
            document.getElementById("skipPhoto").addEventListener("click", () => submit());
        }

        container.querySelectorAll(".option").forEach(btn => {
            btn.addEventListener("click", () => {
                if (id === "gender") profile.gender = btn.dataset.value;
                if (id === "looking_for") profile.looking_for = btn.dataset.value;
                if (id === "goal") profile.goal = btn.dataset.value;
                container.querySelectorAll(".option").forEach(b => b.style.borderColor = "");
                btn.style.borderColor = "var(--accent)";
            });
        });

        container.querySelectorAll(".chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const value = chip.dataset.value;
                if (profile.interests.has(value)) {
                    profile.interests.delete(value);
                    chip.classList.remove("selected");
                } else {
                    profile.interests.add(value);
                    chip.classList.add("selected");
                }
            });
        });
    }

    function validate() {
        const current = STEPS[step];
        if (current.id === "age") {
            const age = parseInt(document.getElementById("input").value, 10);
            if (!age || age < 16 || age > 100) return "Введи возраст от 16 до 100";
            profile.age = age;
        } else if (current.id === "name") {
            const name = document.getElementById("input").value.trim();
            if (name.length < 2) return "Имя слишком короткое";
            profile.name = name;
        } else if (current.id === "gender") {
            if (!profile.gender) return "Выбери пол";
        } else if (current.id === "looking_for") {
            if (!profile.looking_for) return "Выбери, кого ищешь";
        } else if (current.id === "goal") {
            if (!profile.goal) return "Выбери цель";
        } else if (current.id === "interests") {
            if (profile.interests.size < 3) return "Выбери минимум 3 интереса";
        } else if (current.id === "city") {
            const city = document.getElementById("input").value.trim();
            if (!city) return "Введи город";
            profile.city = city;
        }
        return null;
    }

    async function handleNext() {
        const errorEl = document.getElementById("error");
        const err = validate();
        if (err) {
            errorEl.textContent = err;
            return;
        }
        errorEl.textContent = "";
        if (step < STEPS.length - 1) {
            step++;
            render();
        } else {
            await submit();
        }
    }

    async function submit() {
        const errorEl = document.getElementById("error");
        try {
            await api.register({
                age: profile.age,
                name: profile.name,
                gender: profile.gender,
                looking_for: profile.looking_for,
                goal: profile.goal,
                interests: Array.from(profile.interests),
                city: profile.city,
                photo_file_id: profile.photo_file_id,
            });
            onComplete();
        } catch (e) {
            errorEl.textContent = e.message;
        }
    }

    render();
}
```

Create `miniapp/js/screens/home.js`:

```javascript
export function renderHome(app, api) {
    app.innerHTML = `
        <div class="screen active" id="home">
            <h1>Готово!</h1>
            <p>Регистрация завершена. Здесь скоро появится лента анкет.</p>
            <div style="flex:1"></div>
            <button disabled>Смотреть анкеты</button>
        </div>
    `;
}
```

Create `miniapp/js/app.js`:

```javascript
import { api } from "./api.js";
import { renderWelcome } from "./screens/welcome.js";
import { renderRegistration } from "./screens/registration.js";
import { renderHome } from "./screens/home.js";

const app = document.getElementById("app");
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

async function init() {
    try {
        const { is_registered } = await api.auth();
        if (is_registered) {
            renderHome(app, api);
        } else {
            renderWelcome(app, () => renderRegistration(app, api, () => renderHome(app, api)));
        }
    } catch (e) {
        app.innerHTML = `<div class="screen active"><p>Ошибка: ${e.message}</p></div>`;
    }
}

init();
```

- [ ] **Step 4: Local smoke test**

Serve `miniapp/` locally:

```bash
cd PycharmProjects/PythonProject/miniapp
python -m http.server 3000
```

Open `http://localhost:3000` in browser. Since Telegram object is missing, the app will try to auth with empty initData and show an error. That's expected outside Telegram.

- [ ] **Step 5: Commit**

```bash
git add miniapp/
git commit -m "feat: add mini app frontend skeleton and registration flow"
```

---

## Task 5: Bot sends Mini App button after policy

**Files:**
- Modify: `handlers/registration.py` (policy handler) or `handlers/common.py`

- [ ] **Step 1: Find policy handler**

Read `handlers/common.py` and `handlers/registration.py` to locate where `/start` and policy agreement are handled.

- [ ] **Step 2: Add Mini App button after policy agreement**

Modify the policy agreement callback to send a message with a `web_app` button:

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

MINI_APP_URL = "https://<username>.github.io/miniapp/"  # update before deploy

async def send_open_app_button(message: types.Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "Отлично! Нажми кнопку ниже, чтобы продолжить в приложении.",
        reply_markup=keyboard,
    )
```

Call this function after the user agrees to the policy.

- [ ] **Step 3: Test in bot**

Start the bot, send `/start`, agree to policy, verify the button opens the Mini App URL.

- [ ] **Step 4: Commit**

```bash
git add handlers/registration.py  # or whichever file changed
git commit -m "feat: bot opens mini app after policy agreement"
```

---

## Task 6: Full test run and GitHub Pages prep

- [ ] **Step 1: Run full test suite**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Update requirements**

```bash
.venv/Scripts/pip freeze > requirements.txt
```

If `requirements.txt` is tracked, commit it.

- [ ] **Step 3: GitHub Pages prep**

Push to GitHub. Enable GitHub Pages from root or `miniapp/` folder. Update `MINI_APP_URL` in bot code and `API_BASE_URL` in `miniapp/js/config.js` to production values.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: mini app phase 1 complete"
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| initData validation | Task 1 |
| aiohttp API auth/register/me | Task 2 |
| Bot + web server together | Task 3 |
| Static frontend dark theme | Task 4 |
| Welcome + registration screens | Task 4 |
| Bot opens mini app after policy | Task 5 |
| Tests | Task 1, 2, 6 |

## Placeholder scan

No TBD/TODO placeholders. `MINI_APP_URL` and `API_BASE_URL` are configured constants that must be updated per environment — documented in comments.

## Type consistency check

- `validate_init_data(init_data: str) -> int | None` used consistently.
- `create_app()` returns `web.Application`.
- API endpoints accept/return the JSON shapes defined in the spec.
