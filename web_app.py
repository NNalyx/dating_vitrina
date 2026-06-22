from aiohttp import web

from web_routes import routes


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    return app
