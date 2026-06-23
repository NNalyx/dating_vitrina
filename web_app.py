from pathlib import Path

from aiohttp import web

from web_routes import routes


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Init-Data"
    return resp


DOCS_DIR = Path(__file__).parent / "docs"


async def _index_handler(request: web.Request) -> web.StreamResponse:
    return web.FileResponse(DOCS_DIR / "index.html")


def create_app(bot=None) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app["bot"] = bot
    app.add_routes(routes)
    app.router.add_get("/", _index_handler)
    app.router.add_static("/", path=DOCS_DIR, name="static")
    return app
