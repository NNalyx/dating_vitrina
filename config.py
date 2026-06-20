# config.py

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with the real token from BotFather
DB_PATH = "dating_bot.db"
MIN_AGE = 16

INTEREST_CATEGORIES = [
    (
        "games",
        "🎮 Игры",
        [
            "Dota 2",
            "Valorant",
            "CS2",
            "League of Legends",
            "Minecraft",
            "Fortnite",
            "GTA",
            "Roblox",
            "Genshin Impact",
            "Mobile Games",
        ],
    ),
    (
        "animation",
        "🎬 Анимация",
        ["Аниме", "Манга", "Кино", "Сериалы", "YouTube", "Стримы"],
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
        ],
    ),
    (
        "creative",
        "🎨 Творчество",
        ["Музыка", "Рисование", "Фото", "Видеомонтаж", "Писательство"],
    ),
    (
        "tech",
        "💻 Технологии",
        ["Программирование", "Дизайн", "AI/ML", "Крипта", "Гаджеты"],
    ),
    (
        "lifestyle",
        "🌿 Образ жизни",
        ["Путешествия", "Кулинария", "Чтение", "Настольные игры", "Волонтёрство"],
    ),
]
