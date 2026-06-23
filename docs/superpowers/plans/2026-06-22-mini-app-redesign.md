# Mini App Redesign + Photo Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Telegram Mini App with a black/dark-gray/white theme, add animations, and enable optional photo upload during registration.

**Architecture:** Update CSS for visual style and animations, refactor registration screen rendering for transitions and photo upload, add a backend `/api/upload-photo` endpoint that proxies images through Telegram Bot API to obtain a `file_id`, and wire the bot instance into the aiohttp app.

**Tech Stack:** Static HTML/JS/CSS frontend, aiogram Bot, aiohttp backend, SQLite database.

---

## File Structure

- `docs/css/style.css` — theme, layout, animations.
- `docs/js/screens/registration.js` — step rendering, animations, photo upload UI.
- `docs/js/api.js` — adds `uploadPhoto(formData)` helper.
- `web_app.py` — accepts `bot` in `create_app` and stores it in app context.
- `web_routes.py` — new `/api/upload-photo` endpoint.
- `znakomstvabot.py` — passes bot instance to `create_app`.

---

### Task 1: Wire bot instance into aiohttp app

**Files:**
- Modify: `web_app.py`
- Modify: `znakomstvabot.py`
- Test: run backend tests after changes

- [ ] **Step 1: Update `create_app` signature and store bot**

  ```python
  def create_app(bot=None) -> web.Application:
      app = web.Application(middlewares=[cors_middleware])
      app["bot"] = bot
      app.add_routes(routes)
      return app
  ```

- [ ] **Step 2: Pass bot from `znakomstvabot.py`**

  Change:
  ```python
  app = create_app()
  ```
  to:
  ```python
  app = create_app(bot)
  ```

