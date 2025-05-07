from http import HTTPStatus

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from antpathmatcher import AntPathMatcher

from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config


class BotFilterMiddleware:
    def __init__(self, app: ASGIApp, config: Config) -> None:
        self.app = app
        self.antpathmatcher = AntPathMatcher()
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await async_logger.info("Call BotFilterMiddleware")

        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        config = self.config

        if (
            hasattr(config, "middlewares")
            and hasattr(config.middlewares, "security")
            and hasattr(config.middlewares.security, "bot_filter")
            and config.middlewares.security.bot_filter
            and config.middlewares.security.bot_filter.enabled
        ):
            # Extract User-Agent header
            user_agent = None
            for header in scope["headers"]:
                if header[0].decode("latin1").lower() == "user-agent":
                    user_agent = header[1].decode("latin1")
                    break

            if user_agent:
                for bot in config.middlewares.security.bot_filter.blacklist:
                    if self.antpathmatcher.match(bot.user_agent, user_agent):
                        await async_logger.debug(
                            f"BotBlocking - {bot.user_agent=} {user_agent=}"
                        )

                        response = Response(
                            content="Access denied",
                            status_code=HTTPStatus.FORBIDDEN,  # 403
                        )
                        await response(scope, receive, send)
                        return
            else:
                await async_logger.debug(f"BotFilterMiddleware - {user_agent=} is None")
        await self.app(scope, receive, send)
