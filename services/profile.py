# services/profile.py

from config import GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS


_LABEL_MAP = {}
for _options in (GENDER_OPTIONS, LOOKING_FOR_OPTIONS, GOAL_OPTIONS):
    _LABEL_MAP.update(dict(_options))


def _label(key: str) -> str:
    return _LABEL_MAP.get(key, key)


def format_profile(user: dict, *, title: str = "📋 Анкета") -> str:
    """Format a user dict into a profile card text."""
    interests = user.get("interests") or ""
    interests_list = [i.strip() for i in interests.split(",") if i.strip()]
    interests_text = ", ".join(interests_list) if interests_list else "—"

    lines = [
        f"<b>{title}</b>",
        "",
        f"<b>Имя:</b> {user['name']}",
        f"<b>Возраст:</b> {user['age']}",
        f"<b>Пол:</b> {_label(user['gender'])}",
        f"<b>Ищу:</b> {_label(user['looking_for'])}",
        f"<b>Цель:</b> {_label(user['goal'])}",
        f"<b>Увлечения:</b> {interests_text}",
    ]

    city = user.get("city")
    if city:
        lines.append(f"<b>📍 Город:</b> {city}")

    return "\n".join(lines)


def format_browse_card(user: dict, compatibility: int) -> str:
    """Format a candidate card for the browse feed."""
    interests = user.get("interests") or ""
    interests_list = [i.strip() for i in interests.split(",") if i.strip()]
    interests_text = ", ".join(interests_list) if interests_list else "—"

    lines = [
        f"<b>{user['name']}, {user['age']}</b>",
        f"<b>Совместимость:</b> {compatibility}% ❤️",
        "",
        f"🎯 <b>Цель:</b> {_label(user['goal'])}",
        f"⭐ <b>Увлечения:</b> {interests_text}",
    ]
    return "\n".join(lines)
