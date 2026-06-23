# Mini App Full Functionality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the remaining bot features into the Mini App (feed, incoming likes, profile editing, settings/filters) and validate the city inline during registration. After registration the user lands directly in the feed.

**Architecture:** Extend `web_routes.py` with REST endpoints. Add `docs/js/screens/feed.js`, `likes.js`, `profile.js`, `settings.js`, a `docs/js/components/nav.js`, and update `app.js` to manage screens. Style with the existing black/dark-gray/white theme.

**Tech Stack:** Python aiogram/aiohttp, vanilla JS modules, SQLite.

---

### Task 1: Backend city validation endpoint

**Files:**
- Modify: `web_routes.py`

Add `POST /api/validate-city` that reuses `is_valid_city`, `normalize_city`, `is_clean_city`.

```python
@routes.post("/api/validate-city")
async def validate_city_endpoint(request: web.Request) -> web.Response:
    body = await request.json()
    raw = str(body.get("city", "")).strip()
    if not raw:
        return web.json_response({"valid": False, "error": "Введи город"})
    if not is_valid_city(raw):
        return web.json_response({"valid": False, "error": "Название города не похоже на настоящее"})
    normalized = normalize_city(raw)
    if not is_clean_city(normalized):
        return web.json_response({"valid": False, "error": "Недопустимые слова в названии города"})
    return web.json_response({"valid": True, "normalized": normalized})
```

- [ ] Add endpoint.
- [ ] Run `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/test_web_auth.py tests/test_web_register.py -v` — expected PASS.
- [ ] Commit.

---

### Task 2: Backend feed endpoints

**Files:**
- Modify: `web_routes.py`

Add GET `/api/feed`, POST `/api/feed/{id}/like`, POST `/api/feed/{id}/skip`. Use matching/filter services. Record views/skips and likes. Notify via bot on mutual match (reuse a small helper, no circular imports).

Endpoint shape:

```python
@routes.get("/api/feed")
async def feed(request: web.Request) -> web.Response:
    user_id = validate_init_data(request.headers.get("X-Init-Data", ""))
    if user_id is None: return web.json_response({"error": "Invalid initData"}, status=401)
    user = await get_user(user_id)
    if user is None: return web.json_response({"error": "User not found"}, status=404)
    candidates = await get_all_users()
    viewed = await get_viewed_ids(user_id)
    filtered = filter_candidates(user, candidates, viewed)
    scored = score_candidates(user, filtered)
    if not scored:
        return web.json_response({"done": True})
    candidate, compatibility = scored[0]
    return web.json_response({**candidate, "compatibility": compatibility})
```

For `/api/feed/{id}/like` add view + like, then:

```python
is_mutual = await has_like(candidate_id, user_id)
if is_mutual:
    liker = await get_user(user_id)
    liked = await get_user(candidate_id)
    if liker and liked:
        bot = request.app.get("bot")
        if bot:
            await _send_match_notifications(bot, liker, liked)
```

Add `_send_match_notifications(bot, liker, liked)` and `_send_incoming_like(bot, liker, liked_id)` helpers in `web_routes.py` that format text with `format_profile` and send messages/photos.

- [ ] Add endpoints and helpers.
- [ ] Commit.

---

### Task 3: Backend likes, profile, settings endpoints

**Files:**
- Modify: `web_routes.py`

Add:
- `GET /api/likes` — incoming likes list.
- `POST /api/likes/{id}/like_back` — reciprocate.
- `POST /api/likes/{id}/skip` — skip incoming like.
- `PUT /api/me` — update own fields (validate age/name/city/profanity).
- `GET /api/settings` — return filters and notifications.
- `PUT /api/settings` — update filters/notifications.
- `GET /api/photo/{file_id}` — proxy Telegram photo so the frontend can show it.

`/api/photo/{file_id}`:

```python
import io

@routes.get("/api/photo/{file_id}")
async def get_photo(request: web.Request) -> web.Response:
    file_id = request.match_info["file_id"]
    bot = request.app.get("bot")
    if bot is None:
        return web.json_response({"error": "Bot not configured"}, status=500)
    file = await bot.get_file(file_id)
    if file is None:
        return web.json_response({"error": "Photo not found"}, status=404)
    buf = io.BytesIO()
    await bot.download(file, destination=buf)
    buf.seek(0)
    return web.Response(body=buf.read(), content_type="image/jpeg")
```

- [ ] Add endpoints.
- [ ] Commit.

---

### Task 4: Frontend API client extensions

**Files:**
- Modify: `docs/js/api.js`

Extend `api` object:

```javascript
validateCity: (city) => request("POST", "/api/validate-city", { city }),
feed: () => request("GET", "/api/feed"),
like: (id) => request("POST", `/api/feed/${id}/like`),
skip: (id) => request("POST", `/api/feed/${id}/skip`),
likes: () => request("GET", "/api/likes"),
likeBack: (id) => request("POST", `/api/likes/${id}/like_back`),
skipLike: (id) => request("POST", `/api/likes/${id}/skip`),
updateMe: (data) => request("PUT", "/api/me", data),
getSettings: () => request("GET", "/api/settings"),
updateSettings: (data) => request("PUT", "/api/settings", data),
photoUrl: (fileId) => `/api/photo/${fileId}`,
```

- [ ] Update `api.js`.
- [ ] Commit.

---

### Task 5: Inline city validation in registration

**Files:**
- Modify: `docs/js/screens/registration.js`

In the `city` step:
- Add a debounced input listener that calls `api.validateCity`.
- Show inline error and keep Next disabled until valid.
- Store `profile.city = normalized` on success.

Example:

