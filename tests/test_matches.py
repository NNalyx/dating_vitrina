import pytest

from database import add_like, add_user, get_matches, init_db
from services.matching import score_candidates
from tests.test_database_filters import ORIGINAL_DB_PATH, TEST_DB, _setup, _teardown


def test_get_matches_returns_mutual_likes():
    _setup()
    try:
        import asyncio

        async def run():
            await add_user(
                user_id=1,
                username=None,
                age=25,
                name="Анна",
                gender="female",
                looking_for="male",
                goal="relationship",
                interests=["Музыка", "Спорт"],
                photo_file_id=None,
                city="Москва",
            )
            await add_user(
                user_id=2,
                username=None,
                age=26,
                name="Пётр",
                gender="male",
                looking_for="female",
                goal="relationship",
                interests=["Музыка", "Кино"],
                photo_file_id=None,
                city="Москва",
            )
            await add_user(
                user_id=3,
                username=None,
                age=27,
                name="Иван",
                gender="male",
                looking_for="female",
                goal="relationship",
                interests=["Спорт"],
                photo_file_id=None,
                city="Москва",
            )
            # mutual like between 1 and 2
            await add_like(1, 2)
            await add_like(2, 1)
            # one-way like from 3 to 1
            await add_like(3, 1)
            matches = await get_matches(1)
            assert len(matches) == 1
            assert matches[0]["user_id"] == 2

        asyncio.run(run())
    finally:
        _teardown()


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


async def test_api_matches_returns_mutual_like(client, monkeypatch):
    import re

    from tests.test_web_auth import _make_init_data

    def solve(question):
        m = re.match(r"(\d+)\s*([+\-])\s*(\d+)", question)
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return str(a + b if op == "+" else a - b)

    monkeypatch.setattr("services.init_data.BOT_TOKEN", "test_token_12345")

    async def register(uid):
        captcha = await (await client.get("/api/captcha")).json()
        payload = {
            "initData": _make_init_data(uid, "test_token_12345"),
            "captcha_token": captcha["token"],
            "captcha_answer": solve(captcha["question"]),
            "age": 25,
            "name": "User",
            "gender": "female" if uid == 1 else "male",
            "looking_for": "male" if uid == 1 else "female",
            "goal": "relationship",
            "interests": ["Музыка", "Спорт", "Кино"],
            "city": "Москва",
            "photo_file_id": None,
        }
        resp = await client.post("/api/register", json=payload)
        assert resp.status == 201, await resp.json()

    await register(1)
    await register(2)
    await client.post("/api/feed/2/like", headers={"X-Init-Data": _make_init_data(1, "test_token_12345")})
    await client.post("/api/feed/1/like", headers={"X-Init-Data": _make_init_data(2, "test_token_12345")})

    resp = await client.get("/api/matches", headers={"X-Init-Data": _make_init_data(1, "test_token_12345")})
    assert resp.status == 200
    data = await resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 2
    assert "compatibility" in data[0]
