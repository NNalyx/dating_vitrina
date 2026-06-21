# znakomstvabot.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import browse, common, likes, menu, profile, registration


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_routers(
        common.router,
        registration.router,
        menu.router,
        profile.router,
        browse.router,
        likes.router,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
