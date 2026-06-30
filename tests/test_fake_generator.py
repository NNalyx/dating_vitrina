import asyncio
import os

import pytest

import database
from database import add_user, init_db
from services.fake_profile_generator import (
    _choose_gender_and_looking_for,
    _generate_bio,
    _pick_age,
    _pick_city,
    _pick_interests,
    generate_fake_profiles_batch,
)

TEST_DB = "test_fake_generator.db"
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


async def _add_viewer(user_id: int = 1):
    await add_user(
        user_id=user_id,
        username=None,
        age=22,
        name="Оля",
        gender="female",
        looking_for="male",
        goal="relationship",
        interests=["Аниме", "Dota 2", "Музыка"],
        city="Москва",
    )


def test_gender_matches_viewer_preference():
    viewer = {"gender": "female", "looking_for": "male"}
    gender, looking_for = _choose_gender_and_looking_for(viewer)
    assert gender == "male"
    assert looking_for == "female"


def test_age_respects_viewer_filters():
    viewer = {"filter_min_age": 20, "filter_max_age": 25}
    age = _pick_age(viewer)
    assert 20 <= age <= 25


def test_city_respects_only_my_city():
    viewer = {"filter_only_my_city": 1, "city": "Казань"}
    assert _pick_city(viewer) == "Казань"


def test_interests_overlap_when_filter_enabled():
    viewer = {
        "filter_interests": 1,
        "interests": "Аниме,Dota 2,Музыка",
    }
    interests = _pick_interests(viewer)
    assert any(interest in {"Аниме", "Dota 2", "Музыка"} for interest in interests)


def test_bio_is_uniqueish():
    bios = {
        _generate_bio("Аня", 22, "Москва", ["Аниме", "Dota 2", "Музыка"], "relationship")
        for _ in range(20)
    }
    assert len(bios) > 1


@pytest.mark.asyncio
async def test_generate_batch_creates_fake_users():
    await _add_viewer()
    viewer = await database.get_user(1)
    fakes = await generate_fake_profiles_batch(viewer, count=2)
    assert len(fakes) == 2
    for fake in fakes:
        assert fake["is_fake"] == 1
        assert fake["user_id"] < 0
        assert fake["bio"]
