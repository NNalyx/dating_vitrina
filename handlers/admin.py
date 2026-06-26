import json
import os
import tempfile

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from config import GENDER_OPTIONS, GOAL_OPTIONS, LOOKING_FOR_OPTIONS
from database import (
    add_admin_log,
    add_fake_user,
    add_interest,
    ban_user,
    delete_fake_users,
    delete_user,
    get_admin_logs,
    get_admin_stats,
    get_all_users,
    get_banned_users,
    get_fake_users,
    get_interests_from_db,
    get_pending_reports,
    get_report,
    get_user,
    get_user_by_username,
    remove_category,
    remove_interest,
    resolve_report,
    unban_user,
)
from keyboards import (
    admin_back_menu_keyboard,
    admin_bans_keyboard,
    admin_fakes_keyboard,
    admin_interest_category_keyboard,
    admin_interests_keyboard,
    admin_menu_keyboard,
    fake_confirm_keyboard,
    fake_options_keyboard,
    fake_photo_keyboard,
)
from services.admin import is_admin
from services.profile import format_profile
from states import AdminMenu

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user is None or not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    await message.answer(
        "<b>🔧 Админ-панель</b>",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:menu")
async def admin_back_to_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text(
            "<b>🔧 Админ-панель</b>",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()



def _parse_user_identifier(text: str) -> tuple[str, str | int]:
    text = text.strip()
    if text.startswith("@"):
        return "username", text[1:]
    if text.isdigit():
        return "id", int(text)
    return "username", text


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text(
        "Введи <b>user_id</b> или <b>@username</b>:",
        reply_markup=admin_back_menu_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminMenu.users_search)
    await callback.answer()


@router.message(AdminMenu.users_search)
async def admin_user_lookup(message: types.Message, state: FSMContext) -> None:
    text = message.text or ""
    kind, value = _parse_user_identifier(text)
    user = await get_user(value) if kind == "id" else await get_user_by_username(value)
    if user is None:
        await message.answer(
            "Пользователь не найден.",
            reply_markup=admin_back_menu_keyboard(),
        )
        return
    await _show_user_profile(message, user)
    await state.clear()


async def _show_user_profile(message: types.Message, user: dict) -> None:
    text = format_profile(user, title="👤 Анкета пользователя")
    banned = bool(user.get("is_banned"))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⛔ Забанить" if not banned else "✅ Разбанить",
                    callback_data=f"admin:ban:{user['user_id']}:{int(not banned)}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить анкету",
                    callback_data=f"admin:delete:{user['user_id']}",
                )
            ],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:users")],
        ]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")



