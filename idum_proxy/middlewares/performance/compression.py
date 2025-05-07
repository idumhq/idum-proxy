from antpathmatcher import AntPathMatcher
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config
from idum_proxy.networking.routing.routing_selector import RoutingSelector


class CompressionMiddleware:
    def __init__(
        self, app: ASGIApp, config: Config, routing_selector: RoutingSelector
    ) -> None:
        self.app = app
        self.config = config
        self.routing_selector = routing_selector
        self.antpathmatcher = AntPathMatcher()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        await async_logger.info("Call CompressionMiddleware")

        request_headers = dict(scope.get("headers", []))
        accept_encoding = request_headers.get(b"accept-encoding", b"").decode()
        # Check if client supports gzip
        if "gzip" not in accept_encoding.lower():
            await self.app(scope, receive, send)
            return

        config = self.config

        request = Request(scope)
        path = request.url.path

        endpoint = self.routing_selector.find_endpoint(request_url_path=path)

        # compression is enabled only for backends of type https
        if (
            hasattr(endpoint.upstream, "backends")
            and hasattr(endpoint.upstream.backends[0], "https")
            and hasattr(config, "middlewares")
            and hasattr(config.middlewares, "performance")
            and hasattr(config.middlewares.performance, "compression")
            and config.middlewares.performance.compression
            and config.middlewares.performance.compression.enabled is True
        ):
            await async_logger.info("Call GZipMiddleware")

            minimum_size = config.middlewares.performance.compression.minimum_size
            compress_level = config.middlewares.performance.compression.compress_level
            if config.middlewares.performance.compression.type == "gzip":
                await GZipMiddleware(
                    app=self.app,
                    minimum_size=minimum_size,
                    compresslevel=compress_level,
                ).__call__(scope, receive, send)
            if config.middlewares.performance.compression.type == "brotli":
                await GZipMiddleware(
                    app=self.app,
                    minimum_size=minimum_size,
                    compresslevel=compress_level,
                ).__call__(scope, receive, send)
            return
        else:
            await self.app(scope, receive, send)
