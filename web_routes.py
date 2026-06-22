from aiohttp import web

from database import add_user, get_user, user_exists
from services.city_validation import is_valid_city, normalize_city
from services.init_data import validate_init_data
from services.moderation import is_clean_city, is_clean_name

routes = web.RouteTableDef()


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
