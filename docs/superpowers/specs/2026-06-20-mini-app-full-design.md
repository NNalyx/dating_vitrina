# Mini App Full Functionality Design

## Goal
Move the remaining bot features (feed, likes, profile editing, settings/filters) into the Mini App and inline city validation during registration. After registration the user lands directly in the feed. The Telegram bot main menu is no longer the primary UI.

## Architecture
- **Backend:** Extend `web_routes.py` with REST endpoints for feed actions, incoming likes, profile edits, and settings.
- **Frontend:** Extend the existing SPA with screen modules: `feed.js`, `likes.js`, `profile.js`, `settings.js`. `app.js` manages the active screen and bottom navigation.
- **Style:** Keep the existing black/dark-gray/white theme and animations (`style.css`).
- **Bot handlers:** Existing handlers in `handlers/menu.py`, `handlers/browse.py`, etc. remain as a fallback but are not surfaced to Mini App users.

## Backend Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/validate-city` | Validate and normalize a city name. Returns `{valid: bool, normalized?: string, error?: string}`. |
| GET | `/api/feed` | Return next candidate `{user_id, name, age, city, goal, interests, photo_file_id, compatibility}` or `{done: true}`. |
| POST | `/api/feed/{id}/like` | Like candidate; handles mutual match. |
| POST | `/api/feed/{id}/skip` | Skip candidate. |
| GET | `/api/likes` | Return list of incoming likes. |
| POST | `/api/likes/{id}/like_back` | Reciprocate like. |
| POST | `/api/likes/{id}/skip` | Skip incoming like. |
| GET | `/api/me` | Existing; return own profile. |
| PUT | `/api/me` | Update editable fields: name, age, looking_for, goal, interests, city, photo_file_id. |
| GET | `/api/settings` | Return filters and notifications flag. |
| PUT | `/api/settings` | Update filters and notifications flag. |

## Frontend Screens

### Registration City Step
- Debounced input triggers `POST /api/validate-city`.
- Inline error shown if invalid.
- Next button disabled until valid.

### Feed (`renderFeed`)
- Full-screen card with candidate photo, gradient fade at bottom.
- Text overlay: name, age, city, compatibility, goal, interests.
- Swipe left/right animation or like/skip buttons.
- On action, animate card off-screen and load next candidate.
- Empty state: "Пока нет подходящих анкет".

### Likes (`renderLikes`)
- List of incoming likes as compact cards.
- Like back / skip buttons.
- Empty state: "У тебя пока нет новых лайков".

### My Profile (`renderProfile`)
- Display own card with photo.
- Edit buttons per field (name, age, looking_for, goal, interests, city, photo).
- Save via `PUT /api/me`.

### Settings (`renderSettings`)
- Filters: min/max age steppers, only-my-city toggle.
- Notifications toggle.
- Save via `PUT /api/settings`.

### Bottom Navigation
- Icons/labels: Лента, Лайки, Профиль, Настройки.
- Profile button shows user's photo as a small circle.
- Active item highlighted with white accent.

## Data Flow
1. `app.js` calls `/api/auth`.
2. If not registered → welcome → registration → on complete `renderFeed`.
3. If registered → `renderFeed`.
4. Bottom nav switches screen modules, each fetching its own data.

## Error Handling
- API errors shown as inline messages or toast-like text.
- Invalid city blocks progress during registration.

## Testing
- Unit tests for `/api/validate-city`.
- Tests for feed endpoint with filters.
- Tests for likes endpoint and like-back mutual match.
- Tests for profile/settings update endpoints.
