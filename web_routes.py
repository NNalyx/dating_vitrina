import io
import os
import tempfile

from aiohttp import web
from aiogram import Bot
from aiogram.types import FSInputFile

from config import MAX_AGE, MIN_AGE
from database import (
    add_like,
    add_user,
    add_view,
    get_all_users,
    get_notifications_enabled,
    get_user,
    get_user_filters,
    get_viewed_ids,
    has_like,
    set_notifications_enabled,
    update_user,
    update_user_filters,
    user_exists,
)
from services.city_validation import is_valid_city, normalize_city
from services.init_data import validate_init_data
from services.matching import filter_candidates, score_candidates
from services.moderation import is_clean_city, is_clean_name
from services.profile import format_profile

routes = web.RouteTableDef()

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


def _current_user_id(request: web.Request) -> int | None:
    return validate_init_data(request.headers.get("X-Init-Data", ""))


@routes.post("/api/auth")
async def auth(request: web.Request) -> web.Response:
    body = await request.json()
    user_id = validate_init_data(body.get("initData", ""))
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)
    exists = await user_exists(user_id)
    return web.json_response({"user_id": user_id, "is_registered": exists})


@routes.post("/api/register")
async def register(request: web.Request) -> web.Response:
    body = await request.json()
    user_id = validate_init_data(body.get("initData", ""))
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    name = str(body.get("name", "")).strip()
    city = str(body.get("city", "")).strip()

    if len(name) < 2:
        return web.json_response({"error": "Name too short"}, status=400)
    if not is_clean_name(name):
        return web.json_response({"error": "Name contains profanity"}, status=400)
    if not is_valid_city(city):
        return web.json_response({"error": "Invalid city"}, status=400)
    normalized_city = normalize_city(city)
    if not is_clean_city(normalized_city):
        return web.json_response({"error": "City contains profanity"}, status=400)

    try:
        await add_user(
            user_id=user_id,
            username=None,
            age=int(body["age"]),
            name=name,
            gender=str(body["gender"]),
            looking_for=str(body["looking_for"]),
            goal=str(body["goal"]),
            interests=list(body.get("interests", [])),
            photo_file_id=body.get("photo_file_id"),
            city=normalized_city,
        )
    except Exception as exc:
        return web.json_response({"error": str(exc)}, status=500)

    return web.json_response({"status": "ok"}, status=201)


@routes.post("/api/validate-city")
async def validate_city_endpoint(request: web.Request) -> web.Response:
    body = await request.json()
    raw = str(body.get("city", "")).strip()
    if not raw:
        return web.json_response({"valid": False, "error": "Введи город"})
    if not is_valid_city(raw):
        return web.json_response({"valid": False, "error": "Название города не похоже на настоящее"})
    normalized = normalize_city(raw)
    if not is_clean_city(normalized):
        return web.json_response({"valid": False, "error": "Недопустимые слова в названии города"})
    return web.json_response({"valid": True, "normalized": normalized})


@routes.post("/api/upload-photo")
async def upload_photo(request: web.Request) -> web.Response:
    init_data = request.headers.get("X-Init-Data", "")
    user_id = validate_init_data(init_data)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "photo":
        return web.json_response({"error": "No photo field"}, status=400)

    content_type = field.headers.get("Content-Type", "")
    if content_type not in ALLOWED_PHOTO_TYPES:
        return web.json_response({"error": "Invalid image type"}, status=400)

    photo_bytes = bytearray()
    size = 0
    while chunk := await field.read_chunk():
        size += len(chunk)
        if size > MAX_PHOTO_SIZE:
            return web.json_response({"error": "File too large"}, status=400)
        photo_bytes.extend(chunk)

    bot: Bot | None = request.app.get("bot")
    if bot is None:
        return web.json_response({"error": "Bot not configured"}, status=500)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(photo_bytes)
        tmp_path = tmp.name

    try:
        message = await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile(tmp_path),
            disable_notification=True,
        )
        file_id = message.photo[-1].file_id
        await bot.delete_message(chat_id=user_id, message_id=message.message_id)
        return web.json_response({"file_id": file_id})
    finally:
        os.remove(tmp_path)


@routes.get("/api/me")
async def me(request: web.Request) -> web.Response:
    init_data = request.headers.get("X-Init-Data", "")
    user_id = validate_init_data(init_data)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)
    user = await get_user(user_id)
    if user is None:
        return web.json_response({"error": "User not found"}, status=404)
    return web.json_response(user)


