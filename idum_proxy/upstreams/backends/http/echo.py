import asyncio
from datetime import datetime, timezone
from http import HTTPStatus
from string import Template

from starlette.requests import Request
from starlette.responses import JSONResponse

from idum_proxy.config.models import Backends, Endpoint


class Echo:
    def __init__(self, connection_pooling, endpoint: Endpoint, backend: Backends):
        self.connection_pooling = connection_pooling
        self.endpoint = endpoint
        self.backend = backend

    def _get_query_params_with_arrays(
        self,
        request: Request,
    ) -> dict[str, str | list[str]]:
        params = {}
        for key, value in request.query_params.multi_items():
            if key in params:
                # Convert to list if not already
                if not isinstance(params[key], list):
                    params[key] = [params[key]]
                params[key].append(value)
            else:
                params[key] = value
        return params

    async def handle_request(self, request: Request, headers: dict):
        await asyncio.sleep(self.backend.echo.response_delay_ms / 1000)

        response_headers = headers.copy() if headers else {}

        headers_added = self.backend.echo.add_headers.copy()
        for key, value in headers_added.items():
            headers_added[key] = Template(value).substitute(
                timestamp=int(datetime.now(timezone.utc).timestamp())
            )
        response_headers.update(headers_added)

        path = request.url.path.removeprefix(self.endpoint.prefix)
        if request.url.query:
            path = f"{path}?{request.url.query}"

        return JSONResponse(
            content={
                "method": request.method,
                "path": path,
                "ip": request.client.host,
                "headers": response_headers,
                "body": (await request.body()).decode(),
                "query_params": self._get_query_params_with_arrays(request),
                "cookies": dict(request.cookies),
            },
            status_code=HTTPStatus.OK,
            headers=response_headers,
        )
