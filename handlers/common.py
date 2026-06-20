# handlers/common.py

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import user_exists
from keyboards import policy_keyboard
from states import Registration

router = Router()

PRIVACY_POLICY_TEXT = (
    "<b>Политика конфиденциальности</b>\n\n"
    "<span class=\"tg-spoiler\">"
    "Нажимая «Согласен», вы подтверждаете, что вам исполнилось 16 лет, "
    "и соглашаетесь на обработку предоставленных данных (возраст, имя/ник, фото, увлечения) "
    "в рамках работы бота. Администрация не несёт ответственности за действия пользователей "
    "и содержание анкет. Мы не передаём персональные данные третьим лицам."
    "</span>\n\n"
    "Для продолжения регистрации нажмите кнопку ниже."
)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()

    if await user_exists(message.from_user.id):
        await message.answer(
            "Привет снова! Ты уже зарегистрирован. Используй /search для поиска анкет."
        )
        return

    await message.answer(
        "Добро пожаловать! Для начала работы нужно пройти регистрацию.\n\n"
        + PRIVACY_POLICY_TEXT,
        reply_markup=policy_keyboard(),
    )
    await state.set_state(Registration.policy)
