# config.py

import os

from dotenv import load_dotenv

# Load .env from the same directory as this config file.
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), ".env"),
    override=True,
)

# Telegram bot token is read from the BOT_TOKEN environment variable or a .env file.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_PATH = "dating_bot.db"
OWNER_ID = 8241460494
MIN_AGE = 16
MAX_AGE = 100

GENDER_OPTIONS = [
    ("male", "Парень"),
    ("female", "Девушка"),
    ("other", "Другое"),
]

LOOKING_FOR_OPTIONS = [
    ("male", "Парней"),
    ("female", "Девушек"),
    ("all", "Всех"),
]

GOAL_OPTIONS = [
    ("relationship", "Отношения"),
    ("friendship", "Дружба"),
    ("flirt", "Флирт"),
]

INTEREST_CATEGORIES = [
    (
        "games",
        "🎮 Игры",
        [
            "Dota 2",
            "Valorant",
            "CS2",
            "Counter-Strike 2",
            "League of Legends",
            "Minecraft",
            "Fortnite",
            "GTA",
            "GTA V",
            "Roblox",
            "Genshin Impact",
            "Honkai: Star Rail",
            "Zenless Zone Zero",
            "Mobile Games",
            "Apex Legends",
            "Overwatch 2",
            "Team Fortress 2",
            "PUBG",
            "Call of Duty",
            "World of Tanks",
            "War Thunder",
            "osu!",
            "Steam / PC Gaming",
            "Консоли (PlayStation / Xbox / Switch)",
            "Настольные игры",
            "VR / VRChat",
        ],
    ),
    (
        "animation",
        "🎬 Анимация",
        ["Аниме", "Манга", "Кино", "Сериалы", "YouTube", "Стримы", "Marvel / DC"],
    ),
    (
        "sport",
        "⚽ Спорт",
        [
            "Футбол",
            "Баскетбол",
            "Волейбол",
            "Теннис",
            "Хоккей",
            "Тренажёрный зал",
            "Бег",
            "Велоспорт",
            "Плавание",
            "Йога",
            "Скейтбординг",
            "Сноуборд",
            "Единоборства",
        ],
    ),
    (
        "creative",
        "🎨 Творчество",
        ["Музыка", "Рисование", "Фото", "Видеомонтаж", "Писательство", "Танцы", "Косплей", "DIY / Рукоделие"],
    ),
    (
        "tech",
        "💻 Технологии",
        ["Программирование", "Дизайн", "AI / ML", "Крипта", "Гаджеты", "Кибербезопасность", "Data Science"],
    ),
    (
        "lifestyle",
        "🌿 Образ жизни",
        ["Путешествия", "Кулинария", "Чтение", "Волонтёрство", "Медитация", "Здоровый образ жизни", "Кофе", "Животные"],
    ),
    (
        "music",
        "🎵 Музыка",
        ["Рок", "Поп", "Рэп", "Метал", "Классическая музыка", "Электронная музыка", "K-Pop", "Инди", "Играю на инструменте"],
    ),
]
