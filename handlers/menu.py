# handlers/menu.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from database import get_like_stats
from keyboards import main_menu_keyboard

router = Router()


async def show_main_menu(message: types.Message, state: FSMContext) -> None:
    """Display the main menu with like statistics."""
    await state.clear()

    sent, received = await get_like_stats(message.chat.id)
    text = (
        "<b>Главное меню</b>\n\n"
        f"❤️ Отправлено лайков: {sent}\n"
        f"💌 Получено лайков: {received}"
    )
    # Show the inline menu, then remove any leftover reply keyboard with a
    # transient message that is immediately deleted.
    await message.answer(text, reply_markup=main_menu_keyboard())
    remove_msg = await message.answer("·", reply_markup=ReplyKeyboardRemove())
    try:
        await remove_msg.delete()
    except Exception:
        pass


@router.callback_query(F.data == "menu")
async def callback_menu(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Return to main menu from inline callbacks."""
    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно.", show_alert=True)
        return
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()
