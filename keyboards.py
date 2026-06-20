# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import INTEREST_CATEGORIES


def policy_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown with the privacy policy."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="policy_agree")]
        ]
    )


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
