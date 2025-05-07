import asyncio
import json
from http import HTTPStatus
from typing import cast

from starlette.exceptions import HTTPException
from starlette.responses import StreamingResponse

from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Backends, Endpoint, HTTPMethod
from starlette.requests import Request

from idum_proxy.networking.connection_pooling.connection_pooling import (
    ConnectionPoolingSession,
)
from idum_proxy.protocols.https import HTTPS
from idum_proxy.security.authentication.auth import Auth


class Https:
    def __init__(self, connection_pooling, endpoint: Endpoint, backend: Backends):
        self.endpoint = endpoint
        self.backend = backend
        self.connection_pooling = connection_pooling

    async def _forge_target_url(self, url: str, path: str, prefix: str) -> str:
        if url.endswith("$"):
            target_url = url.rstrip("$")
        else:
            path_without_prefix = path.removeprefix(prefix).strip("/")
            target_url = f"{url}/{path_without_prefix}"
        target_url = target_url.strip("/")

        await async_logger.info(f"target URL: {target_url}")
        return target_url

    async def https_request(
        self,
        prefix: str,
        url: str,
        method: HTTPMethod = HTTPMethod.GET,
        headers: dict[str, str] | None = None,
        auth: Auth | None = None,
        data: str | None = None,
        json_data: str | None = None,
        timeout: int | float | None = None,
    ):
        try:
            connection_pooling_session: ConnectionPoolingSession = (
                self.connection_pooling.connection_pool_sessions[prefix]
            )
            async with connection_pooling_session.get_session() as session:
                https: HTTPS = HTTPS(client_session=session, timeout=timeout)
                headers = headers.copy() if headers else {}
                if auth:
                    headers.update(auth.get_headers())
                return await https.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    json_data=json_data,
                )
        finally:
            # for keepalive
            await asyncio.sleep(0.01)

    async def handle_request(self, request: Request, headers: dict):
        backend = (
            self.backend.https[0]
            if isinstance(self.backend.https, list)
            else self.backend.https
        )
        target_url = await self._forge_target_url(
            url=backend.url, path=request.url.path, prefix=self.endpoint.prefix
        )

        http_methods = backend.methods
        headers.update(backend.headers)

        if request.method not in http_methods:
            raise HTTPException(
                status_code=HTTPStatus.METHOD_NOT_ALLOWED,
                detail="Http method not supported",
            )

        body = (
            await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
        )
        content_type = request.headers.get("content-type", "")
        is_json = "application/json" in content_type.lower()
        json_data: str | None = None
        data: str | None = None

        if body:
            if is_json:
                try:
                    # Parse body as JSON and pass as json_data
                    json_data = json.loads(body)
                except json.JSONDecodeError:
                    # If parsing fails but Content-Type is JSON, pass as raw data
                    data = body.decode("utf-8")
            else:
                # For non-JSON content types, pass as raw data
                data = body.decode("utf-8")

        timeout = backend.timeout
        response = await self.https_request(
            prefix=self.endpoint.prefix,
            url=target_url,
            method=cast(HTTPMethod, request.method),
            headers=headers,
            data=data,
            json_data=json_data,
            timeout=timeout,
        )

        if not isinstance(response, StreamingResponse):
            response.headers["content-length"] = str(len(response.body))
        return response
