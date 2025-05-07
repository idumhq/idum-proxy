from http import HTTPStatus

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


from antpathmatcher import AntPathMatcher
from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config


class IpFilterMiddleware:
    def __init__(self, app: ASGIApp, config: Config) -> None:
        self.app = app
        self.antpathmatcher = AntPathMatcher()
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await async_logger.info("Call IpFilterMiddleware")

        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        config = self.config

        if (
            hasattr(config, "middlewares")
            and hasattr(config.middlewares, "security")
            and hasattr(config.middlewares.security, "ip_filter")
            and config.middlewares.security
            and config.middlewares.security.ip_filter
            and config.middlewares.security.ip_filter.enabled
        ):
            client_ip = scope.get("client")[0] if scope.get("client") else None  # type: ignore

            if client_ip:
                for blocking_ip in config.middlewares.security.ip_filter.blacklist:
                    if self.antpathmatcher.match(blocking_ip, client_ip):
                        await async_logger.info(
                            f"IpFilter - {blocking_ip=} {client_ip=}"
                        )
                        response = Response(
                            content="Access denied",
                            status_code=HTTPStatus.FORBIDDEN,  # 403
                        )
                        await response(scope, receive, send)
                        return
            else:
                await async_logger.warning(f"IpFilter - {client_ip=} is None")
        await self.app(scope, receive, send)
