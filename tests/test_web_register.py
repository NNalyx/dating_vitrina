import re

import pytest


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


async def _get_captcha(client):
    resp = await client.get("/api/captcha")
    assert resp.status == 200
    return await resp.json()


async def test_register_new_user(client, monkeypatch):
    from tests.test_web_auth import _make_init_data
    from database import get_user

    captcha = await _get_captcha(client)
    init_data = _make_init_data(111, "test_token_12345")
    payload = {
        "initData": init_data,
        "age": 25,
        "name": "Анна",
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": ["Музыка", "Спорт"],
        "city": "Москва",
        "photo_file_id": None,
        "captcha_token": captcha["token"],
        "captcha_answer": _solve_captcha(captcha["question"]),
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 201, await resp.json()
    user = await get_user(111)
    assert user["name"] == "Анна"


async def test_register_profanity_name_returns_400(client, monkeypatch):
    from tests.test_web_auth import _make_init_data

    captcha = await _get_captcha(client)
    init_data = _make_init_data(222, "test_token_12345")
    payload = {
        "initData": init_data,
        "age": 25,
        "name": "блядь",
        "gender": "female",
        "looking_for": "male",
        "goal": "relationship",
        "interests": ["Музыка"],
        "city": "Москва",
        "photo_file_id": None,
        "captcha_token": captcha["token"],
        "captcha_answer": _solve_captcha(captcha["question"]),
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 400
