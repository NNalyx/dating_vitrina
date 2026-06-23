# Cloudflare Quick-Tunnel Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On every bot startup, start a local `cloudflared` quick tunnel, capture its public `*.trycloudflare.com` URL, serve the Mini App static files from the backend on that URL, and use the live URL for the Telegram Mini App button.

**Architecture:** A new `tunnel.py` module wraps `cloudflared` as an asyncio subprocess, parses stdout/stderr for the public URL, and exposes it via `get_tunnel_url()`. `znakomstvabot.py` starts the tunnel first, waits for the URL, then launches the web server and bot polling. The backend serves `docs/` as static files at `/`, and the frontend uses relative API calls so the tunnel domain is transparent.

**Tech Stack:** Python 3.12, aiogram 3.x, aiohttp, `cloudflared` Windows binary.

---

### Task 1: Create `tunnel.py` tunnel manager

**Files:**
- Create: `tunnel.py`

Implement an asyncio-based wrapper around `cloudflared tunnel --url http://localhost:8080`.

- [ ] **Step 1: Write `tunnel.py`**

```python
import asyncio
import logging
import re
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
DEFAULT_CLOUDFLARED_PATH = Path(r"C:\Users\antpl\Downloads\cloudflared-windows-amd64.exe")

_tunnel_url: str | None = None
_process: asyncio.subprocess.Process | None = None


def get_tunnel_url() -> str | None:
    return _tunnel_url


async def _read_stream(stream: asyncio.StreamReader | None, tag: str, found_event: asyncio.Event):
    global _tunnel_url
    if stream is None:
        return
    while True:
        try:
            line = await stream.readline()
        except Exception as exc:
            _logger.warning("%s stream read error: %s", tag, exc)
            return
        if not line:
            return
        text = line.decode("utf-8", errors="replace").rstrip()
        _logger.debug("[%s] %s", tag, text)
        if not _tunnel_url:
            match = TUNNEL_RE.search(text)
            if match:
                _tunnel_url = match.group(0)
                _logger.info("Cloudflare tunnel URL: %s", _tunnel_url)
                found_event.set()


async def start_tunnel(
    local_url: str = "http://localhost:8080",
    cloudflared_path: Path | str = DEFAULT_CLOUDFLARED_PATH,
    startup_timeout: float = 60.0,
) -> str:
    global _process, _tunnel_url
    if _process is not None and _process.returncode is None:
        if _tunnel_url:
            return _tunnel_url
        await _process.wait()

    _tunnel_url = None
    found_event = asyncio.Event()

    cmd = [str(cloudflared_path), "tunnel", "--url", local_url]
    _logger.info("Starting cloudflared: %s", " ".join(cmd))
    try:
        _process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to start cloudflared: {exc}") from exc

    asyncio.create_task(_read_stream(_process.stdout, "stdout", found_event))
    asyncio.create_task(_read_stream(_process.stderr, "stderr", found_event))

    try:
        await asyncio.wait_for(found_event.wait(), timeout=startup_timeout)
    except asyncio.TimeoutError as exc:
        await stop_tunnel()
        raise RuntimeError("Timed out waiting for cloudflared tunnel URL") from exc

    if _tunnel_url is None:
        await stop_tunnel()
        raise RuntimeError("cloudflared started but no tunnel URL was parsed")

    asyncio.create_task(_watch_process())
    return _tunnel_url


async def _watch_process():
    global _process, _tunnel_url
    if _process is None:
        return
    returncode = await _process.wait()
    _logger.warning("cloudflared exited with code %s", returncode)
    _tunnel_url = None
    _process = None


async def stop_tunnel():
    global _process, _tunnel_url
    _tunnel_url = None
    if _process is None:
        return
    try:
        _process.terminate()
        await asyncio.wait_for(_process.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        _process.kill()
        await _process.wait()
    except ProcessLookupError:
        pass
    _process = None
```

- [ ] **Step 2: Verify module imports cleanly**

Run:

```bash
cd PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import tunnel; print('ok')"
```

Expected: prints `ok` with no errors.

- [ ] **Step 3: Commit**

```bash
git add tunnel.py
git commit -m "feat: add cloudflared quick-tunnel manager"
```

---

### Task 2: Serve Mini App static files from the backend and relax CORS

**Files:**
- Modify: `web_app.py`

- [ ] **Step 1: Replace `web_app.py` contents**

```python
from pathlib import Path

from aiohttp import web

from web_routes import routes


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Init-Data"
    return resp


DOCS_DIR = Path(__file__).parent / "docs"


def create_app(bot=None) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app["bot"] = bot
    app.add_routes(routes)
    app.router.add_static("/", path=DOCS_DIR, name="static", show_index=True)
    return app
```

- [ ] **Step 2: Run existing web tests to confirm no regression**

```bash
cd PycharmProjects/PythonProject && PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_web_auth.py tests/test_web_register.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add web_app.py
git commit -m "feat: serve Mini App static files from backend, allow all CORS origins"
```

---

### Task 3: Wire tunnel startup into `znakomstvabot.py`

**Files:**
- Modify: `znakomstvabot.py`

- [ ] **Step 1: Update `znakomstvabot.py`**

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
from tunnel import start_tunnel, stop_tunnel
from web_app import create_app


async def start_bot(bot: Bot, dp: Dispatcher):
    await dp.start_polling(bot)


