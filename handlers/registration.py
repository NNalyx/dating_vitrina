# handlers/registration.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import MIN_AGE
from database import add_user
from keyboards import build_interests_keyboard, skip_photo_keyboard
from states import Registration

router = Router()


@router.callback_query(F.data == "policy_agree", Registration.policy)
async def process_policy(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User agreed to the privacy policy."""
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

    await state.update_data(age=age)
    await message.answer("Как тебя зовут? Можешь указать имя или ник.")
    await state.set_state(Registration.name)


@router.message(Registration.name)
async def process_name(message: types.Message, state: FSMContext) -> None:
    """Save the user's display name and move to interest selection."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи хотя бы 2 символа.")
        return

    await state.update_data(name=name)
    await message.answer(
        "Выбери свои увлечения. Нужно выбрать минимум 3. Нажми «Готово», когда закончишь.",
        reply_markup=build_interests_keyboard(set()),
    )
    await state.set_state(Registration.interests)


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

    await state.update_data(interests=selected)
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

    await callback.message.edit_text(
        "Отправь свою фотографию. Это повысит количество лайков. "
        "Если не хочешь — нажми «Пропустить».",
        reply_markup=skip_photo_keyboard(),
    )
    await state.set_state(Registration.photo)
    await callback.answer()


@router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext) -> None:
    """Save the largest photo variant and finish registration."""
    photo_id = message.photo[-1].file_id
    await _save_profile(message, state, photo_id)


@router.callback_query(F.data == "photo_skip", Registration.photo)
async def skip_photo(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip the photo step with a warning, then finish registration."""
    await callback.message.edit_text(
        "Фото не добавлено. Пользователи без фото обычно получают меньше лайков."
    )
    await _save_profile(callback.message, state, photo_id=None)
    await callback.answer()


async def _save_profile(
    message: types.Message, state: FSMContext, photo_id: str | None
) -> None:
    """Persist the user and clear the registration state."""
    data = await state.get_data()
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        age=data["age"],
        name=data["name"],
        interests=sorted(data["interests"]),
        photo_file_id=photo_id,
    )
    await message.answer(
        "🎉 Регистрация завершена! Теперь ты можешь использовать /search для поиска анкет."
    )
    await state.clear()
