# Улучшения Mini App dating-бота

> **For agentic workers:** реализуйте задачи последовательно, коммитьте после завершения логического блока.

**Goal:** Убрать старое бот-меню, улучшить уведомления о взаимных лайках, расширить интересы, добавить редактирование профиля в настройки Mini App.

**Architecture:** Минимальные изменения в существующих handlers/web_routes + новые frontend-экраны редакторов профиля. Единый список интересов в `config.py`.

**Tech Stack:** Python 3.12, aiogram 3.29, aiohttp, aiosqlite, pytest; frontend — vanilla JS.

---

### Task 1: Убрать старое меню из /start
**Files:**
- Modify: `handlers/common.py`
- Modify: `handlers/menu.py` (удалить/отключить)
- Modify: `keyboards.py` (удалить `main_menu_keyboard`)

**Steps:**
- [ ] В `cmd_start`, если пользователь зарегистрирован, отправить сообщение «Регистрация успешно пройдена! Заходи в приложение» с кнопкой WebApp.
- [ ] Удалить `handlers/menu.py` и импорты `show_main_menu` из `handlers/common.py`.
- [ ] Удалить `main_menu_keyboard` из `keyboards.py` и все её использования.
- [ ] Запустить тесты: `PYTHONIOENCODING=utf-8 .venv/Scripts/pytest tests/ -v`

### Task 2: Приветственное сообщение после Mini App регистрации
**Files:**
- Modify: `web_routes.py` (`register` endpoint)
- Modify: `handlers/registration.py` (переиспользуемый helper для WebApp-кнопки)

**Steps:**
- [ ] После успешного `add_user` в `POST /api/register` отправить через `bot.send_message` то же сообщение с WebApp-кнопкой.
- [ ] Вынести формирование WebApp-кнопки в небольшой хелпер, чтобы не дублировать код.
- [ ] Запустить тесты.

### Task 3: Улучшить контакт при взаимном лайке
**Files:**
- Modify: `handlers/browse.py` (`_notify_mutual_match`, `_contact_markup`)
- Modify: `handlers/likes.py` (`like_back`)
- Modify: `web_routes.py` (`_send_match_notifications`, `_contact_markup`)

**Steps:**
- [ ] Функция `_contact_markup` возвращает `None`, если нет username и deep link по ID невозможен/бесполезен.
- [ ] При mutual like сначала пробовать `https://t.me/{username}`, затем `tg://user?id={user_id}`. Если оба варианта не дали кнопку — отправить fallback-текст.
- [ ] Обновить тесты mutual like.
- [ ] Запустить тесты.

### Task 4: Расширить интересы
**Files:**
- Modify: `config.py` (`INTEREST_CATEGORIES`)
- Modify: `docs/js/screens/registration.js`
- Create: `docs/js/components/interestPicker.js`
- Modify: `docs/js/screens/profile.js`

**Steps:**
- [ ] Добавить игровые интересы в `INTEREST_CATEGORIES`.
- [ ] Добавить endpoint `/api/interests`, возвращающий `INTEREST_CATEGORIES`.
- [ ] В Mini App заменить плоский список интересов на компонент `interestPicker`, который рендерит категории и чипы.
- [ ] Использовать `interestPicker` в регистрации и в редактировании профиля.
- [ ] Запустить тесты.

### Task 5: Редактирование профиля в настройках
**Files:**
- Modify: `docs/js/screens/settings.js`
- Create: `docs/js/screens/editProfile.js`
- Create: `docs/js/screens/editField.js`
- Modify: `docs/js/api.js` (при необходимости)
- Modify: `web_routes.py` (`PUT /api/me`)

**Steps:**
- [ ] В `settings.js` добавить карточку «Моя анкета» со списком полей и их значений.
- [ ] При тапе на поле открывать `editField.js` — универсальный редактор: input/text/selector/interestPicker/photo.
- [ ] Реализовать `editProfile.js` как обёртку/роутер, если нужно.
- [ ] Убедиться, что `PUT /api/me` корректно обновляет все поля.
- [ ] Запустить тесты.

### Task 6: Финальная проверка
**Steps:**
- [ ] Запустить полный тестовый набор.
- [ ] Сделать git commit и push.
- [ ] Удалить `dating_bot.db`.

---

## Self-Review
- Spec coverage: все 4 пункта спецификации покрыты задачами.
- Placeholders: нет TBD/TODO.
- Type consistency: используются существующие эндпоинты `/api/me`, `/api/register`.
