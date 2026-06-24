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


class AdminMenu(StatesGroup):
    users_search = State()
    ban_input = State()
    broadcast_text = State()
    broadcast_confirm = State()
    interest_action = State()
    interest_category_key = State()
    interest_category_label = State()
    interest_name = State()
    interest_remove = State()