async def start_web(app: web.Application, host: str = "0.0.0.0", port: int = 8080):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info("Web server started on %s:%s", host, port)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()

    public_url = await start_tunnel()
    logging.info("Public Mini App URL: %s", public_url)

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

    app = create_app(bot)
    app["public_url"] = public_url

    try:
        await asyncio.gather(
            start_bot(bot, dp),
            start_web(app),
        )
    finally:
        await stop_tunnel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run smoke import check**

```bash
cd PycharmProjects/PythonProject && .venv/Scripts/python.exe -c "import znakomstvabot; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add znakomstvabot.py
git commit -m "feat: start cloudflared tunnel before bot and expose public URL"
```

---

### Task 4: Use the live tunnel URL for the Mini App button

**Files:**
- Modify: `handlers/registration.py`

- [ ] **Step 1: Update `process_policy` to use `tunnel.get_tunnel_url()`**

Replace the hardcoded `MINI_APP_URL` with a dynamic lookup. Add at the top:

```python
from tunnel import get_tunnel_url
```

Remove:

```python
MINI_APP_URL = "https://nnalyx.github.io/dating_vitrina/"
```

Replace the `process_policy` body URL construction with:

```python
    await state.clear()
    mini_app_url = get_tunnel_url()
    if mini_app_url is None:
        await callback.answer(
            "Приложение ещё запускается. Попробуй через несколько секунд.",
            show_alert=True,
        )
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=mini_app_url),
                )
            ]
        ]
    )
```

- [ ] **Step 2: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: use live cloudflared tunnel URL for Mini App button"
```

---

### Task 5: Make the frontend use relative API URLs

**Files:**
- Modify: `docs/js/config.js`
- Modify: `docs/js/api.js`

- [ ] **Step 1: Set `API_BASE_URL` to empty string**

`docs/js/config.js`:

```javascript
export const API_BASE_URL = "";
```

This makes all API calls relative to the current origin, so the same tunnel domain serves both frontend and backend.

- [ ] **Step 2: Add a fallback origin in `api.js` for non-Telegram contexts**

`docs/js/api.js`:

```javascript
import { API_BASE_URL } from "./config.js";

const initData = window.Telegram?.WebApp?.initData || "";
const BASE_URL = API_BASE_URL || window.location.origin || "";

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
    const resp = await fetch(`${BASE_URL}${path}`, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
}

async function uploadRequest(path, formData) {
    const resp = await fetch(`${BASE_URL}${path}`, {
        method: "POST",
        headers: {
            "X-Init-Data": initData,
        },
        body: formData,
    });
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
    uploadPhoto: (file) => {
        const formData = new FormData();
        formData.append("photo", file);
        return uploadRequest("/api/upload-photo", formData);
    },
};
```

- [ ] **Step 3: Commit**

```bash
git add docs/js/config.js docs/js/api.js
git commit -m "feat: frontend uses relative API URLs for tunnel domain"
```

---

### Task 6: Add lightweight tests and run the full suite

**Files:**
- Create: `tests/test_tunnel.py`
- Create: `tests/test_static_serving.py`

- [ ] **Step 1: Test tunnel URL regex parsing**

```python
import pytest

from tunnel import TUNNEL_RE


@pytest.mark.parametrize(
    "line,expected",
    [
        ("2025-01-01T00:00:00Z INF https://foo-bar.trycloudflare.com", "https://foo-bar.trycloudflare.com"),
        ("Your quick tunnel has been created at: https://abc-123.trycloudflare.com", "https://abc-123.trycloudflare.com"),
        ("no url here", None),
    ],
)
def test_tunnel_url_regex(line, expected):
    match = TUNNEL_RE.search(line)
    assert (match.group(0) if match else None) == expected
```

- [ ] **Step 2: Test static file serving**

```python
async def test_index_served(aiohttp_client):
    from web_app import create_app

    app = create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/")
    assert resp.status == 200
    text = await resp.text()
    assert "<title>Dating App</title>" in text
```

- [ ] **Step 3: Run full test suite**

```bash
cd PycharmProjects/PythonProject && PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_tunnel.py tests/test_static_serving.py
git commit -m "test: tunnel URL regex and static Mini App serving"
```

---

### Task 7: Push to GitHub and wipe the database

- [ ] **Step 1: Push commits**

```bash
cd PycharmProjects/PythonProject && git push origin master
```

- [ ] **Step 2: Delete the local SQLite database**

```bash
cd PycharmProjects/PythonProject && rm -f dating_bot.db
```

- [ ] **Step 3: Confirm database is gone**

```bash
cd PycharmProjects/PythonProject && ls dating_bot.db 2>&1 || echo "DB removed"
```

Expected: prints `DB removed`.

---

## Self-Review

| Requirement | Task |
|---|---|
| Launch cloudflared on startup | Task 1 + Task 3 |
| Parse public tunnel URL | Task 1 |
| Expose URL to bot | Task 3 (`app["public_url"]`) and Task 4 (`tunnel.get_tunnel_url()`) |
| Serve Mini App from backend | Task 2 |
| Frontend uses same-origin API | Task 5 |
| Registration button uses live URL | Task 4 |
| Handle tunnel process exit | Task 1 (`_watch_process` logs exit; restart requires manual bot restart) |
| Commit, push, wipe DB | Task 7 |

No placeholders are used; every code block is the intended final code.
