# states.py

from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    policy = State()
    age = State()
    name = State()
    gender = State()
    looking_for = State()
    goal = State()
    interests = State()
    city = State()
    photo = State()


class EditProfile(StatesGroup):
    choosing_field = State()
    age = State()
    name = State()
    looking_for = State()
    goal = State()
    interests = State()
    photo = State()
