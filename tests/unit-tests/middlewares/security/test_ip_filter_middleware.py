import logging
from http import HTTPStatus

import pytest
from starlette.applications import Starlette

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from idum_proxy import IdumProxy
from idum_proxy.config.models import Config
from idum_proxy.middlewares.security.ip_filter import IpFilterMiddleware


@pytest.fixture(params=[True, False])
def config(request):
    return Config(
        **{
            "version": "1.0",
            "name": "Default config",
            "middlewares": {
                "security": {
                    "ip_filter": {"enabled": request.param, "blacklist": ["*.0.0.2"]}
                },
            },
            "endpoints": [
                {
                    "prefix": "/",
                    "match": "**/*",
                    "backends": {
                        "https": {"url": "https://jsonplaceholder.typicode.com/posts"}
                    },
                    "upstream": {"proxy": {"enabled": True}},
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_ip_filter_middleware(config):
    enabled = config.middlewares.security.ip_filter.enabled
    logging.info(f"Enabled = {enabled}")
    idum_proxy = IdumProxy(config=config)

    async def test_ip(request: Request):
        client_ip = request.client.host if request.client else None
        return JSONResponse({"client_ip": client_ip})

    routes = [Route("/test-ip", endpoint=test_ip)]

    app = Starlette(routes=routes)

    # Add the middleware to your app
    app.add_middleware(IpFilterMiddleware, config=idum_proxy.config)  # type: ignore

    # Create a test client
    client = TestClient(app)

    # Test a request
    response = client.get("/test-ip")
    assert response.status_code == HTTPStatus.OK

    response = client.get("/example")
    assert response.status_code == HTTPStatus.NOT_FOUND

    client = TestClient(app, client=("1.0.0.2", 1000))
    response = client.get("/test-ip")
    assert response.status_code == HTTPStatus.FORBIDDEN if enabled else HTTPStatus.OK

    response = client.get("/example")
    assert response.status_code == HTTPStatus.FORBIDDEN if enabled else HTTPStatus.OK
