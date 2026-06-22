from aiohttp import web

from web_routes import routes


ALLOWED_ORIGINS = {
    "https://nnalyx.github.io",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}


@web.middleware
async def cors_middleware(request: web.Request, handler):
    origin = request.headers.get("Origin", "")
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Init-Data"
    return resp


def create_app(bot=None) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app["bot"] = bot
    app.add_routes(routes)
    return app
