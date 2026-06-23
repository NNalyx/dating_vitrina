# handlers/likes.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from database import add_like, get_all_users, get_user, has_like
from handlers.browse import _notify_mutual_match
from keyboards import like_response_keyboard
from services.profile import format_profile
from services.ui import send_mini_app_button

router = Router()


@router.message(F.text == "❤️ Мои лайки")
async def show_likes(message: types.Message, state: FSMContext) -> None:
    """Show the most recent incoming like."""
    await _present_likes(message, state)


@router.callback_query(F.data == "menu:likes")
async def callback_show_likes(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Open the likes screen from the inline main menu."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.delete()
    await _present_likes(callback.message, state)
    await callback.answer()


async def _present_likes(message: types.Message, state: FSMContext) -> None:
    """Fetch and display the most recent unreciprocated incoming like."""
    await state.clear()

    user_id = message.chat.id
    user = await get_user(user_id)
    if user is None:
        await message.answer("Сначала пройди регистрацию: /start")
        return

    liker_id = None
    for candidate in await get_all_users():
        cid = candidate["user_id"]
        if cid == user_id:
            continue
        if await has_like(cid, user_id):
            if not await has_like(user_id, cid):
                liker_id = cid
                break

    if liker_id is None:
        await message.answer("У тебя пока нет новых лайков.")
        return

    liker = await get_user(liker_id)
    if liker is None:
        await message.answer("Анкета лайкнувшего не найдена.")
        return

    text = "<b>💌 Тебя лайкнули!</b>\n\n" + format_profile(liker, title="📋 Анкета")
    photo_id = liker.get("photo_file_id")
    if photo_id:
        await message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=like_response_keyboard(liker_id),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=like_response_keyboard(liker_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("like_back:"))
async def like_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Reciprocate a like."""
    if callback.from_user is None or callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    liker_id = int(callback.data.split(":", 1)[1])
    await add_like(callback.from_user.id, liker_id)
    await _notify_mutual_match(
        callback.message,
        liker_id=callback.from_user.id,
        liked_id=liker_id,
    )
    await callback.message.delete()
    await send_mini_app_button(
        callback.message,
        "Отлично! Продолжай знакомиться в приложении.",
        state=state,
    )


@router.callback_query(F.data.startswith("like_skip:"))
async def like_skip(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Skip an incoming like."""
    if callback.message is None:
        await callback.answer("Ошибка.", show_alert=True)
        return

    await callback.message.delete()
    await send_mini_app_button(
        callback.message,
        "Пропущено. Заходи в приложение, чтобы найти кого-то ещё.",
        state=state,
    )
    await callback.answer()
