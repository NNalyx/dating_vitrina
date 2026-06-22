import pytest

from database import add_user, get_user, init_db


@pytest.fixture
async def client(aiohttp_client, tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    from web_app import create_app

    app = create_app()
    return await aiohttp_client(app)


async def test_register_new_user(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    from tests.test_web_auth import _make_init_data

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
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 201
    user = await get_user(111)
    assert user["name"] == "Анна"


async def test_register_profanity_name_returns_400(client, monkeypatch):
    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")
    from tests.test_web_auth import _make_init_data

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
    }
    resp = await client.post("/api/register", json=payload)
    assert resp.status == 400
