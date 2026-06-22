import os
import tempfile

from aiohttp import web
from aiogram import Bot
from aiogram.types import FSInputFile

from database import add_user, get_user, user_exists
from services.city_validation import is_valid_city, normalize_city
from services.init_data import validate_init_data
from services.moderation import is_clean_city, is_clean_name

routes = web.RouteTableDef()

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


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
