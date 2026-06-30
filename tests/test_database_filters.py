import asyncio
import os

import database
from database import init_db, add_user, get_user, update_user, update_user_filters, get_user_filters

TEST_DB = "test_filters.db"
ORIGINAL_DB_PATH = database.DB_PATH


def _setup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    database.DB_PATH = TEST_DB
    asyncio.run(init_db())


def _teardown():
    database.DB_PATH = ORIGINAL_DB_PATH
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


async def _add_sample_user(user_id: int, city: str | None = None):
    await add_user(
        user_id=user_id,
        username=None,
        age=25,
        name="Alice",
        gender="female",
        looking_for="male",
        goal="relationship",
        interests=["Dota 2", "Аниме"],
        photo_file_id=None,
        city=city,
    )


def test_user_stores_city():
    _setup()
    try:
        asyncio.run(_add_sample_user(1, "Москва"))
        user = asyncio.run(get_user(1))
        assert user["city"] == "Москва"
    finally:
        _teardown()


def test_update_user_filters():
    _setup()
    try:
        asyncio.run(_add_sample_user(2))
        asyncio.run(update_user_filters(2, min_age=20, max_age=30, only_my_city=True))
        filters = asyncio.run(get_user_filters(2))
        assert filters == {"min_age": 20, "max_age": 30, "only_my_city": True, "filter_interests": False}
    finally:
        _teardown()


def test_filter_interests_toggle():
    _setup()
    try:
        asyncio.run(_add_sample_user(4))
        asyncio.run(update_user(4, filter_interests=True))
        filters = asyncio.run(get_user_filters(4))
        assert filters["filter_interests"] is True
        user = asyncio.run(get_user(4))
        assert user["filter_interests"] == 1
    finally:
        _teardown()


def test_update_user_username():
    _setup()
    try:
        asyncio.run(_add_sample_user(3))
        asyncio.run(update_user(3, username="new_user"))
        user = asyncio.run(get_user(3))
        assert user["username"] == "new_user"
    finally:
        _teardown()
