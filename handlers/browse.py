# handlers/browse.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from database import (
    add_like,
    add_view,
    get_all_users,
    get_user,
    get_viewed_ids,
    has_like,
)
from handlers.menu import show_main_menu
from keyboards import browse_keyboard, write_link_keyboard
from services.matching import filter_candidates, score_candidates
from services.profile import format_browse_card, format_profile

router = Router()


async def _show_next_profile(message: types.Message, state: FSMContext) -> None:
    """Show the next candidate from the feed."""
    if message.from_user is None:
        return

    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала пройди регистрацию: /start")
        return

    candidates = await get_all_users()
    viewed_ids = await get_viewed_ids(message.from_user.id)
    filtered = filter_candidates(user, candidates, viewed_ids)
    scored = score_candidates(user, filtered)

    if not scored:
        await message.answer(
            "Пока нет подходящих анкет. Попробуй позже.",
            reply_markup=browse_keyboard(),
        )
        await state.clear()
        return

    candidate, compatibility = scored[0]
    await state.update_data(
        current_candidate_id=candidate["user_id"],
        current_compatibility=compatibility,
    )

    text = format_browse_card(candidate, compatibility)
    photo_id = candidate.get("photo_file_id")

    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=browse_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=browse_keyboard(),
            parse_mode="HTML",
        )


@router.message(F.text == "🔍 Смотреть анкеты")
async def start_browse(message: types.Message, state: FSMContext) -> None:
    """Start browsing profiles."""
    await state.clear()
    await _show_next_profile(message, state)


@router.callback_query(F.data == "browse:skip")
async def browse_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip current profile and show the next one."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    data = await state.get_data()
    candidate_id = data.get("current_candidate_id")
    if candidate_id:
        await add_view(callback.from_user.id, candidate_id)

    await callback.message.delete()
    await _show_next_profile(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "browse:like")
async def browse_like(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Like current profile and handle mutual match."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    data = await state.get_data()
    candidate_id = data.get("current_candidate_id")
    if candidate_id is None:
        await callback.answer("Ошибка: анкета не выбрана.", show_alert=True)
        return

    await add_view(callback.from_user.id, candidate_id)
    await add_like(callback.from_user.id, candidate_id)

    is_mutual = await has_like(candidate_id, callback.from_user.id)
    if is_mutual:
        await _notify_mutual_match(
            callback.message,
            liker_id=callback.from_user.id,
            liked_id=candidate_id,
        )
    else:
        await callback.answer("Лайк отправлен! ❤️")

    await callback.message.delete()
    await _show_next_profile(callback.message, state)


async def _notify_mutual_match(
    message: types.Message, liker_id: int, liked_id: int
) -> None:
    """Send mutual match notifications to both users."""
    liker = await get_user(liker_id)
    liked = await get_user(liked_id)
    if not liker or not liked:
        return

    liker_text = (
        "<b>💞 Взаимный лайк!</b>\n\n"
        + format_profile(liked, title="📋 Анкета")
    )
    liked_text = (
        "<b>💞 Взаимный лайк!</b>\n\n"
        + format_profile(liker, title="📋 Анкета")
    )

    await message.bot.send_message(
        chat_id=liker_id,
        text=liker_text,
        reply_markup=write_link_keyboard(liked.get("username"), liked_id),
        parse_mode="HTML",
    )
    await message.bot.send_message(
        chat_id=liked_id,
        text=liked_text,
        reply_markup=write_link_keyboard(liker.get("username"), liker_id),
        parse_mode="HTML",
    )
