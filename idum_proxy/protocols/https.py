from http import HTTPStatus

import aiohttp
import logging
import asyncio
from typing import Any

from aiohttp import ClientSession
from starlette.responses import JSONResponse, Response


class HTTPS:
    """HTTP/HTTPS client for making asynchronous requests."""

    def __init__(
        self,
        ssl: bool = True,
        timeout: float = 30.0,
        proxy: Any | None = None,
        client_session: ClientSession | None = None,
    ):
        """Initialize the HTTPS client.

        Args:
            ssl: Whether to use SSL verification
            timeout: Request timeout in seconds
            proxy: Optional proxy configuration
        """
        self.ssl = ssl
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.proxy = proxy
        self.client_session = client_session or ClientSession()

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        data: any = None,
        json_data: any = None,
        params: dict | None = None,
    ) -> Response:
        """Make an HTTP/HTTPS request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            headers: Optional request headers
            data: Optional request body
            json_data: Optional JSON request body
            params: Optional URL parameters

        Returns:
            Dictionary containing response data, status and headers
        """
        try:
            async with self.client_session.request(
                method=method,
                url=url,
                ssl=self.ssl,
                headers=headers,
                data=data,
                json=json_data,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                proxy=self.proxy,
                allow_redirects=True,
            ) as response:
                if "Content-Type" not in response.headers:
                    return Response(status_code=HTTPStatus.NO_CONTENT.value)

                elif "application/json" in response.headers["Content-Type"]:
                    content = await response.json()
                    _headers = response.headers.copy()

                    if "Content-Length" in _headers:
                        del _headers["Content-Length"]

                    return JSONResponse(
                        content=content,
                        status_code=response.status,
                        media_type="application/json",
                        # headers=response.headers,
                    )

                elif "text/" in response.headers["Content-Type"]:
                    content = await response.text()
                    _headers = response.headers.copy()

                    if "Content-Length" in _headers:
                        del _headers["Content-Length"]

                    return Response(
                        content=content,
                        status_code=response.status,
                        media_type=response.headers["Content-Type"],
                        # headers=response.headers,
                    )

                elif "application/" in response.headers["Content-Type"]:
                    # application/octet-stream, application/jar, ...
                    """
                    async def stream_generator():
                        async for chunk in response.content.iter_chunked(8192):
                            yield chunk
                    
                    return StreamingResponse(
                        stream_generator(),
                        status_code=response.status,
                        media_type=response.headers.get("Content-Type"),
                        headers=headers,
                    )
                    """
                    content = await response.read()
                    return Response(
                        content=content,
                        status_code=response.status,
                        media_type=response.headers.get("Content-Type"),
                        headers=response.headers,
                    )

                return Response(status_code=HTTPStatus.NO_CONTENT.value)

        except aiohttp.ClientError as e:
            self.logger.error(f"Request error: {str(e)}")
            raise
        except asyncio.TimeoutError:
            self.logger.error(f"Request timed out after {self.timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise
