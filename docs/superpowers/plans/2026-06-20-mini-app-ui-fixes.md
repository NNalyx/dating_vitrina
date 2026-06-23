# Mini App UI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Center-align Mini App form fields, switch to black/white/red color scheme, and fix selected-state highlight for option buttons.

**Architecture:** Pure frontend CSS/JS tweak. Update CSS variables and rules in `docs/css/style.css`, then switch `docs/js/screens/registration.js` from inline `borderColor` to a `.selected` class for option buttons.

**Tech Stack:** Static HTML/JS/CSS (Telegram Mini App).

---

## File Structure

- `docs/css/style.css` — theme variables, layout, button/input styles.
- `docs/js/screens/registration.js` — option button rendering and selection logic.

---

### Task 1: Update CSS theme and alignment

**Files:**
- Modify: `docs/css/style.css`

- [ ] **Step 1: Replace CSS variables and base styles**

  Replace the `:root` block and the `body`, `button`, `.btn`, `.secondary`, `input`, `select`, `.chip`, `.chip.selected` rules with the black/white/red theme and centered text.

  ```css
  :root {
      --bg: #000000;
      --surface: #ffffff;
      --text: #ffffff;
      --text-on-surface: #000000;
      --accent: #ff0000;
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
      color: var(--text);
      opacity: 0.7;
      line-height: 1.5;
  }

  button, .btn {
      border: none;
      border-radius: var(--radius);
      padding: 16px 20px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      background: var(--accent);
      color: var(--text);
      text-align: center;
      width: 100%;
      transition: opacity 0.2s;
  }

  button:disabled, .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
  }

  button.secondary, .btn.secondary {
      background: var(--surface);
      color: var(--text-on-surface);
  }

  button.secondary.selected, .btn.secondary.selected {
      background: var(--accent);
      color: var(--text);
  }

  input, select {
      background: var(--surface);
      border: 1px solid transparent;
      border-radius: var(--radius);
      color: var(--text-on-surface);
      padding: 16px;
      font-size: 16px;
      outline: none;
      width: 100%;
      text-align: center;
  }

  input::placeholder {
      color: var(--text-on-surface);
      opacity: 0.5;
      text-align: center;
  }

  input:focus, select:focus {
      border-color: var(--accent);
  }

  .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
  }

  .chip {
      background: var(--surface);
      color: var(--text-on-surface);
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
      opacity: 0.7;
      font-size: 14px;
  }

  .error {
      color: var(--accent);
      font-size: 14px;
      text-align: center;
  }
  ```

- [ ] **Step 2: Verify CSS file is valid**

  Read `docs/css/style.css` and confirm:
  - every opening `{` has a matching `}`;
  - `:root` variables `--bg`, `--surface`, `--text`, `--text-on-surface`, `--accent` are defined;
  - no references to removed `--accent-2` remain.

---

### Task 2: Fix selected-state logic for option buttons

**Files:**
- Modify: `docs/js/screens/registration.js:96-104`

- [ ] **Step 1: Replace inline borderColor with class toggle**

  Change the option-button click handler from:

  ```javascript
  container.querySelectorAll(".option").forEach(btn => {
      btn.addEventListener("click", () => {
          if (id === "gender") profile.gender = btn.dataset.value;
          if (id === "looking_for") profile.looking_for = btn.dataset.value;
          if (id === "goal") profile.goal = btn.dataset.value;
          container.querySelectorAll(".option").forEach(b => b.style.borderColor = "");
          btn.style.borderColor = "var(--accent)";
      });
  });
  ```

  to:

  ```javascript
  container.querySelectorAll(".option").forEach(btn => {
      btn.addEventListener("click", () => {
          if (id === "gender") profile.gender = btn.dataset.value;
          if (id === "looking_for") profile.looking_for = btn.dataset.value;
          if (id === "goal") profile.goal = btn.dataset.value;
          container.querySelectorAll(".option").forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");
      });
  });
  ```

- [ ] **Step 2: Verify JS syntax**

  Run:
  ```bash
  node --check docs/js/screens/registration.js
  ```

  Expected: no output (success).

---

### Task 3: Manual verification

**Files:**
- Test in browser: `docs/index.html`

- [ ] **Step 1: Serve docs folder locally**

  Run:
  ```bash
  python -m http.server 3000 --directory docs
  ```

- [ ] **Step 2: Open in browser**

  Open: http://localhost:3000

- [ ] **Step 3: Check the following**

  - Background is black, text is white.
  - Input fields are white with black centered text and centered placeholder.
  - Option buttons (Парень/Девушка/Другое, Парней/Девушек/Всех, Отношения/Дружба/Флирт) are white, full-width, text centered.
  - Tapping an option button turns it red with white text; other buttons in the same group revert to white.
  - Interest chips are white; selected chips turn red.
  - The primary "Далее" button is red with white text.

- [ ] **Step 4: Stop the local server**

  Press `Ctrl+C` in the terminal.

---

## Self-Review

- **Spec coverage:**
  - Center alignment → Task 1 (`width: 100%`, `text-align: center`, full-width option buttons).
  - Black/white/red theme → Task 1 (updated CSS variables and rules).
  - Selected highlight for option buttons → Task 2 (class-based `.selected`).
- **Placeholder scan:** No TBD/TODO/fill-in-details found.
- **Type consistency:** CSS variables match usage in both files; JS uses `classList.add/remove("selected")` consistently.
