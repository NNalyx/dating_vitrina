# keyboards.py

from itertools import islice
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, WebAppInfo
from config import INTEREST_CATEGORIES, GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS
from tunnel import get_tunnel_url


def _chunks(iterable, size: int):
    """Yield successive chunks of `size` from `iterable`."""
    it = iter(iterable)
    return iter(lambda: list(islice(it, size)), [])


def policy_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown with the privacy policy."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Согласен", callback_data="policy_agree")]
        ]
    )


def _options_keyboard(options, prefix: str) -> InlineKeyboardMarkup:
    """Build a compact 2-column keyboard for a list of options."""
    rows = []
    for chunk in _chunks(options, 2):
        rows.append(
            [
                InlineKeyboardButton(text=label, callback_data=f"{prefix}:{key}")
                for key, label in chunk
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gender_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting user's gender."""
    return _options_keyboard(GENDER_OPTIONS, "gender")


def looking_for_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting who the user is looking for."""
    return _options_keyboard(LOOKING_FOR_OPTIONS, "looking_for")


def goal_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting the dating goal."""
    return _options_keyboard(GOAL_OPTIONS, "goal")


def build_interests_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Build an inline keyboard with category headers and 2-column items."""
    rows = []
    for _category_key, category_label, items in INTEREST_CATEGORIES:
        rows.append(
            [InlineKeyboardButton(text=category_label, callback_data="noop")]
        )
        for chunk in _chunks(items, 2):
            row = []
            for item in chunk:
                mark = "✅ " if item in selected else ""
                row.append(
                    InlineKeyboardButton(
                        text=f"{mark}{item}", callback_data=f"interest:{item}"
                    )
                )
            rows.append(row)
    rows.append([InlineKeyboardButton(text="Готово ✅", callback_data="interest_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_photo_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when asking for an optional photo."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="photo_skip")]
        ]
    )


def mini_app_button_keyboard() -> InlineKeyboardMarkup | None:
    """Inline button that opens the Mini App."""
    url = get_tunnel_url()
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for profile editing options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data="edit:name"),
                InlineKeyboardButton(text="✏️ Возраст", callback_data="edit:age"),
            ],
            [
                InlineKeyboardButton(text="✏️ Кого ищу", callback_data="edit:looking_for"),
                InlineKeyboardButton(text="✏️ Цель", callback_data="edit:goal"),
            ],
            [
                InlineKeyboardButton(text="✏️ Интересы", callback_data="edit:interests"),
                InlineKeyboardButton(text="✏️ Фото", callback_data="edit:photo"),
            ],
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
        ]
    )


def write_link_keyboard(username: str | None, user_id: int) -> InlineKeyboardMarkup | None:
    """Keyboard with a link to start a private chat, or None if no usable link."""
    if username:
        url = f"https://t.me/{username}"
    else:
        # tg://user?id= deep links are unreliable for users the recipient has never chatted with.
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать", url=url)],
        ]
    )


def settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Keyboard for the settings screen."""
    if notifications_enabled:
        toggle_text = "🔔 Уведомления о лайках: включены (выключить)"
    else:
        toggle_text = "🔕 Уведомления о лайках: выключены (включить)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data="settings:toggle")],
            [InlineKeyboardButton(text="🔍 Фильтры ленты", callback_data="settings:filters")],
        ]
    )


def filters_keyboard(min_age: int, max_age: int, only_my_city: bool) -> InlineKeyboardMarkup:
    """Keyboard for configuring feed filters."""
    city_text = "🏙️ Только мой город" if only_my_city else "🌍 Любой город"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖ Мин", callback_data="filter:min_age:-1"),
                InlineKeyboardButton(text=f"Возраст: от {min_age} до {max_age}", callback_data="noop"),
                InlineKeyboardButton(text="➕ Мин", callback_data="filter:min_age:+1"),
            ],
            [
                InlineKeyboardButton(text="➖ Макс", callback_data="filter:max_age:-1"),
                InlineKeyboardButton(text="➕ Макс", callback_data="filter:max_age:+1"),
            ],
            [InlineKeyboardButton(text=city_text, callback_data="filter:toggle_city")],
            [InlineKeyboardButton(text="↩️ Сбросить", callback_data="filter:reset")],
        ]
    )



def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
                InlineKeyboardButton(text="👤 Пользователи", callback_data="admin:users"),
            ],
            [
                InlineKeyboardButton(text="🚨 Жалобы", callback_data="admin:reports"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast"),
            ],
            [
                InlineKeyboardButton(text="🏷 Интересы", callback_data="admin:interests"),
                InlineKeyboardButton(text="🚫 Баны", callback_data="admin:bans"),
            ],
            [
                InlineKeyboardButton(text="🎭 Фейки", callback_data="admin:fakes"),
                InlineKeyboardButton(text="📋 Логи", callback_data="admin:logs"),
            ],
        ]
    )


def admin_back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ В меню", callback_data="admin:menu")]
        ]
    )



def admin_interests_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories:
        rows.append(
            [InlineKeyboardButton(text=cat["label"], callback_data=f"admin:intcat:{cat['key']}")]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:intcat:add")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_interest_category_keyboard(cat_key: str, items: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        rows.append(
            [InlineKeyboardButton(text=f"❌ {item}", callback_data=f"admin:intremove:{cat_key}:{item}")]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить интерес", callback_data=f"admin:intadd:{cat_key}")])
    rows.append([InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"admin:intcatdel:{cat_key}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:interests")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_bans_keyboard(banned_users: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for user in banned_users:
        text = f"{user['name']}, {user['age']} (id:{user['user_id']})"
        rows.append(
            [InlineKeyboardButton(text=text, callback_data=f"admin:unban:{user['user_id']}")]
        )
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_fakes_keyboard(fake_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить фейк", callback_data="admin:fakes:add")],
            [InlineKeyboardButton(text="🖼 Аватарки фейков", callback_data="admin:fakes:avatars")],
            [InlineKeyboardButton(text=f"🗑 Сбросить все фейки ({fake_count})", callback_data="admin:fakes:reset")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:menu")],
        ]
    )


def admin_fake_avatars_gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мужские", callback_data="admin:fakeavatar:gender:male")],
            [InlineKeyboardButton(text="Женские", callback_data="admin:fakeavatar:gender:female")],
            [InlineKeyboardButton(text="Нейтральные", callback_data="admin:fakeavatar:gender:neutral")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:fakes")],
        ]
    )


def admin_fake_avatar_upload_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Готово", callback_data="admin:fakeavatar:done"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin:fakes"),
            ]
        ]
    )


def fake_options_keyboard(options: list[tuple[str, str]], field: str) -> InlineKeyboardMarkup:
    """Build a keyboard for choosing a fake profile option (gender/looking_for/goal)."""
    rows = []
    for key, label in options:
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"fakeopt:{field}:{key}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fake_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить фото", callback_data="fakeopt:photo:skip")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:fakes")],
        ]
    )


def fake_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data="fakeopt:publish")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:fakes")],
        ]
    )
