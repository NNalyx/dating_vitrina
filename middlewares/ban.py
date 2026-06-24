from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import OWNER_ID
from database import is_banned


class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user is not None:
            user_id = event.from_user.id

        if user_id and user_id != OWNER_ID and await is_banned(user_id):
            if isinstance(event, CallbackQuery):
                await event.answer("Аккаунт заблокирован.", show_alert=True)
            else:
                await event.answer("Аккаунт заблокирован.")
            return None

        return await handler(event, data)