@routes.put("/api/me")
async def update_me(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    body = await request.json()
    user = await get_user(user_id)
    if user is None:
        return web.json_response({"error": "User not found"}, status=404)

    fields = {}

    if "name" in body:
        name = str(body["name"]).strip()
        if len(name) < 2:
            return web.json_response({"error": "Name too short"}, status=400)
        if not is_clean_name(name):
            return web.json_response({"error": "Name contains profanity"}, status=400)
        fields["name"] = name

    if "age" in body:
        age = int(body["age"])
        if age < MIN_AGE or age > MAX_AGE:
            return web.json_response({"error": f"Age must be between {MIN_AGE} and {MAX_AGE}"}, status=400)
        fields["age"] = age

    if "city" in body:
        city = str(body["city"]).strip()
        if not is_valid_city(city):
            return web.json_response({"error": "Invalid city"}, status=400)
        normalized = normalize_city(city)
        if not is_clean_city(normalized):
            return web.json_response({"error": "City contains profanity"}, status=400)
        fields["city"] = normalized

    if "looking_for" in body:
        fields["looking_for"] = str(body["looking_for"])

    if "goal" in body:
        fields["goal"] = str(body["goal"])

    if "interests" in body:
        interests = list(body["interests"])
        if len(interests) < 3:
            return web.json_response({"error": "Select at least 3 interests"}, status=400)
        fields["interests"] = interests

    if "photo_file_id" in body:
        value = body["photo_file_id"]
        fields["photo_file_id"] = value if value else None

    if not fields:
        return web.json_response({"status": "ok"})

    await update_user(user_id, **fields)
    return web.json_response({"status": "ok"})


@routes.get("/api/feed")
async def feed(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    user = await get_user(user_id)
    if user is None:
        return web.json_response({"error": "User not found"}, status=404)

    candidates = await get_all_users()
    viewed_ids = await get_viewed_ids(user_id)
    filtered = filter_candidates(user, candidates, viewed_ids)
    scored = score_candidates(user, filtered)

    if not scored:
        return web.json_response({"done": True})

    candidate, compatibility = scored[0]
    return web.json_response({**candidate, "compatibility": compatibility})


@routes.post("/api/feed/{id}/like")
async def feed_like(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    candidate_id = int(request.match_info["id"])
    await add_view(user_id, candidate_id)
    await add_like(user_id, candidate_id)

    is_mutual = await has_like(candidate_id, user_id)
    bot: Bot | None = request.app.get("bot")

    if is_mutual and bot:
        liker = await get_user(user_id)
        liked = await get_user(candidate_id)
        if liker and liked:
            await _send_match_notifications(bot, liker, liked)
    elif bot and await get_notifications_enabled(candidate_id):
        liker = await get_user(user_id)
        if liker:
            await _send_incoming_like(bot, liker, candidate_id)

    return web.json_response({"status": "ok", "mutual": is_mutual})


@routes.post("/api/feed/{id}/skip")
async def feed_skip(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    candidate_id = int(request.match_info["id"])
    await add_view(user_id, candidate_id)
    return web.json_response({"status": "ok"})


@routes.get("/api/likes")
async def likes(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    result = []
    for candidate in await get_all_users():
        cid = candidate["user_id"]
        if cid == user_id:
            continue
        if await has_like(cid, user_id) and not await has_like(user_id, cid):
            result.append(candidate)
    return web.json_response(result)


@routes.post("/api/likes/{id}/like_back")
async def like_back_endpoint(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    liker_id = int(request.match_info["id"])
    await add_like(user_id, liker_id)

    bot: Bot | None = request.app.get("bot")
    if bot:
        liker = await get_user(user_id)
        liked = await get_user(liker_id)
        if liker and liked:
            await _send_match_notifications(bot, liker, liked)

    return web.json_response({"status": "ok"})


@routes.post("/api/likes/{id}/skip")
async def skip_like_endpoint(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    liker_id = int(request.match_info["id"])
    await add_view(user_id, liker_id)
    return web.json_response({"status": "ok"})


@routes.get("/api/settings")
async def settings_get(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    filters = await get_user_filters(user_id)
    notifications = await get_notifications_enabled(user_id)
    return web.json_response({**filters, "notifications_enabled": notifications})


@routes.put("/api/settings")
async def settings_put(request: web.Request) -> web.Response:
    user_id = _current_user_id(request)
    if user_id is None:
        return web.json_response({"error": "Invalid initData"}, status=401)

    body = await request.json()
    min_age = int(body.get("min_age", MIN_AGE))
    max_age = int(body.get("max_age", MAX_AGE))
    only_my_city = bool(body.get("only_my_city", False))
    notifications_enabled = bool(body.get("notifications_enabled", True))

    min_age = max(MIN_AGE, min(MAX_AGE, min_age))
    max_age = max(MIN_AGE, min(MAX_AGE, max_age))
    if min_age > max_age:
        min_age, max_age = max_age, min_age

    await update_user(
        user_id,
        filter_min_age=min_age,
        filter_max_age=max_age,
        filter_only_my_city=only_my_city,
        notifications_enabled=notifications_enabled,
    )
    return web.json_response({"status": "ok"})


@routes.get("/api/photo/{file_id}")
async def get_photo(request: web.Request) -> web.Response:
    file_id = request.match_info["file_id"]
    bot: Bot | None = request.app.get("bot")
    if bot is None:
        return web.json_response({"error": "Bot not configured"}, status=500)

    file = await bot.get_file(file_id)
    if file is None:
        return web.json_response({"error": "Photo not found"}, status=404)

    buf = io.BytesIO()
    await bot.download(file, destination=buf)
    buf.seek(0)
    return web.Response(body=buf.read(), content_type="image/jpeg")


def _contact_markup(user: dict) -> dict:
    username = user.get("username")
    user_id = user["user_id"]
    url = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
    return {
        "inline_keyboard": [
            [{"text": "💬 Написать", "url": url}],
        ]
    }


async def _send_match_notifications(bot: Bot, liker: dict, liked: dict) -> None:
    liker_text = "<b>💞 Взаимный лайк!</b>\n\n" + format_profile(liked, title="📋 Анкета")
    liked_text = "<b>💞 Взаимный лайк!</b>\n\n" + format_profile(liker, title="📋 Анкета")

    for chat_id, text, contact in (
        (liker["user_id"], liker_text, liked),
        (liked["user_id"], liked_text, liker),
    ):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=_contact_markup(contact),
                parse_mode="HTML",
            )
        except Exception:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
            )


async def _send_incoming_like(bot: Bot, liker: dict, liked_id: int) -> None:
    text = "<b>💌 Тебя лайкнули!</b>\n\n" + format_profile(liker, title="📋 Анкета")
    photo_id = liker.get("photo_file_id")
    try:
        if photo_id:
            await bot.send_photo(
                chat_id=liked_id,
                photo=photo_id,
                caption=text,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=liked_id,
                text=text,
                parse_mode="HTML",
            )
    except Exception:
        pass
