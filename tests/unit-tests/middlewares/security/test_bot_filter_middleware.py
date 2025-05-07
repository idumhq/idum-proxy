from http import HTTPStatus

import pytest

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from idum_proxy import IdumProxy
from idum_proxy.middlewares.security.bot_filter import BotFilterMiddleware


@pytest.mark.asyncio
async def test_bot_filter_middleware():
    idum_proxy = IdumProxy("idum_proxy/default.json")

    async def test_ip(request: Request):
        client_ip = request.client.host if request.client else None
        return JSONResponse({"client_ip": client_ip})

    routes = [Route("/test-bot", endpoint=test_ip)]

    app = Starlette(routes=routes)

    # Add the middleware to your app
    app.add_middleware(BotFilterMiddleware, config=idum_proxy.config)  # type: ignore

    client = TestClient(app)

    response = client.get("/test-bot")
    assert response.status_code == HTTPStatus.OK

    response = client.get("/example")
    assert response.status_code == HTTPStatus.NOT_FOUND

    client = TestClient(app, headers={"User-Agent": "crawl-66-249-66-1.googlebot.com"})
    response = client.get("/test-bot")
    assert response.status_code == HTTPStatus.FORBIDDEN

    response = client.get("/example")
    assert response.status_code == HTTPStatus.FORBIDDEN
