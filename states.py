# states.py

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    policy = State()
    age = State()
    name = State()
    interests = State()
    photo = State()
