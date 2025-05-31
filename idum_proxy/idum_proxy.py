import contextlib
from idum_proxy import __version__
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from idum_proxy.config.models import Endpoint, Config
from idum_proxy.middlewares.content_length_middleware import ContentLengthMiddleware
import asyncio
import gunicorn.app.base
from idum_proxy.async_logger import async_logger

from idum_proxy.middlewares.performance.resource_filter import (
    ResourceFilterMiddleware,
)
from idum_proxy.middlewares.performance.caching.in_memory import (
    InMemoryCacheMiddleware,
)

from idum_proxy.middlewares.performance.caching.in_file import (
    InFileCacheMiddleware,
)

from idum_proxy.middlewares.performance.compression import (
    CompressionMiddleware,
)
from idum_proxy.middlewares.security.bot_filter import (
    BotFilterMiddleware,
)
from idum_proxy.middlewares.security.ip_filter import (
    IpFilterMiddleware,
)

from http import HTTPStatus, HTTPMethod

from idum_proxy.middlewares.transformer.response_transform import (
    ResponseTransformerMiddleware,
)

from idum_proxy.config.loader import get_file_config
from idum_proxy.networking.connection_pooling.connection_pooling import (
    ConnectionPooling,
)

from idum_proxy.networking.routing.routing_selector import RoutingSelector
import httpx

from idum_proxy.upstreams.backends.file_system.file import File
from idum_proxy.upstreams.backends.system.command import Command
from idum_proxy.upstreams.backends.http.echo import Echo
from idum_proxy.upstreams.backends.http.https import Https
from idum_proxy.upstreams.backends.http.mock import Mock
from idum_proxy.upstreams.backends.http.redirect import Redirect
from idum_proxy.upstreams.backends.system.scheduler import Scheduler
from idum_proxy.utils.utils import check_path


class ProxyHandlerFactory:
    _handlers = {
        "command": Command,
        "echo": Echo,
        "redirect": Redirect,
        "mock": Mock,
        "https": Https,
        "file": File,
        "scheduler": Scheduler,
    }

    @classmethod
    async def create_and_handle(
        cls, backend, endpoint, request, headers, connection_pooling
    ):
        for attr_name, handler_class in cls._handlers.items():
            if hasattr(backend, attr_name) and getattr(backend, attr_name):
                handler = handler_class(
                    connection_pooling=connection_pooling,
                    endpoint=endpoint,
                    backend=backend,
                )
                return await handler.handle_request(request=request, headers=headers)

        raise ValueError("No valid handler found for backend")


