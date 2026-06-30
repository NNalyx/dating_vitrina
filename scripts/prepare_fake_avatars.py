import asyncio
import json
from pathlib import Path

import aiohttp
from aiogram import Bot

from config import BOT_TOKEN, OWNER_ID

AVATARS_DIR = Path("data/fake_avatars/neutral")
FILE_IDS_PATH = Path("data/fake_avatars/file_ids.json")
COUNT = 30


async def download_image(session: aiohttp.ClientSession, dest: Path) -> None:
    # Append a unique query param to bypass image/CDN caching.
    url = f"https://thispersondoesnotexist.com/?{asyncio.get_event_loop().time()}"
    async with session.get(url) as resp:
        resp.raise_for_status()
        dest.write_bytes(await resp.read())


async def upload_and_record(bot: Bot, path: Path, gender: str, records: list[dict]) -> None:
    with open(path, "rb") as f:
        msg = await bot.send_photo(chat_id=OWNER_ID, photo=f, disable_notification=True)
    file_id = msg.photo[-1].file_id
    records.append({"path": str(path), "gender": gender, "file_id": file_id})
    await asyncio.sleep(0.5)


async def main() -> None:
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    bot = Bot(token=BOT_TOKEN)
    records = []
    if FILE_IDS_PATH.exists():
        records = json.loads(FILE_IDS_PATH.read_text(encoding="utf-8"))
    existing_paths = {r["path"] for r in records}

    async with aiohttp.ClientSession() as session:
        for i in range(COUNT):
            dest = AVATARS_DIR / f"{i + 1:03d}.jpg"
            if str(dest) in existing_paths:
                continue
            await download_image(session, dest)
            await upload_and_record(bot, dest, "neutral", records)
            print(f"Uploaded {dest} -> {records[-1]['file_id']}")

    FILE_IDS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
