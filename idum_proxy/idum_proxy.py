import contextlib
import logging
from pathlib import Path

import aiohttp

from idum_proxy import __version__
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket
from idum_proxy.config.models import Endpoint, Config
from idum_proxy.logger import get_logger
from idum_proxy.middlewares.content_length_middleware import ContentLengthMiddleware
import asyncio
import gunicorn.app.base
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
from idum_proxy.networking.connection_pooling.connectors.connector_sage_singleton import (
    safe_singleton,
)
from idum_proxy.networking.connection_pooling.connectors.event_loop_connector_manager import (
    event_loop_manager,
)
from idum_proxy.networking.connection_pooling.tracing.default_trace_handler import (
    DefaultTraceHandlers,
    TraceHandlers,
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

logger = get_logger(__name__)


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
            logger.debug(f"{upstream=} - {backend=}")

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
        logger.error(f"Error: {e}")
        logger.exception(e)
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
        async def handle_all_methods(request: Request):
            return await handle_request(
                self.routing_selector,
                self.config,
                self.app,
                request,
                None,
            )

        routes = [
            # Route("/health", health_check, methods=["GET"]),
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

        self.config = get_file_config(config_file) if config_file else config
        if not self.config:
            if config_file:
                logger.info(f"File {config_file} not found")
            self.config = Config(
                **{
                    "version": "1.0",
                    "name": "Default config",
                    "endpoints": [
                        {
                            "prefix": "/",
                            "match": "**/*",
                            "backends": {
                                "https": {
                                    "url": "https://jsonplaceholder.typicode.com/posts"
                                }
                            },
                            "upstream": {"proxy": {"enabled": True}},
                        }
                    ],
                }
            )
        self.routing_selector = RoutingSelector(self.config)

        self.app = Starlette(
            debug=True,
            routes=routes,
        )
        configure_middlewares()
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)

        self.proxy_baseurl = "http://127.0.0.1:8091"

    """
        self.connection_pooling = ConnectionPooling()
        
        for endpoint in self.config.endpoints:
            self.connection_pooling.append_new_client_session(
                key=endpoint.prefix, timeout=endpoint.timeout
            )

    def __del__(self):
        if hasattr(self, "connection_pooling") and hasattr(
            self.connection_pooling, "close"
        ):
            try:
                loop = asyncio.get_running_loop()
                # Create task and let it run
                asyncio.run_coroutine_threadsafe(self.connection_pooling.close(), loop)
            except RuntimeError:
                # No event loop running, try to run synchronously
                try:
                    asyncio.run(self.connection_pooling.close())
                except Exception:
                    # Silently ignore cleanup errors during shutdown
                    pass
    """

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

    async def startup_event(self):
        # Create a TCPConnector
        connector = aiohttp.TCPConnector(
            limit=100, force_close=False, enable_cleanup_closed=False
        )

        trace_handlers = TraceHandlers(
            enable_logging=True, log_level=logging.INFO, logger_name="idum_proxy"
        )

        handlers = DefaultTraceHandlers(trace_handlers)

        # Enable connection tracing
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(handlers.on_request_start)
        trace_config.on_request_end.append(handlers.on_request_end)
        trace_config.on_request_exception.append(handlers.on_request_exception)
        trace_config.on_connection_create_start.append(
            handlers.on_connection_create_start
        )
        trace_config.on_connection_create_end.append(handlers.on_connection_create_end)
        trace_config.on_connection_reuseconn.append(handlers.on_connection_reuseconn)
        trace_config.on_dns_resolvehost_start.append(handlers.on_dns_resolvehost_start)
        trace_config.on_dns_resolvehost_end.append(handlers.on_dns_resolvehost_end)

        connector.trace_config = trace_config

        # Store the connector in the application state
        self.app.state.connector = connector
        self.app.state.trace_config = trace_config

    async def shutdown_event(self):
        if hasattr(self.app.state, "connector") and not self.app.state.connector.closed:
            await self.app.state.connector.close()

    def serve(self, host: str = "0.0.0.0", port: int = 443):
        async def health_check(request):
            return JSONResponse({"status": "healthy"})

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

        @contextlib.asynccontextmanager
        async def lifespan(app):
            # Startup
            print("Application starting...")

            yield
            # Shutdown
            print("Application shutting down...")
            # Cleanup (optional, but good practice)
            await event_loop_manager.cleanup_all()
            await safe_singleton.cleanup()

        DEFAULT_SERVER = "gunicorn"
        DEFAULT_NB_WORKERS = 5

        server = DEFAULT_SERVER
        nb_workers = DEFAULT_NB_WORKERS

        if check_path(self.config, "server.type"):
            server = self.config.server.type

        if server == "local":
            return

        if server == "granian":
            logger.info("Starting Granian server")

            from granian import Granian
            from granian.constants import Interfaces, Loops

            # Granian configuration
            granian_app = Granian(
                target=idum_proxy.app,  # Will be set to self.app
                address=host,
                port=port,
                interface=Interfaces.ASGI,
                workers=nb_workers,
                loop=Loops.uvloop,
                # SSL configuration
                ssl_cert=Path("fullchain.pem"),
                ssl_key=Path("privkey.pem"),
                # Performance settings
            )

            # Set the application instance
            # granian_app.target = self.app
            granian_app.serve()

        elif server == "robyn":
            logger.info("Starting Robyn server")
            from robyn import Robyn

            # Create Robyn app instance
            robyn_app = Robyn(__file__)

            @robyn_app.get("/async/str/const", const=True)
            async def async_str_const_get():
                return "async str const get"

            # Mount the Starlette ASGI app
            # robyn_app.include_router(self.app)

            # Configure and start Robyn server
            robyn_app.start(host=host, port=port)
            # workers=nb_workers,
            # ssl_cert=ssl_cert_path.as_posix(),
            # ssl_key=ssl_key_path.as_posix()

        elif server == "gunicorn":
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
                "keyfile": Path(Path(__file__).parent.parent / "privkey.pem").as_posix(),
                "certfile": Path(Path(__file__).parent.parent / "fullchain.pem").as_posix(),
                "ssl_version": 3,  # TLS 1.2+
                "ciphers": "TLSv1.2:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!SRP:!CAMELLIA",
            }
            StandaloneApplication(self.app, options).run()
        elif server == "uvicorn":
            logger.info("Start uvicorn server")

            import uvicorn

            uvicorn.run(
                self.app,
                host=host,
                port=port,
                ssl_keyfile=Path(Path(__file__).parent.parent / "privkey.pem").as_posix(),
                ssl_certfile=Path(Path(__file__).parent.parent / "fullchain.pem").as_posix(),
                ssl_version=3,  # TLS 1.2+
                ssl_ciphers="TLSv1.2:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!SRP:!CAMELLIA",
            )
        else:
            logger.info("Start hypercorn server")
            import asyncio
            from hypercorn.config import Config as HypercornConfig
            from hypercorn.asyncio import serve

            config = HypercornConfig()
            config.bind = [f"{host}:{port}"]
            config.certfile =Path(Path(__file__).parent.parent / "fullchain.pem").as_posix()
            config.keyfile = Path(Path(__file__).parent.parent / "privkey.pem").as_posix()
            config.alpn_protocols = ["h2", "http/1.1"]  # Default priority
            config.h2_max_concurrent_streams = 100  # Default is 100
            config.h2_max_frame_size = 16384  # Default is 16KB

            asyncio.run(serve(self.app, config))


if __name__ == "__main__":
    source_dir = Path(__file__).parent
    config_path = source_dir / "default.json"

    idum_proxy: IdumProxy = IdumProxy(config_file=config_path.as_posix())
    idum_proxy.serve()
