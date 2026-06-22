# Дизайн: Telegram Mini App — Фаза 1 (скелет + регистрация)

## Контекст

Telegram-бот знакомств на Python (aiogram) с SQLite. Уже реализованы: регистрация через чат, лайки, лента, фильтры, настройки.

Цель Фазы 1 — дать пользователю красивый интерфейс миниаппа для регистрации, запущенный через GitHub Pages, с сохранением данных в ту же базу через бэкенд внутри процесса бота.

## Scope (Фаза 1)

- Статический фронтенд миниаппа в папке `miniapp/`.
- Тёмная минималистичная визуальная тема.
- Проверка Telegram `initData` на бэкенде.
- Экран приветствия и пошаговая регистрация в миниаппе.
- API-эндпоинты:
  - `POST /api/auth` — валидация `initData`, возврат статуса регистрации.
  - `POST /api/register` — сохранение профиля.
  - `GET /api/me` — получение профиля текущего пользователя.
- Запуск веб-сервера (`aiohttp`) в одном процессе с ботом.
- Бот оставляет только: `/start` → политика → кнопка открытия миниаппа.

## Out of scope (Фаза 1)

- Лента анкет и лайки (Фаза 2).
- Взаимные лайки и уведомления (Фаза 2).
- Профиль/настройки в миниаппе (Фаза 3).
- Сложные анимации и офлайн-режим.
- Отдельный деплой бэкенда на VPS/хостинг — пока локальный запуск + ngrok/Cloudflare Tunnel для тестов из Telegram.

## Архитектура

```
┌─────────────────────┐
│   Telegram client   │
└──────────┬──────────┘
           │ Web App button
           ▼
┌─────────────────────┐      HTTPS       ┌──────────────────────┐
│  GitHub Pages       │ ◄────────────────│  User's browser      │
│  (static files)     │                  │  inside Telegram     │
└─────────────────────┘                  └──────────┬───────────┘
                                                    │
                                                    │ fetch(initData)
                                                    ▼
                                           ┌─────────────────────┐
                                           │  aiohttp backend    │
                                           │  (same process as   │
                                           │   aiogram bot)      │
                                           └──────────┬──────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────────┐
                                           │  SQLite dating_bot.db│
                                           └─────────────────────┘
```

## Файловая структура

```
PycharmProjects/PythonProject/
├── miniapp/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js
│       ├── api.js
│       └── screens/
│           ├── welcome.js
│           ├── registration.js
│           └── home.js
├── web_app.py              # aiohttp app + initData validation
├── web_routes.py           # API route handlers
├── web_config.py           # BACKEND_URL, allowed origins
├── znakomstvabot.py        # launches both bot and web server
├── config.py               # BOT_TOKEN reused for initData hash
└── tests/
    ├── test_web_auth.py
    └── test_web_register.py
```

## Визуальная тема

- Фон: `#0f0f0f` или `#121212`.
- Карточки: `#1c1c1e` с скруглением `16px`.
- Акцент: `#ff2d55` или `#8b5cf6` (розово-фиолетовый градиент).
- Текст: `#ffffff` primary, `#8e8e93` secondary.
- Шрифт: системный sans-serif (Telegram uses San Francisco/Inter/Roboto).
- Минимум теней, много воздуха, крупные кнопки.

## Telegram initData

При открытии миниаппа Telegram передаёт строку `initData` в URL-хеше или через `Telegram.WebApp.initData`.

Пример:
```
query_id=AAHdF6IQAAAAAN0XohDhrOrc
&user=%7B%22id%22%3A123456%2C%22first_name%22%3A%22Anna%22%7D
&auth_date=1690000000
&hash=abc123...
```

Проверка на бэкенде:
1. Убрать поле `hash`.
2. Отсортировать оставшиеся key=value по ключу.
3. Склеить через `\n`.
4. Вычислить HMAC-SHA256 от этой строки с ключом = HMAC-SHA256(`WebAppData`, BOT_TOKEN).
5. Сравнить с `hash` (constant-time).

## API

### `POST /api/auth`

Request body:
```json
{
  "initData": "query_id=...&hash=..."
}
```

Response 200:
```json
{
  "user_id": 123456,
  "is_registered": false
}
```

Response 401:
```json
{
  "error": "Invalid initData"
}
```

### `POST /api/register`

Request body:
```json
{
  "initData": "...",
  "age": 25,
  "name": "Анна",
  "gender": "female",
  "looking_for": "male",
  "goal": "relationship",
  "interests": ["Музыка", "Спорт"],
  "city": "Москва",
  "photo_file_id": null
}
```

Response 201:
```json
{
  "status": "ok"
}
```

Response 400:
```json
{
  "error": "Name contains profanity"
}
```

### `GET /api/me`

Headers: `X-Init-Data: ...`

Response 200:
```json
{
  "user_id": 123456,
  "name": "Анна",
  "age": 25,
  "gender": "female",
  "looking_for": "male",
  "goal": "relationship",
  "interests": "Музыка,Спорт",
  "city": "Москва",
  "photo_file_id": null
}
```

## Пошаговая регистрация в миниаппе

1. **Возраст** — цифровой ввод, кнопка «Далее».
2. **Имя** — текст, проверка длины и мата.
3. **Пол** — кнопки: Парень / Девушка / Другое.
4. **Кого ищешь** — Парней / Девушек / Всех.
5. **Цель** — Отношения / Дружба / Флирт.
6. **Интересы** — чипсы по категориям, минимум 3.
7. **Город** — текст с валидацией.
8. **Фото** — optional, кнопка «Пропустить».

После завершения: `POST /api/register` → показать главный экран.

## Бот (оставляем минимум)

Команда `/start`:
1. Если пользователь не согласился с политикой — показать политику и кнопку «Согласен».
2. После согласия — отправить сообщение:
   ```
   🚀 Добро пожаловать! Нажми кнопку ниже, чтобы продолжить в приложении.
   ```
   С кнопкой `web_app`.

## Запуск

```bash
cd PycharmProjects/PythonProject
PYTHONIOENCODING=utf-8 .venv/Scripts/python znakomstvabot.py
```

Бот и веб-сервер стартуют одновременно в одном event loop.

## Локальное тестирование через Telegram

1. Запустить бота.
2. Запустить туннель:
   ```bash
   ngrok http 8080
   ```
3. Полученный HTTPS-URL прописать в `miniapp/js/config.js` как `API_BASE_URL`.
4. Обновить Mini App URL в @BotFather на URL GitHub Pages.
5. Проверить регистрацию через Telegram.

## Безопасность

- `initData` проверяется на каждом запросе.
- CORS разрешён только для домена GitHub Pages.
- Файл `config.py` с `BOT_TOKEN` не попадает в Git.
- `photo_file_id` приходит из Telegram позже (загрузка фото через бота); в Фазе 1 фото опционально и может быть пропущено.

## Тесты

- `tests/test_web_auth.py`:
  - Валидная `initData` → 200 + `user_id`.
  - Невалидная `initData` → 401.
- `tests/test_web_register.py`:
  - Регистрация нового пользователя → 201 + запись в БД.
  - Регистрация с матом в имени → 400.
  - Дублирование регистрации → 409 или обновление.

## Success criteria

- Миниапп открывается из Telegram по кнопке.
- Пользователь проходит регистрацию в миниаппе.
- Данные сохраняются в `dating_bot.db`.
- `initData` валидируется на бэкенде.
- Все тесты проходят.
- GitHub Pages раздаёт статику миниаппа.
