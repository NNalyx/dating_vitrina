from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.admin import admin_fake_avatar_upload
from states import AdminMenu


@pytest.fixture
def state():
    storage = MemoryStorage()
    return FSMContext(storage=storage, key="test")


@pytest.fixture
def message():
    msg = MagicMock()
    msg.photo = [MagicMock(file_id="photo_123")]
    msg.answer = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_admin_upload_photo_saves_avatar(message, state, monkeypatch):
    added = []

    async def fake_add_avatar(gender, file_id):
        added.append((gender, file_id))

    monkeypatch.setattr("handlers.admin.add_fake_avatar", fake_add_avatar)

    await state.set_state(AdminMenu.fake_avatar_upload)
    await state.update_data(fake_avatar_gender="male", fake_avatar_count=0)

    await admin_fake_avatar_upload(message, state)

    assert added == [("male", "photo_123")]
    message.answer.assert_awaited_once()
    assert "Добавлено: 1" in message.answer.await_args[0][0]