- [ ] **Step 3: Run backend tests**

  Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v`
  Expected: 43 passed.

---

### Task 2: Add backend photo upload endpoint

**Files:**
- Modify: `web_routes.py`
- Test: manual via Mini App

- [ ] **Step 1: Add imports and helper**

  At the top of `web_routes.py`:
  ```python
  from aiogram import Bot
  from aiogram.types import FSInputFile
  import tempfile
  import os
  ```

- [ ] **Step 2: Implement `/api/upload-photo`**

  ```python
  ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
  MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


  @routes.post("/api/upload-photo")
  async def upload_photo(request: web.Request) -> web.Response:
      init_data = request.headers.get("X-Init-Data", "")
      user_id = validate_init_data(init_data)
      if user_id is None:
          return web.json_response({"error": "Invalid initData"}, status=401)

      reader = await request.multipart()
      field = await reader.next()
      if field is None or field.name != "photo":
          return web.json_response({"error": "No photo field"}, status=400)

      content_type = field.headers.get("Content-Type", "")
      if content_type not in ALLOWED_PHOTO_TYPES:
          return web.json_response({"error": "Invalid image type"}, status=400)

      photo_bytes = bytearray()
      size = 0
      while chunk := await field.read_chunk():
          size += len(chunk)
          if size > MAX_PHOTO_SIZE:
              return web.json_response({"error": "File too large"}, status=400)
          photo_bytes.extend(chunk)

      bot: Bot = request.app["bot"]
      if bot is None:
          return web.json_response({"error": "Bot not configured"}, status=500)

      with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
          tmp.write(photo_bytes)
          tmp_path = tmp.name

      try:
          message = await bot.send_photo(chat_id=user_id, photo=FSInputFile(tmp_path))
          file_id = message.photo[-1].file_id
          await bot.delete_message(chat_id=user_id, message_id=message.message_id)
          return web.json_response({"file_id": file_id})
      finally:
          os.remove(tmp_path)
  ```

- [ ] **Step 3: Update CORS headers for multipart**

  In `web_app.py` `cors_middleware`, the existing headers are sufficient because the browser sends `Content-Type: multipart/form-data` automatically (no preflight for simple multipart). Keep current CORS setup.

---

### Task 3: Add `uploadPhoto` to frontend API client

**Files:**
- Modify: `docs/js/api.js`

- [ ] **Step 1: Add multipart request helper**

  ```javascript
  async function uploadRequest(path, formData) {
      const resp = await fetch(`${API_BASE_URL}${path}`, {
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
  ```

- [ ] **Step 2: Expose `uploadPhoto`**

  Update `api` object:
  ```javascript
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

---

### Task 4: Update CSS theme and animations

**Files:**
- Modify: `docs/css/style.css`

- [ ] **Step 1: Replace CSS with new theme + animations**

  ```css
  :root {
      --bg: #000000;
      --surface: #1c1c1e;
      --surface-hover: #2c2c2e;
      --text: #ffffff;
      --text-muted: rgba(255, 255, 255, 0.6);
      --text-on-surface: #000000;
      --accent: #ffffff;
      --radius: 20px;
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
      opacity: 0;
      transform: translateY(10px);
      transition: opacity 0.25s ease-out, transform 0.25s ease-out;
  }

  .screen.active {
      display: flex;
      opacity: 1;
      transform: translateY(0);
  }

  h1, h2, p {
      margin: 0;
  }

  h1 {
      font-size: 28px;
      font-weight: 700;
  }

  h2 {
      text-align: center;
  }

  p {
      color: var(--text-muted);
      line-height: 1.5;
      text-align: center;
  }

  button, .btn {
      border: none;
      border-radius: var(--radius);
      padding: 16px 20px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      background: var(--accent);
      color: var(--text-on-surface);
      text-align: center;
      width: 100%;
      transition: transform 0.15s ease-out, background 0.2s ease-out, color 0.2s ease-out;
  }

  button:active, .btn:active {
      transform: scale(0.97);
  }

  button:disabled, .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
  }

  button.secondary, .btn.secondary {
      background: var(--surface);
      color: var(--text);
  }

  button.secondary:hover, .btn.secondary:hover {
      background: var(--surface-hover);
  }

  button.secondary.selected, .btn.secondary.selected {
      background: var(--accent);
      color: var(--text-on-surface);
  }

  input, select {
      background: var(--surface);
      border: 1px solid transparent;
      border-radius: var(--radius);
      color: var(--text);
      padding: 16px;
      font-size: 16px;
      outline: none;
      width: 100%;
      text-align: center;
      transition: border-color 0.2s ease-out, box-shadow 0.2s ease-out;
  }

  input::placeholder {
      color: var(--text-muted);
      text-align: center;
  }

  input:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2);
  }

  .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
  }

  .chip {
      background: var(--surface);
      color: var(--text);
      border-radius: 20px;
      padding: 8px 14px;
      font-size: 14px;
      cursor: pointer;
      user-select: none;
      opacity: 0;
      transform: translateY(8px);
      animation: chipIn 0.25s ease-out forwards;
  }

  @keyframes chipIn {
      to {
          opacity: 1;
          transform: translateY(0);
      }
  }

  .chip.selected {
      background: var(--accent);
      color: var(--text-on-surface);
  }

  .options {
      display: flex;
      flex-direction: column;
      gap: 12px;
  }

  .option {
      opacity: 0;
      transform: translateY(8px);
      animation: optionIn 0.25s ease-out forwards;
  }

  @keyframes optionIn {
      to {
          opacity: 1;
          transform: translateY(0);
      }
  }

  .step-counter {
      color: var(--text-muted);
      font-size: 14px;
      text-align: center;
  }

  .error {
      color: var(--text);
      font-size: 14px;
      text-align: center;
      opacity: 0.9;
  }

  .photo-preview {
      width: 160px;
      height: 160px;
      border-radius: 50%;
      object-fit: cover;
      align-self: center;
      border: 2px solid var(--surface);
  }

  .photo-input {
      display: none;
  }
  ```

---

### Task 5: Update registration screen with animations and photo upload

**Files:**
- Modify: `docs/js/screens/registration.js`

- [ ] **Step 1: Wrap option buttons in `.options` container**

  Change render functions for gender/looking_for/goal from:
  ```javascript
  container.innerHTML = GENDER_OPTIONS.map(o =>
      `<button class="secondary option" data-value="${o.value}">${o.label}</button>`
  ).join("<br><br>");
  ```
  to:
  ```javascript
  container.innerHTML = `<div class="options">${GENDER_OPTIONS.map((o, i) =>
      `<button class="secondary option" data-value="${o.value}" style="animation-delay: ${i * 50}ms">${o.label}</button>`
  ).join("")}</div>`;
  ```
  Do the same for `LOOKING_OPTIONS` and `GOAL_OPTIONS`.

- [ ] **Step 2: Add stagger delays to interest chips**

  Change:
  ```javascript
  container.innerHTML = `<div class="chips">${INTERESTS.map(i =>
      `<span class="chip ${profile.interests.has(i) ? "selected" : ""}" data-value="${i}">${i}</span>`
  ).join("")}</div>`;
  ```
  to:
  ```javascript
  container.innerHTML = `<div class="chips">${INTERESTS.map((i, idx) =>
      `<span class="chip ${profile.interests.has(i) ? "selected" : ""}" data-value="${i}" style="animation-delay: ${idx * 30}ms">${i}</span>`
  ).join("")}</div>`;
  ```

- [ ] **Step 3: Replace photo step with upload UI**

  Change the `photo` step from:
  ```javascript
  container.innerHTML = `
      <p>Фото повышает количество лайков. Пока можешь пропустить.</p>
      <button class="secondary" id="skipPhoto">Пропустить</button>
  `;
  document.getElementById("skipPhoto").addEventListener("click", () => submit());
  ```
  to:
  ```javascript
  container.innerHTML = `
      <p>Фото повышает количество лайков. Пока можешь пропустить.</p>
      <img id="photoPreview" class="photo-preview" src="" alt="" style="display:none;">
      <input type="file" id="photoInput" class="photo-input" accept="image/*">
      <button class="secondary" id="choosePhoto">Выбрать фото</button>
      <button class="secondary" id="skipPhoto">Пропустить</button>
  `;

  const photoInput = document.getElementById("photoInput");
  const photoPreview = document.getElementById("photoPreview");
  const choosePhoto = document.getElementById("choosePhoto");

  choosePhoto.addEventListener("click", () => photoInput.click());

  photoInput.addEventListener("change", async () => {
      const file = photoInput.files[0];
      if (!file) return;
      photoPreview.src = URL.createObjectURL(file);
      photoPreview.style.display = "block";
      choosePhoto.textContent = "Загрузка...";
      choosePhoto.disabled = true;
      try {
          const data = await api.uploadPhoto(file);
          profile.photo_file_id = data.file_id;
          choosePhoto.textContent = "Фото загружено";
      } catch (e) {
          document.getElementById("error").textContent = e.message;
          choosePhoto.textContent = "Выбрать фото";
          choosePhoto.disabled = false;
      }
  });

  document.getElementById("skipPhoto").addEventListener("click", () => submit());
  ```

- [ ] **Step 4: Keep existing option selection logic with `.selected` class**

  Ensure the click handler uses:
  ```javascript
  container.querySelectorAll(".option").forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  ```

---

### Task 6: Manual verification

**Files:**
- Test in browser: `docs/index.html`

- [ ] **Step 1: Serve docs locally**

  Run:
  ```bash
  python -m http.server 3000 --directory docs
  ```

- [ ] **Step 2: Start backend with tunnel**

  Run bot + tunnel as before (`cloudflared --url http://localhost:8080`), update `docs/js/config.js` if tunnel URL changed.

- [ ] **Step 3: Open Mini App and verify**

  - No red anywhere.
  - Black/dark-gray/white palette.
  - Step transitions are smooth.
  - Buttons scale on press.
  - Option buttons and interest chips animate in.
  - Photo step: choose image → preview appears → upload succeeds → registration completes.
  - Skip photo still works.

- [ ] **Step 4: Stop local server**

  Press `Ctrl+C`.

---

### Task 7: Commit, push, and wipe DB

- [ ] **Step 1: Add and commit**

  ```bash
  git add docs/css/style.css docs/js/screens/registration.js docs/js/api.js web_app.py web_routes.py znakomstvabot.py
  git commit -m "feat(miniapp): redesign theme, animations, photo upload"
  ```

- [ ] **Step 2: Push**

  Use the GitHub token if needed.

- [ ] **Step 3: Wipe DB**

  ```bash
  rm dating_bot.db
  ```

---

## Self-Review

- **Spec coverage:**
  - Remove red / dark-gray-black-white theme → Task 4.
  - Animations → Task 4 CSS + Task 5 stagger delays.
  - Photo upload → Tasks 1, 2, 3, 5.
  - Optional photo → Task 5 skip button remains.
- **Placeholder scan:** No TBD/TODO/fill-in-details found.
- **Type consistency:** `file_id` returned by backend and stored in `profile.photo_file_id`; `api.uploadPhoto` returns `{file_id}` consistently.
