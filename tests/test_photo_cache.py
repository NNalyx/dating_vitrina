import hashlib
import os
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
async def client(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("database.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("config.PHOTOS_DIR", str(tmp_path / "photos"))
    monkeypatch.setattr("web_routes.PHOTOS_DIR", str(tmp_path / "photos"))
    from database import init_db

    await init_db()
    from web_app import create_app
    from aiogram import Bot

    bot = AsyncMock(spec=Bot)
    app = create_app(bot)
    return await aiohttp_client(app), bot


async def test_photo_cached_on_first_request(client, tmp_path):
    client, bot = client
    file_id = "AgACAgIAAxkBAAExample"
    cache_path = os.path.join(str(tmp_path / "photos"), hashlib.sha256(file_id.encode()).hexdigest() + ".jpg")

    # Ensure the bot returns some bytes.
    bot.get_file.return_value = AsyncMock(file_path="photos/file.jpg")

    async def fake_download(file, destination):
        destination.write(b"fake-image-data")

    bot.download.side_effect = fake_download

    resp = await client.get(f"/api/photo/{file_id}")
    assert resp.status == 200
    assert await resp.read() == b"fake-image-data"
    assert os.path.exists(cache_path)
    bot.download.assert_awaited_once()

    # Second request should not call bot.download again.
    bot.download.reset_mock()
    resp2 = await client.get(f"/api/photo/{file_id}")
    assert resp2.status == 200
    assert await resp2.read() == b"fake-image-data"
    bot.download.assert_not_awaited()
