import json
import random
from pathlib import Path

from config import INTEREST_CATEGORIES
from database import add_fake_user, get_user

AVATARS_DIR = Path("data/fake_avatars")
FILE_IDS_PATH = AVATARS_DIR / "file_ids.json"

ALL_INTERESTS = [item for _, _, items in INTEREST_CATEGORIES for item in items]

MALE_NAMES = [
    "Александр",
    "Максим",
    "Дмитрий",
    "Артём",
    "Иван",
    "Кирилл",
    "Никита",
    "Михаил",
    "Егор",
    "Матвей",
    "Андрей",
    "Илья",
    "Алексей",
    "Роман",
    "Владимир",
    "Павел",
]

FEMALE_NAMES = [
    "Анастасия",
    "Мария",
    "Анна",
    "Виктория",
    "Екатерина",
    "София",
    "Дарья",
    "Алиса",
    "Вероника",
    "Полина",
    "Елизавета",
    "Ксения",
    "Александра",
    "Ольга",
    "Татьяна",
    "Юлия",
]

CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Челябинск",
    "Самара",
    "Уфа",
    "Ростов-на-Дону",
    "Красноярск",
    "Воронеж",
    "Пермь",
    "Волгоград",
    "Краснодар",
]

GOAL_LABELS = {
    "relationship": "отношения",
    "friendship": "дружбу",
    "flirt": "флирт",
}

BIO_TEMPLATES = [
    "{name}, {age}. Живу в {city}. Увлекаюсь {interest1} и {interest2}. Ищу {goal}.",
    "Привет! Я из {city}. Люблю {interest1} и не представляю жизни без {interest2}. Хочу {goal}.",
    "{city}, {age} лет. Главные увлечения: {interest1}, {interest2}. Цель — {goal}.",
    "Люблю {interest1}, {interest2} и новые знакомства. Живу в {city}, ищу {goal}.",
    "{name}, {age}. Мой город — {city}. Увлекаюсь {interest1} и {interest2}. Ищу {goal}.",
    "Из {city}. Свободное время провожу за {interest1} и {interest2}. Хочу {goal}.",
    "{age} лет, {city}. Интересы: {interest1}, {interest2}. Ищу {goal}.",
    "Живу в {city}, увлекаюсь {interest1}. Также нравится {interest2}. Ищу {goal}.",
    "{name}. Люблю {interest1} и {interest2}. Из {city}, {age} лет. Цель — {goal}.",
    "{city}. {age} лет. {interest1} и {interest2} — то, что меня заводит. Ищу {goal}.",
]


def _load_file_ids() -> list[dict]:
    if not FILE_IDS_PATH.exists():
        return []
    return json.loads(FILE_IDS_PATH.read_text(encoding="utf-8"))


def pick_avatar_file_id(gender: str) -> str | None:
    file_ids = _load_file_ids()
    if not file_ids:
        return None
    gender_key = gender if gender in ("male", "female") else "neutral"
    candidates = [record for record in file_ids if record.get("gender") == gender_key]
    if not candidates:
        candidates = [record for record in file_ids if record.get("gender") == "neutral"]
    if not candidates:
        candidates = file_ids
    return random.choice(candidates)["file_id"]


def _pick_name(gender: str) -> str:
    pool = (
        MALE_NAMES
        if gender == "male"
        else FEMALE_NAMES
        if gender == "female"
        else MALE_NAMES + FEMALE_NAMES
    )
    return random.choice(pool)


def _choose_gender_and_looking_for(viewer: dict) -> tuple[str, str]:
    viewer_gender = viewer.get("gender", "other")
    viewer_looking = viewer.get("looking_for", "all")

    if viewer_looking == "male":
        gender = "male"
    elif viewer_looking == "female":
        gender = "female"
    else:
        gender = random.choice(["male", "female"])

    if viewer_gender in ("male", "female"):
        looking_for = viewer_gender
    else:
        looking_for = "all"

    return gender, looking_for


def _pick_age(viewer: dict) -> int:
    min_age = max(viewer.get("filter_min_age", 18), 18)
    max_age = min(viewer.get("filter_max_age", 35), 45)
    if min_age > max_age:
        max_age = min_age
    return random.randint(min_age, max_age)


def _pick_city(viewer: dict) -> str:
    only_my_city = bool(viewer.get("filter_only_my_city", 0))
    user_city = viewer.get("city")
    if only_my_city and user_city:
        return user_city
    if user_city and random.random() < 0.5:
        return user_city
    return random.choice(CITIES)


def _pick_goal(viewer: dict) -> str:
    user_goal = viewer.get("goal")
    if user_goal and random.random() < 0.7:
        return user_goal
    return random.choice(["relationship", "friendship", "flirt"])


def _pick_interests(viewer: dict) -> list[str]:
    filter_interests = bool(viewer.get("filter_interests", 0))
    user_interests_raw = viewer.get("interests") or ""
    user_interests = {item.strip() for item in user_interests_raw.split(",") if item.strip()}

    if filter_interests and user_interests:
        overlap = random.sample(list(user_interests), min(2, len(user_interests)))
        extras = random.sample(ALL_INTERESTS, k=min(3, len(ALL_INTERESTS)))
        interests = list(dict.fromkeys(overlap + extras))
    else:
        interests = random.sample(ALL_INTERESTS, k=min(5, len(ALL_INTERESTS)))

    return interests[:5]


def _generate_bio(name: str, age: int, city: str, interests: list[str], goal: str) -> str:
    selected = random.sample(interests, min(2, len(interests)))
    interest1, interest2 = selected[0], selected[1]
    goal_label = GOAL_LABELS.get(goal, goal)
    template = random.choice(BIO_TEMPLATES)
    return template.format(
        name=name,
        age=age,
        city=city,
        interest1=interest1,
        interest2=interest2,
        goal=goal_label,
    )


async def generate_fake_profiles_batch(viewer: dict, count: int = 3) -> list[dict]:
    fakes = []
    for _ in range(count):
        gender, looking_for = _choose_gender_and_looking_for(viewer)
        name = _pick_name(gender)
        age = _pick_age(viewer)
        city = _pick_city(viewer)
        goal = _pick_goal(viewer)
        interests = _pick_interests(viewer)
        bio = _generate_bio(name, age, city, interests, goal)
        photo_file_id = pick_avatar_file_id(gender)

        user_id = await add_fake_user(
            name=name,
            age=age,
            gender=gender,
            looking_for=looking_for,
            goal=goal,
            interests=interests,
            city=city,
            photo_file_id=photo_file_id,
            bio=bio,
        )
        fakes.append(await get_user(user_id))
    return fakes
