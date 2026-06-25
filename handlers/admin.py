from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    add_admin_log,
    ban_user,
    delete_user,
    get_user,
    get_user_by_username,
    unban_user,
)
from keyboards import admin_back_menu_keyboard, admin_menu_keyboard
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
