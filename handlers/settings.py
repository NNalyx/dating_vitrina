# handlers/settings.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MAX_AGE, MIN_AGE
from database import (
    get_notifications_enabled,
    set_notifications_enabled,
    get_user_filters,
    update_user_filters,
)
from keyboards import filters_keyboard, settings_keyboard

router = Router()


def _clamp_age(value: int) -> int:
    return max(MIN_AGE, min(MAX_AGE, value))


@router.callback_query(F.data == "menu:settings")
async def open_settings(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Show the settings screen."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    await state.clear()
    await callback.message.delete()

    enabled = await get_notifications_enabled(callback.from_user.id)
    status = "включены" if enabled else "выключены"
    text = (
        "<b>⚙️ Настройки</b>\n\n"
        f"Уведомления о новых лайках: {status}\n\n"
        "Нажми кнопку ниже, чтобы переключить."
    )
    await callback.message.answer(
        text,
        reply_markup=settings_keyboard(enabled),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "settings:toggle")
async def toggle_notifications(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle incoming-like notifications."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    enabled = await get_notifications_enabled(callback.from_user.id)
    enabled = not enabled
    await set_notifications_enabled(callback.from_user.id, enabled)

    status = "включены" if enabled else "выключены"
    text = (
        "<b>⚙️ Настройки</b>\n\n"
        f"Уведомления о новых лайках: {status}\n\n"
        "Нажми кнопку ниже, чтобы переключить."
    )
    await callback.message.edit_text(
        text,
        reply_markup=settings_keyboard(enabled),
        parse_mode="HTML",
    )
    await callback.answer("Настройки обновлены.")


@router.callback_query(F.data == "settings:filters")
async def open_filters(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Open the feed filters screen."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    await state.clear()
    filters = await get_user_filters(callback.from_user.id)
    text = (
        "<b>🔍 Фильтры ленты</b>\n\n"
        f"Возраст: от {filters['min_age']} до {filters['max_age']}\n"
        f"Город: {'только мой' if filters['only_my_city'] else 'любой'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=filters_keyboard(
            filters["min_age"], filters["max_age"], filters["only_my_city"]
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter:"))
async def adjust_filter(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Handle filter adjustment buttons."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    user_id = callback.from_user.id
    filters = await get_user_filters(user_id)
    min_age = filters["min_age"]
    max_age = filters["max_age"]
    only_my_city = filters["only_my_city"]

    action = callback.data.split(":", 1)[1]

    if action == "toggle_city":
        only_my_city = not only_my_city
    elif action == "reset":
        min_age = MIN_AGE
        max_age = MAX_AGE
        only_my_city = False
    elif action.startswith("min_age:"):
        delta = 1 if action.endswith("+1") else -1
        min_age = _clamp_age(min_age + delta)
        if min_age > max_age:
            max_age = min_age
    elif action.startswith("max_age:"):
        delta = 1 if action.endswith("+1") else -1
        max_age = _clamp_age(max_age + delta)
        if max_age < min_age:
            min_age = max_age

    await update_user_filters(
        user_id,
        min_age=min_age,
        max_age=max_age,
        only_my_city=only_my_city,
    )

    text = (
        "<b>🔍 Фильтры ленты</b>\n\n"
        f"Возраст: от {min_age} до {max_age}\n"
        f"Город: {'только мой' if only_my_city else 'любой'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=filters_keyboard(min_age, max_age, only_my_city),
        parse_mode="HTML",
    )
    await callback.answer("Фильтры обновлены.")
