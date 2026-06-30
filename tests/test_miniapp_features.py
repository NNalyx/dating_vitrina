import re

import aiohttp
import pytest
from unittest.mock import AsyncMock

from tests.test_web_auth import _make_init_data


def _solve_captcha(question: str) -> str:
    match = re.match(r"(\d+)\s*([+\-])\s*(\d+)", question)
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    return str(a + b if op == "+" else a - b)


@pytest.fixture
async def client(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("database.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("config.BOT_TOKEN", "test_token_12345")
    monkeypatch.setattr("web_routes.BOT_TOKEN", "test_token_12345")
    from database import init_db

    await init_db()
    from web_app import create_app

    app = create_app()
    return await aiohttp_client(app)


@pytest.fixture
async def client_with_bot(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("database.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("config.BOT_TOKEN", "test_token_12345")
    monkeypatch.setattr("web_routes.BOT_TOKEN", "test_token_12345")
    from database import init_db

    await init_db()
    from web_app import create_app
    from aiogram import Bot

    bot = AsyncMock(spec=Bot)
    app = create_app(bot)
    return await aiohttp_client(app), bot


async def _register(client, monkeypatch, user_id, payload):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    captcha_resp = await client.get("/api/captcha")
    assert captcha_resp.status == 200
    captcha = await captcha_resp.json()
    init_data = _make_init_data(user_id, "test_token_12345")
    data = {
        "initData": init_data,
        "captcha_token": captcha["token"],
        "captcha_answer": _solve_captcha(captcha["question"]),
        **payload,
    }
    resp = await client.post("/api/register", json=data)
    assert resp.status == 201, await resp.json()


async def _header(user_id):
    init_data = _make_init_data(user_id, "test_token_12345")
    return {"X-Init-Data": init_data}


async def test_validate_city_valid(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    headers = await _header(123)
    resp = await client.post("/api/validate-city", json={"city": "  москва  "}, headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["valid"] is True
    assert data["normalized"] == "Москва"


async def test_validate_city_invalid(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    headers = await _header(123)
    resp = await client.post("/api/validate-city", json={"city": "123"}, headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["valid"] is False


async def test_feed_returns_fake_when_alone(client, monkeypatch):
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    headers = await _header(1)
    resp = await client.get("/api/feed", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data.get("is_fake") == 1


async def test_feed_returns_candidate(client, monkeypatch):
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await _register(
        client,
        monkeypatch,
        2,
        {
            "age": 26,
            "name": "Пётр",
            "gender": "male",
            "looking_for": "female",
            "goal": "relationship",
            "interests": ["Музыка", "Кино", "Игры"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    headers = await _header(1)
    resp = await client.get("/api/feed", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["user_id"] == 2
    assert "compatibility" in data


async def test_like_records_like(client, monkeypatch):
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await _register(
        client,
        monkeypatch,
        2,
        {
            "age": 26,
            "name": "Пётр",
            "gender": "male",
            "looking_for": "female",
            "goal": "relationship",
            "interests": ["Музыка", "Кино", "Игры"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    headers = await _header(1)
    resp = await client.post("/api/feed/2/like", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert data["mutual"] is False


async def test_incoming_likes_and_like_back(client, monkeypatch):
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await _register(
        client,
        monkeypatch,
        2,
        {
            "age": 26,
            "name": "Пётр",
            "gender": "male",
            "looking_for": "female",
            "goal": "relationship",
            "interests": ["Музыка", "Кино", "Игры"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await client.post("/api/feed/2/like", headers=await _header(1))
    likes_resp = await client.get("/api/likes", headers=await _header(2))
    likes = await likes_resp.json()
    assert len(likes) == 1
    assert likes[0]["user_id"] == 1

    back_resp = await client.post("/api/likes/1/like_back", headers=await _header(2))
    assert back_resp.status == 200


async def test_update_profile(client, monkeypatch):
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    headers = await _header(1)
    resp = await client.put("/api/me", json={"name": "Анна Мария", "age": 26}, headers=headers)
    assert resp.status == 200

    me_resp = await client.get("/api/me", headers=headers)
    me = await me_resp.json()
    assert me["name"] == "Анна Мария"
    assert me["age"] == 26


async def test_settings_get_and_update(client, monkeypatch):
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    headers = await _header(1)
    get_resp = await client.get("/api/settings", headers=headers)
    settings = await get_resp.json()
    assert settings["min_age"] == 16
    assert settings["notifications_enabled"] is True

    put_resp = await client.put(
        "/api/settings",
        json={
            "min_age": 20,
            "max_age": 30,
            "only_my_city": True,
            "filter_interests": True,
            "notifications_enabled": False,
        },
        headers=headers,
    )
    assert put_resp.status == 200

    get_resp2 = await client.get("/api/settings", headers=headers)
    settings2 = await get_resp2.json()
    assert settings2["min_age"] == 20
    assert settings2["max_age"] == 30
    assert settings2["only_my_city"] is True
    assert settings2["filter_interests"] is True
    assert settings2["notifications_enabled"] is False


async def test_get_interests(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    headers = await _header(123)
    resp = await client.get("/api/interests", headers=headers)
    assert resp.status == 200
    data = await resp.json()
    assert len(data) > 0
    assert all("key" in cat and "label" in cat and "items" in cat for cat in data)
    game_category = next((cat for cat in data if cat["key"] == "games"), None)
    assert game_category is not None
    assert "Valorant" in game_category["items"]
    assert "CS2" in game_category["items"]


async def test_register_sends_welcome_message(client_with_bot, monkeypatch):
    client, bot = client_with_bot
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    monkeypatch.setattr("tunnel.get_tunnel_url", lambda: "https://example.com")
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    bot.send_message.assert_awaited_once()
    call_args = bot.send_message.await_args
    assert "Регистрация успешно пройдена" in call_args.kwargs["text"]


async def test_mutual_like_sends_match_notification(client_with_bot, monkeypatch):
    client, bot = client_with_bot
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await _register(
        client,
        monkeypatch,
        2,
        {
            "age": 26,
            "name": "Пётр",
            "gender": "male",
            "looking_for": "female",
            "goal": "relationship",
            "interests": ["Музыка", "Кино", "Игры"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await client.post("/api/feed/2/like", headers=await _header(1))
    back_resp = await client.post("/api/likes/1/like_back", headers=await _header(2))
    assert back_resp.status == 200
    assert bot.send_message.await_count >= 2
    texts = [call.kwargs.get("text", "") for call in bot.send_message.await_args_list]
    assert any("Взаимный лайк" in text for text in texts)


async def test_reset_views_clears_viewed(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    await _register(
        client,
        monkeypatch,
        2,
        {
            "age": 26,
            "name": "Пётр",
            "gender": "male",
            "looking_for": "female",
            "goal": "relationship",
            "interests": ["Музыка", "Кино", "Игры"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    from database import add_view, get_viewed_ids

    await add_view(1, 2)
    assert await get_viewed_ids(1) == {2}

    resp = await client.post("/api/reset-views", headers=await _header(1))
    assert resp.status == 200
    assert await get_viewed_ids(1) == set()


async def test_upload_photo_rejects_oversized(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    await _register(
        client,
        monkeypatch,
        1,
        {
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        },
    )
    headers = await _header(1)
    data = aiohttp.FormData()
    data.add_field("photo", b"x" * (3 * 1024 * 1024 + 1), content_type="image/jpeg")
    resp = await client.post("/api/upload-photo", headers=headers, data=data)
    assert resp.status == 400
    body = await resp.json()
    assert body["error"] == "File too large"
