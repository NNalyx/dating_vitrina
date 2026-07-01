import asyncio
import os

import pytest

import database
from database import (
    init_db,
    add_fake_avatar,
    get_random_fake_avatar_file_id,
    count_fake_avatars,
)

TEST_DB = "test_fake_avatars.db"
ORIGINAL_DB_PATH = database.DB_PATH


@pytest.fixture(autouse=True)
def _db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    database.DB_PATH = TEST_DB
    asyncio.run(init_db())
    yield
    database.DB_PATH = ORIGINAL_DB_PATH
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.mark.asyncio
async def test_add_and_retrieve_avatar():
    await add_fake_avatar("male", "file_id_123")
    assert await count_fake_avatars("male") == 1
    file_id = await get_random_fake_avatar_file_id("male")
    assert file_id == "file_id_123"


@pytest.mark.asyncio
async def test_fallback_to_neutral():
    await add_fake_avatar("neutral", "neutral_id")
    assert await get_random_fake_avatar_file_id("male") == "neutral_id"


@pytest.mark.asyncio
async def test_returns_none_when_empty():
    assert await get_random_fake_avatar_file_id("female") is None
