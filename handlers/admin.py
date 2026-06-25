import json
import os
import tempfile

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    add_admin_log,
    add_interest,
    ban_user,
    delete_user,
    get_admin_stats,
    get_all_users,
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
    admin_interest_category_keyboard,
    admin_interests_keyboard,
    admin_menu_keyboard,
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



async def _refresh_user_profile(callback: types.CallbackQuery, user_id: int) -> None:
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
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:users")],
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
