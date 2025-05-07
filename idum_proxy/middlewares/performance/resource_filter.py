from http import HTTPStatus

from antpathmatcher import AntPathMatcher
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config


class ResourceFilterMiddleware:
    """
    Performance middleware that filters out requests to specific resources
    to avoid unnecessary processing by the application.
    """

    def __init__(self, app: ASGIApp, config: Config) -> None:
        self.app = app
        self.config = config
        self.antpathmatcher = AntPathMatcher()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        await async_logger.info("Call ResourceFilterMiddleware")

        config = self.config

        if (
            hasattr(config, "middlewares")
            and hasattr(config.middlewares, "performance")
            and hasattr(config.middlewares.performance, "resource_filter")
            and config.middlewares.performance
            and config.middlewares.performance.resource_filter
            and config.middlewares.performance.resource_filter.enabled is True
            and config.middlewares.performance.resource_filter.skip_paths
        ):
            for skip_path in config.middlewares.performance.resource_filter.skip_paths:
                await async_logger.info(f"Call ResourceFilterMiddleware - {skip_path=}")

                if self.antpathmatcher.match(skip_path, scope["path"].lstrip("/")):
                    response = Response(
                        status_code=HTTPStatus.NO_CONTENT  # 204
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
