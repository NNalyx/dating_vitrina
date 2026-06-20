# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import INTEREST_CATEGORIES, GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS


def policy_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown with the privacy policy."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="policy_agree")]
        ]
    )


def gender_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting user's gender."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"gender:{key}")]
        for key, label in GENDER_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def looking_for_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting who the user is looking for."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"looking_for:{key}")]
        for key, label in LOOKING_FOR_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def goal_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting the dating goal."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"goal:{key}")]
        for key, label in GOAL_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_interests_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Build an inline keyboard where selected items have a checkmark."""
    buttons = []
    for _category_key, _category_label, items in INTEREST_CATEGORIES:
        for item in items:
            mark = "✅ " if item in selected else ""
            buttons.append(
                [InlineKeyboardButton(text=f"{mark}{item}", callback_data=f"interest:{item}")]
            )
    buttons.append([InlineKeyboardButton(text="Готово ✅", callback_data="interest_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def skip_photo_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when asking for an optional photo."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="photo_skip")]
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Моя анкета")],
            [KeyboardButton(text="🔍 Смотреть анкеты")],
            [KeyboardButton(text="❤️ Мои лайки")],
        ],
        resize_keyboard=True,
    )


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for profile editing options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Имя", callback_data="edit:name")],
            [InlineKeyboardButton(text="✏️ Возраст", callback_data="edit:age")],
            [InlineKeyboardButton(text="✏️ Кого ищу", callback_data="edit:looking_for")],
            [InlineKeyboardButton(text="✏️ Цель", callback_data="edit:goal")],
            [InlineKeyboardButton(text="✏️ Интересы", callback_data="edit:interests")],
            [InlineKeyboardButton(text="✏️ Фото", callback_data="edit:photo")],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )


def browse_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for browsing profiles."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Лайк", callback_data="browse:like"),
                InlineKeyboardButton(text="👎 Пропустить", callback_data="browse:skip"),
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )


def like_response_keyboard(liker_id: int) -> InlineKeyboardMarkup:
    """Keyboard for responding to an incoming like."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Лайк в ответ", callback_data=f"like_back:{liker_id}"),
                InlineKeyboardButton(text="👎 Пропустить", callback_data=f"like_skip:{liker_id}"),
            ],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )


def write_link_keyboard(username: str | None, user_id: int) -> InlineKeyboardMarkup:
    """Keyboard with a link to start a private chat."""
    if username:
        url = f"https://t.me/{username}"
    else:
        url = f"tg://user?id={user_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать", url=url)],
            [InlineKeyboardButton(text="🔙 В меню", callback_data="menu")],
        ]
    )
