import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN
from database import init_db
from handlers import admin, browse, common, likes, profile, registration, settings
from middlewares import BanMiddleware
from tunnel import start_tunnel, stop_tunnel
from web_app import create_app


async def start_bot(bot: Bot, dp: Dispatcher):
    await dp.start_polling(bot)


async def start_web(app: web.Application, host: str = "0.0.0.0", port: int = 8080):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info("Web server started on %s:%s", host, port)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    await init_db()

    public_url = await start_tunnel()
    logging.info("Public Mini App URL: %s", public_url)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
    dp.include_routers(
        common.router,
        registration.router,
        profile.router,
        browse.router,
        likes.router,
        settings.router,
        admin.router,
    )

    app = create_app(bot)
    app["public_url"] = public_url

    try:
        await asyncio.gather(
            start_bot(bot, dp),
            start_web(app),
        )
    finally:
        await stop_tunnel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
