# services/ui.py

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards import mini_app_button_keyboard


async def send_mini_app_button(
    message: Message,
    text: str,
    state: FSMContext | None = None,
) -> None:
    """Send a message with the Mini App open button.

    If the tunnel URL is not available yet, sends a plain text fallback.
    """
    if state is not None:
        await state.clear()

    keyboard = mini_app_button_keyboard()
    if keyboard is None:
        await message.answer(text + "\n\nПриложение скоро будет доступно.")
        return

    await message.answer(text, reply_markup=keyboard)
