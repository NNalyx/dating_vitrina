import re

import pytest

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
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    from database import init_db

    await init_db()
    from web_app import create_app

    app = create_app()
    return await aiohttp_client(app)


async def _register(client, user_id: int, gender: str, looking_for: str, city: str):
    captcha = await (await client.get("/api/captcha")).json()
    init_data = _make_init_data(user_id, "test_token_12345")
    payload = {
        "initData": init_data,
        "age": 22,
        "name": "Test",
        "gender": gender,
        "looking_for": looking_for,
        "goal": "relationship",
        "interests": ["Аниме", "Dota 2", "Музыка"],
        "city": city,
        "photo_file_id": None,
        "captcha_token": captcha["token"],
        "captcha_answer": _solve_captcha(captcha["question"]),
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 201, await resp.json()


async def test_feed_returns_fake_when_no_real_candidates(client, monkeypatch):
    monkeypatch.setattr(
        "services.fake_profile_generator.pick_avatar_file_id",
        lambda _gender: None,
    )
    await _register(client, 100, "female", "male", "Москва")

    init_data = _make_init_data(100, "test_token_12345")
    resp = await client.get("/api/feed", headers={"X-Init-Data": init_data})
    assert resp.status == 200, await resp.json()
    data = await resp.json()
    assert data["is_fake"] == 1
    assert data["user_id"] < 0
    assert data["gender"] == "male"
    assert data["looking_for"] == "female"
    assert data["city"] == "Москва"