async def handle_request(
    routing_selector, config, app, request: Request, connection_pooling
):
    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers.pop("accept-encoding", None)
    headers.pop("user-agent", None)

    headers["user-agent"] = f"python-idum-proxy/{__version__}"

    # headers["content-type"] = "application/json"
    try:
        endpoint: Endpoint = routing_selector.find_endpoint(
            request_url_path=request.url.path
        )

        upstream = endpoint.upstream

        if (
            hasattr(upstream, "proxy")
            and upstream.proxy is not None
            and upstream.proxy.enabled is True
        ):
            # select the backend
            backend = (
                endpoint.backends[0]
                if isinstance(endpoint.backends, list)
                else endpoint.backends
            )
            await async_logger.debug(f"{upstream=} - {backend=}")

            return await ProxyHandlerFactory.create_and_handle(
                backend, endpoint, request, headers, connection_pooling
            )

        if (
            hasattr(upstream, "virtual")
            and upstream.virtual is not None
            and upstream.virtual.enabled is True
        ):
            sources = upstream.virtual.sources

            if upstream.virtual.strategy == "first-match":
                endpoints_by_identifier = {
                    endpoint.identifier: endpoint for endpoint in config.endpoints
                }
                transport = httpx.ASGITransport(app=app)

                for source in sources:
                    # call local asgi app with the url
                    # source1: http://0.0.0.0:8080/pypi-demo-local
                    # source2: # ex: http://0.0.0.0:8080/pypi-remote-official

                    source_endpoint = endpoints_by_identifier[source]
                    async with httpx.AsyncClient(
                        transport=transport, base_url="http://testserver"
                    ) as client:
                        resource_path = request.url.path.removeprefix(endpoint.prefix)
                        path = source_endpoint.prefix + resource_path

                        if request.url.query:
                            path = f"{request.url.path}?{request.url.query}"

                        r = await client.request(url=path, method=method)
                        if r.status_code != HTTPStatus.OK:
                            continue
                        return Response(
                            status_code=r.status_code,
                            media_type=r.headers["content-type"]
                            if "content-type" in r.headers
                            else "application/text",
                            content=r.text,
                        )
        return Response(
            status_code=HTTPStatus.NOT_FOUND,
            media_type="text/plain",
            content="Not Found",
        )

    except Exception as e:
        await async_logger.error(f"Error: {e}")
        await async_logger.exception(e)
        if isinstance(e, asyncio.TimeoutError):
            return Response(
                content="Request timed out",
                status_code=HTTPStatus.REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
        return Response(
            content=str(e),
            status_code=500,
            headers={"Content-Type": "application/json"},
        )


async def websocket_proxy(websocket: WebSocket, channel: str):
    """WebSocket proxy with channel support"""
    await websocket.accept()

    try:
        # Connect to backend WebSocket
        """
        backend_ws_url = f"ws://backend-ws.com/channels/{channel}"

        async with httpx.AsyncClient() as client:
            # In real implementation, you'd use websockets library
            # This is simplified for demonstration
            while True:
                # Receive from client
                data = await websocket.receive_text()

                # Forward to backend (simplified)
                # In practice, maintain persistent connection to backend

                # Echo back for demo
                await websocket.send_text(f"Channel {channel}: {data}")
        """
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


class IdumProxy:
    def __init__(self, config_file: str | None = None, config: Config | None = None):
        self.app = None
        self.proxy_baseurl = "http://127.0.0.1:8091"

        self.config = get_file_config(config_file) if config_file else config
        self.routing_selector = RoutingSelector(self.config)
        self.connection_pooling = ConnectionPooling()

        for endpoint in self.config.endpoints:
            self.connection_pooling.append_new_client_session(
                key=endpoint.prefix, timeout=endpoint.timeout
            )

    """
    @contextlib.asynccontextmanager
    async def tcp_connect(self, host: str, port: int, timeout: float = 30.0):
        tcp = TCP(timeout=timeout)
        async with tcp.connect(host=host, port=port) as conn:
            yield conn

    @contextlib.asynccontextmanager
    async def tls_connect(
        self,
        host: str,
        port: int,
        ssl_context: Any | None = None,
        timeout: float = 30.0,
    ):
        tls = TLS(timeout=timeout, ssl_context=ssl_context)
        async with tls.connect(host=host, port=port) as conn:
            yield conn
    """

    def serve(self, host: str = "0.0.0.0", port: int = 8080):
        async def health_check(request):
            return JSONResponse({"status": "healthy"})

        async def handle_all_methods(request: Request):
            return await handle_request(
                self.routing_selector,
                self.config,
                self.app,
                request,
                self.connection_pooling,
            )

        def configure_middlewares():
            # skips

            # backends
            # app.add_middleware(CircuitBreakingMiddleware, idum_proxy=idum_proxy)  # type: ignore
            self.app.add_middleware(ContentLengthMiddleware)  # type: ignore

            if (
                check_path(self.config, "middlewares.performance.cache.memory.enabled")
                and self.config.middlewares.performance.cache.memory.enabled is True
            ):
                self.app.add_middleware(InMemoryCacheMiddleware, config=self.config)  # type: ignore

            if (
                check_path(self.config, "middlewares.performance.cache.file.enabled")
                and self.config.middlewares.performance.cache.file.enabled is True
            ):
                self.app.add_middleware(InFileCacheMiddleware, config=self.config)  # type: ignore

            if (
                check_path(self.config, "middlewares.security.bot_filter.enabled")
                and self.config.middlewares.security.bot_filter.enabled is True
            ):
                self.app.add_middleware(BotFilterMiddleware, config=self.config)  # type: ignore

            if (
                check_path(self.config, "middlewares.security.ip_filter.enabled")
                and self.config.middlewares.security.ip_filter.enabled is True
            ):
                self.app.add_middleware(IpFilterMiddleware, config=self.config)  # type: ignore

            if (
                check_path(
                    self.config, "middlewares.performance.resource_filter.enabled"
                )
                and self.config.middlewares.performance.resource_filter.enabled is True
            ):
                self.app.add_middleware(ResourceFilterMiddleware, config=self.config)  # type: ignore

            self.app.add_middleware(
                CompressionMiddleware,
                config=self.config,  # type: ignore
                routing_selector=self.routing_selector,
            )  # type: ignore

            self.app.add_middleware(
                ResponseTransformerMiddleware, routing_selector=self.routing_selector
            )  # type: ignore

            # from aioprometheus import MetricsMiddleware  # type: ignore
            # from aioprometheus.asgi.starlette import metrics  # type: ignore

            # app.add_middleware(MetricsMiddleware)  # type: ignore
            # app.add_route("/metrics", metrics)

            self.app.user_middleware.reverse()

        """
        async def startup() -> None:
            # Load scheduler configuration
            config = {
                "job_history": {
                    "storage_type": "file",
                    "path": ".data/scheduler/job_history",
                    "retention_hours": 168,
                },
                "cron_jobs": {
                    "cache_cleanup": {
                        "schedule": "0 2 * * *",
                        "command": "find .cache -type f -mtime +7 -delete",
                        "description": "Daily cache cleanup at 2 AM",
                    },
                    "log_rotation": {
                        "schedule": "0 0 * * 0",
                        "command": "logrotate /etc/logrotate.d/idum-proxy",
                        "description": "Weekly log rotation",
                    },
                },
                "job_history_retention": 168,
            }

            self.scheduler_service = SchedulerService(config)
            await self.scheduler_service.start()
            logging.info("Application started with scheduler")
        """
        routes = [
            Route("/health", health_check, methods=["GET"]),
            Route(
                "/{path:path}",
                handle_all_methods,
                methods=[
                    HTTPMethod.GET,
                    HTTPMethod.POST,
                    HTTPMethod.PUT,
                    HTTPMethod.DELETE,
                    HTTPMethod.PATCH,
                ],
            ),
            WebSocketRoute("/ws/{channel}", websocket_proxy),
        ]

        @contextlib.asynccontextmanager
        async def lifespan(app):
            # Startup
            print("Application starting...")
            yield
            # Shutdown
            print("Application shutting down...")

        self.app = Starlette(
            routes=routes, lifespan=lifespan
        )  # ,) on_shutdown=[shutdown])
        configure_middlewares()

        DEFAULT_SERVER = "gunicorn"
        DEFAULT_NB_WORKERS = 5

        server = DEFAULT_SERVER
        nb_workers = DEFAULT_NB_WORKERS

        if check_path(self.config, "server.type"):
            server = self.config.server.type

        if server == "local":
            return

        if server == "gunicorn":
            if check_path(self.config, "server.workers"):
                nb_workers = self.config.server.workers

            class StandaloneApplication(gunicorn.app.base.BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            options = {
                "bind": f"{host}:{port}",
                "workers": nb_workers,
                "worker_class": "uvicorn.workers.UvicornWorker",
            }
            StandaloneApplication(self.app, options).run()
        else:
            import uvicorn

            uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    idum_proxy: IdumProxy = IdumProxy(config_file="idum_proxy/default.json")
    idum_proxy.serve()
