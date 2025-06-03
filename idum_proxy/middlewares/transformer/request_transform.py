from starlette.types import ASGIApp, Receive, Scope, Send

from antpathmatcher import AntPathMatcher

from idum_proxy.config.models import Config
from idum_proxy.logger import get_logger

logger = get_logger(__name__)


class RequestTransformerMiddleware:
    def __init__(self, app: ASGIApp, config: Config) -> None:
        self.app = app
        self.antpathmatcher = AntPathMatcher()
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        logger.info("Call RequestTransformerMiddleware")

        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        # config = self.idum_proxy.config

        await self.app(scope, receive, send)
