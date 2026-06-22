# handlers/common.py

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import user_exists
from handlers.menu import show_main_menu
from keyboards import policy_keyboard
from states import Registration

router = Router()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: types.CallbackQuery) -> None:
    """Ignore taps on non-interactive category header buttons."""
    await callback.answer()

PRIVACY_POLICY_TEXT = (
    "<b>Политика конфиденциальности</b>\n\n"
    "<blockquote expandable>\n"
    "1. Мы храним: возраст, имя, пол, цель знакомства, увлечения и фото.\n"
    "2. Данные используются только для подбора анкет внутри бота.\n"
    "3. Бот предназначен для пользователей 16+.\n"
    "4. Мы не передаём данные третьим лицам.\n"
    "5. Администрация не отвечает за поведение других пользователей.\n"
    "</blockquote>\n\n"
    "Для продолжения регистрации нажми кнопку ниже."
)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()

    if message.from_user is None:
        return

    if await user_exists(message.from_user.id):
        await show_main_menu(message, state)
        return

    await message.answer(
        "Добро пожаловать! Для начала работы нужно пройти регистрацию.\n\n"
        + PRIVACY_POLICY_TEXT,
        reply_markup=policy_keyboard(),
    )
    await state.set_state(Registration.policy)
