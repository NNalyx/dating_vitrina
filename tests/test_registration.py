# tests/test_registration.py

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from handlers.registration import _save_profile, process_city, process_name
from states import Registration


def _make_message(user_id: int, username: str | None, is_bot: bool):
    message = MagicMock()
    message.from_user = MagicMock(id=user_id, username=username, is_bot=is_bot)
    message.answer = AsyncMock()
    return message


def test_save_profile_uses_passed_user_id(monkeypatch):
    """Regression test: even if the message object belongs to the bot, the
    real user's id/username must be saved. This previously failed when users
    skipped the photo step because callback.message.from_user was the bot.
    """
    captured = {}

    async def fake_add_user(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("handlers.registration.add_user", fake_add_user)
    monkeypatch.setattr("handlers.registration.show_main_menu", AsyncMock())

    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "age": 20,
            "name": "Alice",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["Dota 2", "Аниме", "Кино"],
            "city": "Москва",
        }
    )

    # The message object comes from a callback, so its `from_user` is the bot.
    message = _make_message(user_id=999999999, username="MyBot", is_bot=True)

    asyncio.run(
        _save_profile(
            message,
            state,
            user_id=123456,
            username="alice",
            photo_id="photo123",
        )
    )

    assert captured["user_id"] == 123456
    assert captured["username"] == "alice"
    assert captured["photo_file_id"] == "photo123"
    assert captured["age"] == 20
    assert captured["gender"] == "female"
    assert captured["city"] == "Москва"


def test_process_name_rejects_profanity():
    message = MagicMock()
    message.text = "блядь"
    message.answer = AsyncMock()

    state = MagicMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    asyncio.run(process_name(message, state))

    state.update_data.assert_not_called()
    message.answer.assert_awaited_once_with(
        "⚠️ Имя содержит недопустимые слова. Введи другое имя."
    )


def test_process_city_rejects_profanity():
    message = MagicMock()
    message.text = "блядь"
    message.answer = AsyncMock()

    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "age": 25,
            "name": "Анна",
            "gender": "female",
            "looking_for": "male",
            "goal": "relationship",
            "interests": ["music", "sport", "travel"],
        }
    )
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    asyncio.run(process_city(message, state))

    state.update_data.assert_not_called()
    message.answer.assert_awaited_once_with(
        "⚠️ Название города содержит недопустимые слова. Введи город ещё раз."
    )