async def _refresh_user_profile(
    callback: types.CallbackQuery, user_id: int, *, back_callback: str = "admin:users"
) -> None:
    user = await get_user(user_id)
    if user is None:
        if callback.message is not None:
            await callback.message.edit_text(
                "Пользователь не найден.",
                reply_markup=admin_menu_keyboard(),
            )
        return

    banned = bool(user.get("is_banned"))
    text = format_profile(user, title="👤 Анкета пользователя")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⛔ Забанить" if not banned else "✅ Разбанить",
                    callback_data=f"admin:ban:{user_id}:{int(not banned)}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить анкету",
                    callback_data=f"admin:delete:{user_id}",
                )
            ],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=back_callback)],
        ]
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:ban:"))
async def admin_ban_toggle(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    user_id = int(parts[2])
    ban = int(parts[3])
    if ban:
        await ban_user(user_id)
        action = "ban"
        text = "Пользователь заблокирован."
    else:
        await unban_user(user_id)
        action = "unban"
        text = "Пользователь разблокирован."
    await add_admin_log(callback.from_user.id, action, user_id)
    await callback.answer(text)
    await _refresh_user_profile(callback, user_id)


@router.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete_user(callback: types.CallbackQuery, state: FSMContext) -> None:
    user_id = int(callback.data.split(":")[2])
    await delete_user(user_id)
    await add_admin_log(callback.from_user.id, "delete_user", user_id)
    await callback.answer("Анкета удалена.")
    if callback.message is not None:
        await callback.message.edit_text(
            "Анкета удалена.",
            reply_markup=admin_menu_keyboard(),
        )



@router.callback_query(F.data == "admin:reports")
async def admin_reports(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    reports = await get_pending_reports(limit=10)
    if not reports:
        if callback.message is not None:
            await callback.message.edit_text(
                "Нет открытых жалоб.",
                reply_markup=admin_menu_keyboard(),
            )
        await callback.answer()
        return

    rows = []
    for r in reports:
        text = f"#{r['report_id']} от {r['reporter_id']} на {r['reported_id']}"
        rows.append(
            [InlineKeyboardButton(text=text, callback_data=f"admin:report:{r['report_id']}")]
        )
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")])

    if callback.message is not None:
        await callback.message.edit_text(
            "Открытые жалобы:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:report:"))
async def admin_report_detail(callback: types.CallbackQuery, state: FSMContext) -> None:
    report_id = int(callback.data.split(":")[2])
    report = await get_report(report_id)
    if report is None:
        await callback.answer("Жалоба не найдена.")
        return

    text = (
        f"<b>Жалоба #{report_id}</b>\n"
        f"От: {report['reporter_id']}\n"
        f"На: {report['reported_id']}\n"
        f"Причина: {report['reason']}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Анкета",
                    callback_data=f"admin:viewuser:{report['reported_id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⛔ Забанить",
                    callback_data=f"admin:banfromreport:{report_id}:{report['reported_id']}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Отклонить",
                    callback_data=f"admin:reportdismiss:{report_id}",
                )
            ],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:reports")],
        ]
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:banfromreport:"))
async def admin_ban_from_report(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    report_id = int(parts[2])
    user_id = int(parts[3])
    await ban_user(user_id)
    await resolve_report(report_id, "resolved")
    await add_admin_log(
        callback.from_user.id,
        "ban_from_report",
        user_id,
        f"report_id={report_id}",
    )
    await callback.answer("Пользователь забанен, жалоба закрыта.")
    await admin_reports(callback, state)


@router.callback_query(F.data.startswith("admin:reportdismiss:"))
async def admin_dismiss_report(callback: types.CallbackQuery, state: FSMContext) -> None:
    report_id = int(callback.data.split(":")[2])
    await resolve_report(report_id, "dismissed")
    await add_admin_log(
        callback.from_user.id,
        "dismiss_report",
        details=f"report_id={report_id}",
    )
    await callback.answer("Жалоба отклонена.")
    await admin_reports(callback, state)


@router.callback_query(F.data.startswith("admin:viewuser:"))
async def admin_view_reported_user(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user_id = int(callback.data.split(":")[2])
    user = await get_user(user_id)
    if user is None:
        await callback.answer("Анкета не найдена.")
        return
    await _refresh_user_profile(callback, user_id, back_callback="admin:reports")
    await callback.answer()


@router.callback_query(F.data == "admin:bans")
async def admin_bans(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    banned = await get_banned_users(limit=20)
    if not banned:
        if callback.message is not None:
            await callback.message.edit_text(
                "Забаненных пользователей нет.",
                reply_markup=admin_menu_keyboard(),
            )
        await callback.answer()
        return

    text = f"<b>🚫 Забаненные пользователи ({len(banned)})</b>\n\nНажми, чтобы разбанить:"
    if callback.message is not None:
        await callback.message.edit_text(
            text,
            reply_markup=admin_bans_keyboard(banned),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:unban:"))
async def admin_unban_user(callback: types.CallbackQuery, state: FSMContext) -> None:
    user_id = int(callback.data.split(":")[2])
    await unban_user(user_id)
    await add_admin_log(callback.from_user.id, "unban", user_id)
    await callback.answer("Пользователь разбанен.")
    await admin_bans(callback, state)


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: types.CallbackQuery) -> None:
    stats = await get_admin_stats()
    text = (
        f"<b>📊 Статистика</b>\n\n"
        f"Всего пользователей: {stats['total_users']}\n"
        f"Новых за сутки: {stats['new_today']}\n"
        f"Новых за неделю: {stats['new_week']}\n"
        f"Новых за месяц: {stats['new_month']}\n"
        f"Всего лайков: {stats['total_likes']}\n"
        f"Всего просмотров: {stats['total_views']}\n"
        f"Активных пользователей: {stats['active_users']}\n"
        f"Открытых жалоб: {stats['pending_reports']}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📁 Экспорт JSON", callback_data="admin:export")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")],
        ]
    )
    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:export")
async def admin_export(callback: types.CallbackQuery) -> None:
    stats = await get_admin_stats()
    users = await get_all_users()
    reports = await get_pending_reports(limit=1000)
    data = {"stats": stats, "users": users, "reports": reports}

    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    await callback.message.answer_document(FSInputFile(path), caption="Экспорт данных")
    os.remove(path)
    await callback.answer()



@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    if callback.message is not None:
        await callback.message.edit_text(
            "Введи текст рассылки:",
            reply_markup=admin_back_menu_keyboard(),
        )
    await state.set_state(AdminMenu.broadcast_text)
    await callback.answer()


@router.message(AdminMenu.broadcast_text)
async def admin_broadcast_preview(message: types.Message, state: FSMContext) -> None:
    text = message.text or ""
    await state.update_data(broadcast_text=text)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Отправить всем", callback_data="admin:broadcast:send")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:menu")],
        ]
    )
    await message.answer(
        f"<b>Предпросмотр:</b>\n\n{text}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(AdminMenu.broadcast_confirm)


@router.callback_query(F.data == "admin:broadcast:send", AdminMenu.broadcast_confirm)
async def admin_broadcast_send(
    callback: types.CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    users = await get_all_users()
    sent = 0
    for user in users:
        if user.get("is_banned"):
            continue
        try:
            await bot.send_message(chat_id=user["user_id"], text=text)
            sent += 1
        except Exception:
            pass
    await add_admin_log(callback.from_user.id, "broadcast", details=f"sent={sent}")
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text(
            f"Рассылка завершена. Доставлено: {sent}",
            reply_markup=admin_menu_keyboard(),
        )
    await callback.answer()



@router.callback_query(F.data == "admin:interests")
async def admin_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    categories = await get_interests_from_db()
    if callback.message is not None:
        await callback.message.edit_text(
            "🏷 Управление интересами",
            reply_markup=admin_interests_keyboard(categories),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:intcat:"))
async def admin_interest_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 2)[2]
    if key == "add":
        if callback.message is not None:
            await callback.message.edit_text(
                "Введи ключ и название категории через запятую (например: games, 🎮 Игры):",
                reply_markup=admin_back_menu_keyboard(),
            )
        await state.set_state(AdminMenu.interest_category_key)
        await callback.answer()
        return

    categories = await get_interests_from_db()
    cat = next((c for c in categories if c["key"] == key), None)
    if cat is None:
        await callback.answer("Категория не найдена.")
        return
    if callback.message is not None:
        await callback.message.edit_text(
            f"{cat['label']}\n\nВыбери интерес для удаления или добавь новый:",
            reply_markup=admin_interest_category_keyboard(cat["key"], cat["items"]),
        )
    await callback.answer()


@router.message(AdminMenu.interest_category_key)
async def admin_add_category(message: types.Message, state: FSMContext) -> None:
    text = message.text or ""
    parts = [p.strip() for p in text.split(",", 1)]
    if len(parts) != 2:
        await message.answer("Нужно ввести ключ и название через запятую.")
        return
    key, label = parts
    await state.update_data(interest_key=key, interest_label=label)
    await message.answer(
        "Введи название интереса для этой категории:",
        reply_markup=admin_back_menu_keyboard(),
    )
    await state.set_state(AdminMenu.interest_name)


@router.callback_query(F.data.startswith("admin:intadd:"))
async def admin_add_interest_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 2)[2]
    categories = await get_interests_from_db()
    cat = next((c for c in categories if c["key"] == key), None)
    if cat is None:
        await callback.answer("Категория не найдена.")
        return
    await state.update_data(interest_key=key, interest_label=cat["label"])
    if callback.message is not None:
        await callback.message.edit_text(
            "Введи название нового интереса:",
            reply_markup=admin_back_menu_keyboard(),
        )
    await state.set_state(AdminMenu.interest_name)
    await callback.answer()


@router.message(AdminMenu.interest_name)
async def admin_save_interest(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = data.get("interest_key")
    label = data.get("interest_label")
    name = (message.text or "").strip()
    if not key or not label or not name:
        await message.answer("Ошибка: не хватает данных.")
        return
    await add_interest(key, label, name)
    await add_admin_log(
        message.from_user.id,
        "add_interest",
        details=f"{key}/{name}",
    )
    await message.answer(
        f"Интерес '{name}' добавлен.",
        reply_markup=admin_menu_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data.startswith("admin:intremove:"))
async def admin_remove_interest(callback: types.CallbackQuery, state: FSMContext) -> None:
    _, _, key, name = callback.data.split(":", 3)
    await remove_interest(key, name)
    await add_admin_log(
        callback.from_user.id,
        "remove_interest",
        details=f"{key}/{name}",
    )
    await callback.answer("Интерес удалён.")
    await admin_interest_category(callback, state)


@router.callback_query(F.data.startswith("admin:intcatdel:"))
async def admin_remove_category(callback: types.CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 2)[2]
    await remove_category(key)
    await add_admin_log(callback.from_user.id, "remove_category", details=key)
    await callback.answer("Категория удалена.")
    await admin_interests(callback, state)



@router.callback_query(F.data == "admin:logs")
async def admin_logs(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    logs = await get_admin_logs(limit=20)
    if not logs:
        text = "Логи пусты."
    else:
        lines = ["<b>📋 Последние действия админа</b>"]
        for log in logs:
            target = f" → {log['target_id']}" if log["target_id"] else ""
            lines.append(
                f"{log['created_at']}: {log['action']}{target} {log['details'] or ''}"
            )
        text = "\n".join(lines)
    if callback.message is not None:
        await callback.message.edit_text(
            text,
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:fakes")
async def admin_fakes_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    fake_users = await get_fake_users(limit=100)
    text = (
        f"<b>🎭 Фейковые анкеты</b>\n\n"
        f"Количество: {len(fake_users)}\n\n"
        f"Фейки нужны, чтобы лента не была пустой, пока в боте мало реальных пользователей."
    )
    if callback.message is not None:
        await callback.message.edit_text(
            text,
            reply_markup=admin_fakes_keyboard(len(fake_users)),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:fakes:reset")
async def admin_fakes_reset(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    count = await delete_fake_users()
    await add_admin_log(
        callback.from_user.id,
        "reset_fake_users",
        details=f"removed={count}",
    )
    await callback.answer(f"Удалено фейков: {count}")
    await admin_fakes_menu(callback, state)


@router.callback_query(F.data == "admin:fakes:add")
async def admin_fake_add_start(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text(
            "Введи имя для фейковой анкеты:",
            reply_markup=admin_back_menu_keyboard(),
        )
    await state.set_state(AdminMenu.fake_name)
    await callback.answer()


@router.message(AdminMenu.fake_name)
async def admin_fake_name(message: types.Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Имя не может быть пустым.")
        return
    await state.update_data(fake_name=name)
    await message.answer(
        "Введи возраст (число от 16 до 100):",
        reply_markup=admin_back_menu_keyboard(),
    )
    await state.set_state(AdminMenu.fake_age)


@router.message(AdminMenu.fake_age)
async def admin_fake_age(message: types.Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Нужно ввести число.")
        return
    age = int(text)
    if not (16 <= age <= 100):
        await message.answer("Возраст должен быть от 16 до 100.")
        return
    await state.update_data(fake_age=age)
    await message.answer(
        "Выбери пол:",
        reply_markup=fake_options_keyboard(GENDER_OPTIONS, "gender"),
    )
    await state.set_state(AdminMenu.fake_gender)


@router.callback_query(F.data.startswith("fakeopt:gender:"))
async def admin_fake_gender(callback: types.CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 2)[2]
    await state.update_data(fake_gender=value)
    if callback.message is not None:
        await callback.message.edit_text(
            "Кого ищет фейк?",
            reply_markup=fake_options_keyboard(LOOKING_FOR_OPTIONS, "looking_for"),
        )
    await state.set_state(AdminMenu.fake_looking_for)
    await callback.answer()


@router.callback_query(F.data.startswith("fakeopt:looking_for:"))
async def admin_fake_looking_for(callback: types.CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 2)[2]
    await state.update_data(fake_looking_for=value)
    if callback.message is not None:
        await callback.message.edit_text(
            "Выбери цель знакомства:",
            reply_markup=fake_options_keyboard(GOAL_OPTIONS, "goal"),
        )
    await state.set_state(AdminMenu.fake_goal)
    await callback.answer()


@router.callback_query(F.data.startswith("fakeopt:goal:"))
async def admin_fake_goal(callback: types.CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 2)[2]
    await state.update_data(fake_goal=value)
    if callback.message is not None:
        await callback.message.edit_text(
            "Введи город (или отправь '-' без кавычек, чтобы пропустить):",
            reply_markup=admin_back_menu_keyboard(),
        )
    await state.set_state(AdminMenu.fake_city)
    await callback.answer()


@router.message(AdminMenu.fake_city)
async def admin_fake_city(message: types.Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if city == "-":
        city = ""
    await state.update_data(fake_city=city or None)
    await message.answer(
        "Введи увлечения через запятую:",
        reply_markup=admin_back_menu_keyboard(),
    )
    await state.set_state(AdminMenu.fake_interests)


@router.message(AdminMenu.fake_interests)
async def admin_fake_interests(message: types.Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    interests = [i.strip() for i in text.split(",") if i.strip()]
    if not interests:
        await message.answer("Нужно ввести хотя бы одно увлечение.")
        return
    await state.update_data(fake_interests=interests)
    await message.answer(
        "Отправь фото для анкеты или нажми 'Пропустить фото':",
        reply_markup=fake_photo_keyboard(),
    )
    await state.set_state(AdminMenu.fake_photo)


@router.message(AdminMenu.fake_photo)
async def admin_fake_photo(message: types.Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Отправь фото или нажми кнопку пропуска.")
        return
    file_id = message.photo[-1].file_id
    await state.update_data(fake_photo_file_id=file_id)
    await _send_fake_preview(message, state)


@router.callback_query(F.data == "fakeopt:photo:skip")
async def admin_fake_photo_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.update_data(fake_photo_file_id=None)
    if callback.message is not None:
        await callback.message.edit_text("Фото пропущено.")
    await _send_fake_preview(callback.message, state)
    await callback.answer()


async def _send_fake_preview(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    preview_text = _format_fake_preview(data)
    await message.answer(
        preview_text,
        reply_markup=fake_confirm_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminMenu.fake_confirm)


def _format_fake_preview(data: dict) -> str:
    from services.profile import _label

    lines = [
        "<b>🎭 Предпросмотр фейковой анкеты</b>",
        "",
        f"<b>Имя:</b> {data['fake_name']}",
        f"<b>Возраст:</b> {data['fake_age']}",
        f"<b>Пол:</b> {_label(data['fake_gender'])}",
        f"<b>Ищу:</b> {_label(data['fake_looking_for'])}",
        f"<b>Цель:</b> {_label(data['fake_goal'])}",
        f"<b>Увлечения:</b> {', '.join(data['fake_interests'])}",
    ]
    city = data.get("fake_city")
    if city:
        lines.append(f"<b>📍 Город:</b> {city}")
    photo = data.get("fake_photo_file_id")
    lines.append(f"<b>Фото:</b> {'есть' if photo else 'нет'}")
    return "\n".join(lines)


@router.callback_query(F.data == "fakeopt:publish")
async def admin_fake_publish(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    required = ("fake_name", "fake_age", "fake_gender", "fake_looking_for", "fake_goal", "fake_interests")
    if not all(k in data for k in required):
        await callback.answer("Не хватает данных. Начни заново.")
        await admin_fakes_menu(callback, state)
        return

    user_id = await add_fake_user(
        name=data["fake_name"],
        age=data["fake_age"],
        gender=data["fake_gender"],
        looking_for=data["fake_looking_for"],
        goal=data["fake_goal"],
        interests=data["fake_interests"],
        city=data.get("fake_city"),
        photo_file_id=data.get("fake_photo_file_id"),
    )
    await add_admin_log(
        callback.from_user.id,
        "add_fake_user",
        target_id=user_id,
        details=data["fake_name"],
    )
    await state.clear()
    await callback.answer("Фейковая анкета опубликована.")
    await admin_fakes_menu(callback, state)
