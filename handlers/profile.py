# handlers/profile.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MAX_AGE, MIN_AGE
from database import get_user, update_user
from keyboards import (
    build_interests_keyboard,
    goal_keyboard,
    looking_for_keyboard,
    profile_edit_keyboard,
)
from services.profile import format_profile
from services.ui import send_mini_app_button
from states import EditProfile

router = Router()


@router.message(F.text == "📋 Моя анкета")
async def show_my_profile(message: types.Message, state: FSMContext) -> None:
    """Show the user's own profile with edit options."""
    await _present_profile(message, state)


@router.callback_query(F.data == "menu:profile")
async def callback_show_profile(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Open the user's profile from the inline main menu."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.delete()
    await _present_profile(callback.message, state)
    await callback.answer()


async def _present_profile(message: types.Message, state: FSMContext) -> None:
    """Fetch and display the user's profile card."""
    await state.clear()

    user = await get_user(message.chat.id)
    if user is None:
        await message.answer("Анкета не найдена. Начни регистрацию с /start.")
        return

    text = format_profile(user, title="📋 Твоя анкета")
    await message.answer(
        text,
        reply_markup=profile_edit_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("edit:"))
async def start_edit(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Start editing a specific profile field."""
    if callback.message is None or callback.from_user is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    field = callback.data.split(":", 1)[1]

    if field == "age":
        await callback.message.edit_text("Введи новый возраст:")
        await state.set_state(EditProfile.age)
    elif field == "name":
        await callback.message.edit_text("Введи новое имя:")
        await state.set_state(EditProfile.name)
    elif field == "looking_for":
        await callback.message.edit_text(
            "Кого ты ищешь?", reply_markup=looking_for_keyboard()
        )
        await state.set_state(EditProfile.looking_for)
    elif field == "goal":
        await callback.message.edit_text("Что ты ищешь?", reply_markup=goal_keyboard())
        await state.set_state(EditProfile.goal)
    elif field == "interests":
        user = await get_user(callback.from_user.id)
        selected = set()
        if user and user.get("interests"):
            selected = {i.strip() for i in user["interests"].split(",") if i.strip()}
        await state.update_data(interests=list(selected))
        await callback.message.edit_text(
            "Выбери новые увлечения (минимум 3):",
            reply_markup=build_interests_keyboard(selected),
        )
        await state.set_state(EditProfile.interests)
    elif field == "photo":
        await callback.message.edit_text("Отправь новое фото:")
        await state.set_state(EditProfile.photo)
    else:
        await callback.answer("Неизвестное поле.", show_alert=True)
        return

    await callback.answer()


@router.message(EditProfile.age)
async def edit_age(message: types.Message, state: FSMContext) -> None:
    """Validate and save new age."""
    if not message.text or not message.text.isdigit():
        await message.answer("Введи возраст числом.")
        return
    age = int(message.text)
    if age < MIN_AGE:
        await message.answer(f"Минимальный возраст — {MIN_AGE} лет.")
        return
    if age > MAX_AGE:
        await message.answer(f"Максимальный возраст — {MAX_AGE} лет.")
        return

    await update_user(message.chat.id, age=age)
    await message.answer("Возраст обновлён.")
    await send_mini_app_button(message, "Готово!", state=state)


@router.message(EditProfile.name)
async def edit_name(message: types.Message, state: FSMContext) -> None:
    """Save new name."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое.")
        return

    await update_user(message.chat.id, name=name)
    await message.answer("Имя обновлено.")
    await send_mini_app_button(message, "Готово!", state=state)


@router.callback_query(F.data.startswith("looking_for:"), EditProfile.looking_for)
async def edit_looking_for(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save new looking_for preference."""
    if callback.from_user is None:
        await callback.answer("Ошибка: пользователь не определён.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    await update_user(callback.from_user.id, looking_for=value)
    await callback.answer("Кого ищешь — обновлено.")
    await send_mini_app_button(callback.message, "Готово!", state=state)


@router.callback_query(F.data.startswith("goal:"), EditProfile.goal)
async def edit_goal(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save new goal."""
    if callback.from_user is None:
        await callback.answer("Ошибка: пользователь не определён.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    await update_user(callback.from_user.id, goal=value)
    await callback.answer("Цель обновлена.")
    await send_mini_app_button(callback.message, "Готово!", state=state)


@router.callback_query(F.data.startswith("interest:"), EditProfile.interests)
async def edit_toggle_interest(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle interest selection while editing."""
    item = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("interests", []))

    if item in selected:
        selected.remove(item)
    else:
        selected.add(item)

    await state.update_data(interests=list(selected))
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_reply_markup(
        reply_markup=build_interests_keyboard(selected)
    )
    await callback.answer()


@router.callback_query(F.data == "interest_done", EditProfile.interests)
async def edit_finish_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Validate and save edited interests."""
    data = await state.get_data()
    selected = data.get("interests", [])
    if len(selected) < 3:
        await callback.answer("Выбери минимум 3 увлечения.", show_alert=True)
        return

    if callback.from_user is None:
        await callback.answer("Ошибка: пользователь не определён.", show_alert=True)
        return
    await update_user(callback.from_user.id, interests=selected)
    await callback.answer("Интересы обновлены.")
    await send_mini_app_button(callback.message, "Готово!", state=state)


@router.message(EditProfile.photo, F.photo)
async def edit_photo(message: types.Message, state: FSMContext) -> None:
    """Save new photo."""
    photo_id = message.photo[-1].file_id
    await update_user(message.chat.id, photo_file_id=photo_id)
    await message.answer("Фото обновлено.")
    await send_mini_app_button(message, "Готово!", state=state)


@router.message(EditProfile.photo)
async def edit_photo_wrong(message: types.Message) -> None:
    """Handle non-photo input while editing photo."""
    await message.answer("Пожалуйста, отправь фотографию.")
