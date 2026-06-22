# handlers/registration.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MAX_AGE, MIN_AGE
from database import add_user
from handlers.menu import show_main_menu
from keyboards import (
    build_interests_keyboard,
    gender_keyboard,
    goal_keyboard,
    looking_for_keyboard,
    skip_photo_keyboard,
)
from services.city_validation import is_valid_city, normalize_city
from services.moderation import is_clean_city, is_clean_name
from states import Registration

router = Router()


@router.callback_query(F.data == "policy_agree", Registration.policy)
async def process_policy(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User agreed to the privacy policy."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text("Отлично! Сколько тебе лет?")
    await state.set_state(Registration.age)
    await callback.answer()


@router.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext) -> None:
    """Validate age and move to the name step."""
    if not message.text or not message.text.isdigit():
        await message.answer("Пожалуйста, введи возраст числом.")
        return

    age = int(message.text)
    if age < MIN_AGE:
        await message.answer(
            f"Извини, но этот бот только для пользователей {MIN_AGE}+ лет."
        )
        return
    if age > MAX_AGE:
        await message.answer(
            f"Возраст не может быть больше {MAX_AGE} лет. Проверь, пожалуйста, ввод."
        )
        return

    await state.update_data(age=age)
    await message.answer("Как тебя зовут? Можешь указать имя или ник.")
    await state.set_state(Registration.name)


@router.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext) -> None:
    """Save the user's display name and move to gender selection."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи хотя бы 2 символа.")
        return

    if not is_clean_name(name):
        await message.answer("⚠️ Имя содержит недопустимые слова. Введи другое имя.")
        return

    await state.update_data(name=name)
    await message.answer(
        "Укажи свой пол:",
        reply_markup=gender_keyboard(),
    )
    await state.set_state(Registration.gender)


@router.callback_query(F.data.startswith("gender:"), Registration.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save gender and ask who the user is looking for."""
    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text("Кого ты ищешь?", reply_markup=looking_for_keyboard())
    await state.set_state(Registration.looking_for)
    await callback.answer()


@router.callback_query(F.data.startswith("looking_for:"), Registration.looking_for)
async def process_looking_for(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save looking_for preference and ask for the dating goal."""
    looking_for = callback.data.split(":", 1)[1]
    await state.update_data(looking_for=looking_for)
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text(
        "Что ты ищешь?", reply_markup=goal_keyboard()
    )
    await state.set_state(Registration.goal)
    await callback.answer()


@router.callback_query(F.data.startswith("goal:"), Registration.goal)
async def process_goal(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Save goal and move to interest selection."""
    goal = callback.data.split(":", 1)[1]
    await state.update_data(goal=goal)
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text(
        "Выбери свои увлечения. Нужно выбрать минимум 3. Нажми «Готово», когда закончишь.",
        reply_markup=build_interests_keyboard(set()),
    )
    await state.set_state(Registration.interests)
    await callback.answer()


@router.callback_query(F.data.startswith("interest:"), Registration.interests)
async def toggle_interest(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Toggle an interest selection and update the keyboard in place."""
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


@router.callback_query(F.data == "interest_done", Registration.interests)
async def finish_interests(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Validate minimum interest count and move to the photo step."""
    data = await state.get_data()
    selected = data.get("interests", [])

    if len(selected) < 3:
        await callback.answer(
            "Выбери минимум 3 увлечения, чтобы продолжить.", show_alert=True
        )
        return

    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.edit_text(
        "🏙️ Введи свой город (Россия):"
    )
    await state.set_state(Registration.city)
    await callback.answer()


@router.message(Registration.city)
async def process_city(message: types.Message, state: FSMContext) -> None:
    """Validate city and move to the photo step."""
    raw = message.text.strip() if message.text else ""
    if not is_valid_city(raw):
        await message.answer(
            "⚠️ Название города не похоже на настоящее. "
            "Введи город ещё раз (только буквы)."
        )
        return

    normalized = normalize_city(raw)
    if not is_clean_city(normalized):
        await message.answer(
            "⚠️ Название города содержит недопустимые слова. Введи город ещё раз."
        )
        return

    await state.update_data(city=normalized)
    await message.answer(
        "Отправь свою фотографию. Это повысит количество лайков. "
        "Если не хочешь — нажми «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )
    await state.set_state(Registration.photo)


@router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext) -> None:
    """Save the largest photo variant and finish registration."""
    photo_id = message.photo[-1].file_id
    await _save_profile(
        message,
        state,
        user_id=message.from_user.id,
        username=message.from_user.username,
        photo_id=photo_id,
    )


@router.callback_query(F.data == "photo_skip", Registration.photo)
async def skip_photo(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip the photo step with a warning, then finish registration."""
    if callback.message is None or callback.from_user is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return

    await callback.message.edit_text(
        "Фото не добавлено. Пользователи без фото обычно получают меньше лайков."
    )
    await _save_profile(
        callback.message,
        state,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        photo_id=None,
    )
    await callback.answer()


@router.message(Registration.photo)
async def wrong_photo_input(message: types.Message) -> None:
    """Handle any non-photo input during the photo step."""
    await message.answer(
        "Пожалуйста, отправь фотографию или нажми кнопку «Пропустить»."
    )


async def _save_profile(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    username: str | None,
    photo_id: str | None,
) -> None:
    """Persist the user and show the main menu."""
    data = await state.get_data()
    required_fields = ("age", "name", "gender", "looking_for", "goal", "interests", "city")
    missing = [field for field in required_fields if field not in data]
    if missing:
        await message.answer(
            "Что-то пошло не так с регистрацией. Попробуй начать сначала с /start."
        )
        await state.clear()
        return

    try:
        await add_user(
            user_id=user_id,
            username=username,
            age=data["age"],
            name=data["name"],
            gender=data["gender"],
            looking_for=data["looking_for"],
            goal=data["goal"],
            interests=sorted(data["interests"]),
            photo_file_id=photo_id,
            city=data["city"],
        )
    except Exception:
        await message.answer(
            "Не удалось сохранить анкету. Попробуй ещё раз позже."
        )
        return

    await message.answer("🎉 Регистрация завершена!")
    await show_main_menu(message, state)
