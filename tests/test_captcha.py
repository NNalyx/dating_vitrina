import pytest
import re

from web_routes import _generate_captcha, _make_captcha_token, _verify_captcha_token


def _solve(question: str) -> str:
    match = re.match(r"(\d+)\s*([+\-])\s*(\d+)", question)
    assert match
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    return str(a + b if op == "+" else a - b)


@pytest.fixture
def monkeypatched_token(monkeypatch):
    monkeypatch.setattr("web_routes.BOT_TOKEN", "test_captcha_secret")


def test_generate_captcha(monkeypatched_token):
    question, answer = _generate_captcha()
    assert _solve(question) == answer


def test_captcha_token_verification(monkeypatched_token):
    token = _make_captcha_token("42")
    assert _verify_captcha_token(token, "42") is True
    assert _verify_captcha_token(token, "43") is False
    assert _verify_captcha_token("invalid", "42") is False


@pytest.fixture
async def client(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("database.DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr("config.BOT_TOKEN", "test_captcha_secret")
    monkeypatch.setattr("web_routes.BOT_TOKEN", "test_captcha_secret")
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_captcha_secret")
    from database import init_db

    await init_db()
    from web_app import create_app

    app = create_app()
    return await aiohttp_client(app)


async def test_captcha_endpoint_returns_question_and_token(client):
    resp = await client.get("/api/captcha")
    assert resp.status == 200
    data = await resp.json()
    assert "question" in data
    assert "token" in data


async def test_register_requires_captcha(client, monkeypatch):
    from tests.test_web_auth import _make_init_data

    init_data = _make_init_data(777, "test_captcha_secret")
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
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 400
    assert (await resp.json())["error"] == "Invalid captcha"


async def test_register_with_valid_captcha(client, monkeypatch):
    from tests.test_web_auth import _make_init_data
    from database import get_user

    captcha_resp = await client.get("/api/captcha")
    captcha = await captcha_resp.json()

    init_data = _make_init_data(778, "test_captcha_secret")
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
        "captcha_answer": _solve(captcha["question"]),
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 201, await resp.json()
    user = await get_user(778)
    assert user["name"] == "Анна"
