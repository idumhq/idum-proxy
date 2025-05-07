from http import HTTPStatus

import pytest
from starlette.applications import Starlette

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from idum_proxy import IdumProxy
from idum_proxy.middlewares.security.ip_filter import IpFilterMiddleware


@pytest.mark.asyncio
async def test_ip_filter_middleware():
    idum_proxy = IdumProxy("idum_proxy/default.json")

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
    assert response.status_code == HTTPStatus.FORBIDDEN

    response = client.get("/example")
    assert response.status_code == HTTPStatus.FORBIDDEN
