import aiohttp
from aiohttp import ClientTimeout, TCPConnector, TraceConfig

from idum_proxy.networking.connection_pooling.connectors.connector_sage_singleton import (
    safe_singleton,
)
from idum_proxy.networking.connection_pooling.connectors.context_connector import (
    get_context_connector,
)
from idum_proxy.networking.connection_pooling.connectors.event_loop_connector_manager import (
    event_loop_manager,
)
from idum_proxy.networking.connection_pooling.connectors.thread_local_connector import (
    thread_local_connector,
)
from idum_proxy.networking.connection_pooling.tracing.default_trace_handler import (
    DefaultTraceHandlers,
    TraceHandlers,
)


# ❌ DANGEROUS - DON'T DO THIS:
# global_connector = TCPConnector()  # Will cause crashes!


class HTTPClient:
    """HTTP client with safe connector management and tracing"""

    def __init__(
        self,
        connector_strategy: str = "context_var",
        trace_handlers: TraceHandlers | None = None,
        tcp_connector: TCPConnector = None,
    ):
        """
        connector_strategy options:
        - "dedicated": Each client gets its own connector
        - "thread_local": One connector per thread using threading.local()
        - "context_var": One connector per async context using ContextVar
        - "event_loop": One connector per event loop (most robust)
        - "singleton": Global singleton with per-thread/loop isolation
        """
        self.connector_strategy = connector_strategy
        self.tcp_connector: TCPConnector = tcp_connector
        self.timeout: ClientTimeout | None = None
        self._session: aiohttp.ClientSession | None = None
        self._owns_connector = False
        self.trace_handlers = trace_handlers
        self._trace_config: TraceConfig | None = None

    def _create_trace_config(self) -> TraceConfig | None:
        """Create trace config if handlers are provided"""
        if self.trace_handlers is None:
            return None

        handlers = DefaultTraceHandlers(self.trace_handlers)

        trace_config = TraceConfig()
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

        return trace_config

    async def _setup_resources(self):
        """Setup connector based on strategy"""
        if self.tcp_connector is None:
            if self.connector_strategy == "dedicated":
                self.tcp_connector = TCPConnector(
                    ssl=True, keepalive_timeout=75, limit=10
                )
                # ssl_shutdown_timeout=SSL_SHUTDOWN_TIMEOUT)
                self._owns_connector = True

            elif self.connector_strategy == "thread_local":
                self.tcp_connector = thread_local_connector.get_connector()
                self._owns_connector = False

            elif self.connector_strategy == "context_var":
                self.tcp_connector = get_context_connector()
                self._owns_connector = False

            elif self.connector_strategy == "event_loop":
                self.tcp_connector = event_loop_manager.get_connector()
                self._owns_connector = False

            elif self.connector_strategy == "singleton":
                self.tcp_connector = safe_singleton.get_connector()
                self._owns_connector = False

            else:
                raise ValueError(
                    f"Invalid connector_strategy: {self.connector_strategy}"
                )

            self.timeout = ClientTimeout(
                total=60, connect=10, sock_read=15, sock_connect=10
            )
            self._trace_config = self._create_trace_config()

    async def __aenter__(self):
        await self._setup_resources()

        trace_configs = [self._trace_config] if self._trace_config else []

        self._session = aiohttp.ClientSession(
            connector=self.tcp_connector,
            timeout=self.timeout,
            trace_configs=trace_configs,
            connector_owner=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            raise RuntimeError("Session not available. Use 'async with HTTPClient()'")
        return self._session