```javascript
let cityTimeout;
input.addEventListener("input", () => {
    clearTimeout(cityTimeout);
    const city = input.value.trim();
    if (!city) {
        errorEl.textContent = "";
        return;
    }
    cityTimeout = setTimeout(async () => {
        try {
            const data = await api.validateCity(city);
            if (data.valid) {
                errorEl.textContent = "";
                profile.city = data.normalized;
            } else {
                errorEl.textContent = data.error;
            }
        } catch (e) {
            errorEl.textContent = e.message;
        }
    }, 400);
});
```

- [ ] Modify city step.
- [ ] Commit.

---

### Task 6: Feed screen with swipe and gradient

**Files:**
- Create: `docs/js/screens/feed.js`

Render full-screen card:

```javascript
export function renderFeed(app, api, onNavigate) {
    let current = null;

    async function load() {
        const data = await api.feed();
        current = data.done ? null : data;
        render();
    }

    function render() {
        if (!current) {
            app.innerHTML = `<div class="screen active feed-empty"><h2>Пока нет подходящих анкет</h2></div>`;
            return;
        }
        const photo = current.photo_file_id ? `<img class="card-photo" src="${api.photoUrl(current.photo_file_id)}" alt="">` : "";
        app.innerHTML = `
            <div class="screen active feed">
                <div class="card">
                    ${photo}
                    <div class="card-gradient"></div>
                    <div class="card-info">
                        <div class="card-name">${current.name}, ${current.age}</div>
                        <div class="card-meta">${current.city || ""} · ${current.compatibility}% ❤️</div>
                        <div class="card-tags">${current.interests}</div>
                    </div>
                </div>
                <div class="feed-actions">
                    <button class="secondary" id="skipBtn">✕</button>
                    <button id="likeBtn">♥</button>
                </div>
            </div>
        `;
        document.getElementById("skipBtn").addEventListener("click", () => act("skip"));
        document.getElementById("likeBtn").addEventListener("click", () => act("like"));
    }

    async function act(type) {
        if (!current) return;
        const card = document.querySelector(".card");
        if (card) card.style.transform = `translateX(${type === "like" ? "120%" : "-120%"}) rotate(${type === "like" ? "10deg" : "-10deg"})`;
        await api[type](current.user_id);
        setTimeout(load, 200);
    }

    load();
}
```

- [ ] Create `feed.js`.
- [ ] Commit.

---

### Task 7: Likes, profile, settings screens

**Files:**
- Create: `docs/js/screens/likes.js`
- Create: `docs/js/screens/profile.js`
- Create: `docs/js/screens/settings.js`

`likes.js`: fetch `/api/likes`, render list of compact cards with like-back/skip buttons.

`profile.js`: fetch `/api/me`, render own card with edit buttons. Use simple prompts or inline inputs for editing.

`settings.js`: fetch `/api/settings`, render age steppers, only-my-city toggle, notifications toggle. Save on change.

- [ ] Create screens.
- [ ] Commit.

---

### Task 8: Bottom navigation and app wiring

**Files:**
- Create: `docs/js/components/nav.js`
- Modify: `docs/js/app.js`

`nav.js` renders a fixed bottom bar with four items: Лента, Лайки, Профиль, Настройки. Profile item shows user's photo if available. Calls `onChange(screen)`.

`app.js`:

```javascript
import { renderFeed } from "./screens/feed.js";
import { renderLikes } from "./screens/likes.js";
import { renderProfile } from "./screens/profile.js";
import { renderSettings } from "./screens/settings.js";
import { renderNav } from "./components/nav.js";

async function init() {
    const { is_registered, user_id } = await api.auth();
    if (!is_registered) {
        renderWelcome(app, () => renderRegistration(app, api, showMain));
    } else {
        showMain();
    }
}

function showMain() {
    renderNav(app, api, (screen) => {
        if (screen === "feed") renderFeed(app, api);
        if (screen === "likes") renderLikes(app, api);
        if (screen === "profile") renderProfile(app, api);
        if (screen === "settings") renderSettings(app, api);
    });
    renderFeed(app, api);
}
```

- [ ] Create nav and update app.js.
- [ ] Commit.

---

### Task 9: CSS for new screens

**Files:**
- Modify: `docs/css/style.css`

Add styles for:
- `.feed`, `.card`, `.card-photo`, `.card-gradient` (linear-gradient from transparent to black at bottom), `.card-info`.
- `.feed-actions` row with circular like/skip buttons.
- `.bottom-nav` fixed bottom bar with active highlight.
- `.likes-list`, `.like-card`, `.profile-card`, `.settings-form`.

- [ ] Update CSS.
- [ ] Commit.

---

### Task 10: Tests

**Files:**
- Create: `tests/test_validate_city.py`
- Create: `tests/test_feed.py`
- Create: `tests/test_likes.py`
- Create: `tests/test_profile_settings.py`

Cover:
- Valid/invalid city endpoint.
- Feed returns candidate or `{done: true}`.
- Like records like and skips record view.
- Likes endpoint returns incoming likes.
- Profile update validates age/name/city.
- Settings get/update filters and notifications.

Run:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v
```

Expected: all tests pass.

- [ ] Add tests.
- [ ] Commit.

---

### Task 11: Final push and wipe DB

- [ ] `git push origin master`
- [ ] `rm -f dating_bot.db`
- [ ] Confirm DB removed.

---

## Self-Review

- City validation inline: Task 5.
- Feed with swipe/gradient: Task 6 + Task 9.
- Bottom nav with profile photo: Task 8 + Task 9.
- Likes/profile/settings: Tasks 3, 7.
- No placeholders in code snippets.
