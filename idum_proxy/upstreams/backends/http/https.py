import asyncio
import json
import logging
from http import HTTPStatus
from typing import cast, Any

import aiohttp
from aiohttp import ClientTimeout, TCPConnector, TraceConfig
from starlette.exceptions import HTTPException
from starlette.responses import StreamingResponse, Response

from idum_proxy.config.models import Backends, Endpoint, HTTPMethod
from starlette.requests import Request

from idum_proxy.networking.connection_pooling.tracing.default_trace_handler import (
    TraceHandlers,
)
from idum_proxy.protocols.https_aiohttp import HTTPS_aiohttp
from idum_proxy.security.authentication.auth import Auth

from idum_proxy.logger import get_logger

logger = get_logger(__name__)


class Https:
    def __init__(self, connection_pooling, endpoint: Endpoint, backend: Backends):
        self.endpoint = endpoint
        self.backend = backend
        self.connection_pooling = connection_pooling
        self.trace_config = TraceHandlers(
            enable_logging=True, log_level=logging.INFO, logger_name="demo.http"
        )

    async def _forge_target_url(
        self, url: str, path: str, prefix: str, query: str | None = None
    ) -> str:
        if url.endswith("$"):
            target_url = url.rstrip("$")
        else:
            path_without_prefix = path.removeprefix(prefix).strip("/")
            target_url = f"{url}/{path_without_prefix}"
        target_url = target_url.strip("/")
        target_url = f"{target_url}?{query}" if query is not None else target_url

        logger.info(f"target URL: {target_url}")
        return target_url

    async def _fetch_and_stream_data(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
        json_data: dict | None = None,
    ):
        timeout = ClientTimeout(
            total=1800,  # 30 minutes - streaming can take a long time
            connect=30,  # 30 seconds - initial connection might be slow
            sock_read=120,  # 2 minutes - chunks can arrive slowly in streams
            sock_connect=15,  # 15 seconds - socket connection
        )

        async with aiohttp.ClientSession(timeout=timeout) as http_session:
            async with http_session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
            ) as response:
                async for chunk in response.content.iter_chunked(8192):
                    yield chunk

    async def https_request(
        self,
        prefix: str,
        url: str,
        connector: TCPConnector,
        trace_config: TraceConfig,
        method: HTTPMethod = HTTPMethod.GET,
        headers: dict[str, str] | None = None,
        auth: Auth | None = None,
        data: str | None = None,
        json_data: str | None = None,
        timeout: int | float | None = None,
    ):
        try:
            headers = headers.copy() if headers else {}
            if auth:
                headers.update(auth.get_headers())

            is_streaming = "accept" in headers and "-stream" in headers.get("accept")
            if is_streaming:
                generator = self._fetch_and_stream_data(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    json_data=json_data,
                )
                return StreamingResponse(
                    generator,
                    media_type="text/octet-stream",
                    headers={
                        "Cache-Control": "no-cache",
                    },
                )
            else:
                try:
                    async with aiohttp.ClientSession(
                        connector=connector,
                        timeout=aiohttp.ClientTimeout(
                            total=60, connect=10, sock_read=15, sock_connect=10
                        ),
                        trace_configs=[trace_config],
                        connector_owner=False,
                    ) as client:
                        https: HTTPS_aiohttp = HTTPS_aiohttp(client_session=client)
                        # https: HTTPS_curl_cffi = HTTPS_curl_cffi(client_session=client)

                        response = await https.request(
                            method=method,
                            url=url,
                            headers=headers,
                            data=data,
                            json_data=json_data,
                        )
                        return response
                except HTTPException as e:
                    logger.exception(f"HTTP exception: {e}")
                    raise e
        finally:
            # for keepalive
            await asyncio.sleep(0.01)

    async def handle_request(self, request: Request, headers: dict) -> Response | Any:
        backend = (
            self.backend.https[0]
            if isinstance(self.backend.https, list)
            else self.backend.https
        )
        target_url = await self._forge_target_url(
            url=backend.url,
            path=request.url.path,
            query=request.url.query,
            prefix=self.endpoint.prefix,
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
            connector=request.app.state.connector,
            trace_config=request.app.state.trace_config,
        )

        if not isinstance(response, StreamingResponse):
            response.headers["content-length"] = str(len(response.body))
        return response
