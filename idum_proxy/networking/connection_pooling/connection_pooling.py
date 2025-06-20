import asyncio
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import ClientTimeout
import time
import uuid

from idum_proxy.logger import get_logger

logger = get_logger(__name__)


class ConnectionPoolingSession:
    def __init__(self, timeout: float):
        self._session = None
        self._session_lock = asyncio.Lock()
        self.connection_reuse_count = 0
        self.connection_create_count = 0
        self.request_count = 0
        self._connection_map = {}
        self.timeout = timeout
        self.tcp_connector = None

    async def _on_request_start(self, session, context, params):
        request_id = str(uuid.uuid4())[:8]
        context.request_id = request_id
        context.start_time = time.time()
        self.request_count += 1
        logger.info(f"Request started: {request_id} - {params.method} {params.url}")

    async def _on_request_end(self, session, context, params):
        duration = time.time() - context.start_time
        logger.info(f"Request completed: {context.request_id} in {duration:.3f}s")
        logger.info(
            f"Stats - Requests: {self.request_count}, "
            f"Connections created: {self.connection_create_count}, "
            f"Connections reused: {self.connection_reuse_count}"
        )

    async def _on_connection_create_start(self, session, context, params):
        logger.info(
            f"Creating new connection for request: {getattr(context, 'request_id', 'unknown')}"
        )

    async def _on_connection_create_end(self, session, context, params):
        self.connection_create_count += 1
        conn_key = "a"  # id(params.transport)
        self._connection_map[conn_key] = {
            "created_at": time.time(),
            "request_id": getattr(context, "request_id", "unknown"),
            "use_count": 1,
        }
        logger.info(
            f"New connection created: {conn_key} for request {getattr(context, 'request_id', 'unknown')}"
        )

    async def _on_connection_reuse(self, session, context, params):
        self.connection_reuse_count += 1
        conn_key = "a"  # id(params.transport)
        if conn_key in self._connection_map:
            self._connection_map[conn_key]["use_count"] += 1
            age = time.time() - self._connection_map[conn_key]["created_at"]
            use_count = self._connection_map[conn_key]["use_count"]
            logger.info(
                f"Connection reused: {conn_key} for request {getattr(context, 'request_id', 'unknown')} "
                f"(use #{use_count}, age: {age:.1f}s, timeout: {self.timeout})"
            )
        else:
            logger.info(f"Reusing untracked connection: {conn_key}")

    @asynccontextmanager
    async def get_session(self):
        """Get the shared client session, creating it if needed."""
        if self._session is None:
            async with self._session_lock:
                if self._session is None:
                    self.tcp_connector = aiohttp.TCPConnector(
                        ssl=True, keepalive_timeout=75, limit=10
                    )
                    trace_config = aiohttp.TraceConfig()
                    trace_config.on_request_start.append(self._on_request_start)
                    trace_config.on_request_end.append(self._on_request_end)
                    trace_config.on_connection_create_start.append(
                        self._on_connection_create_start
                    )
                    trace_config.on_connection_create_end.append(
                        self._on_connection_create_end
                    )
                    trace_config.on_connection_reuseconn.append(
                        self._on_connection_reuse
                    )

                    # the timeout of the session must be different if it's a chuncked or a standard http call
                    # chuncked needs a long call

                    """
                    if is_streaming:
                        # STREAMING: Longer timeouts for slow/large data transfers
                        timeout = ClientTimeout(
                            total=1800,  # 30 minutes - streaming can take a long time
                            connect=30,  # 30 seconds - initial connection might be slow
                            sock_read=120,  # 2 minutes - chunks can arrive slowly in streams
                            sock_connect=15  # 15 seconds - socket connection
                        )
                    else:
                    """

                    # API: Shorter timeouts for fast responses
                    timeout = ClientTimeout(
                        total=60,  # 1 minute - APIs should respond quickly
                        connect=10,  # 10 seconds - fast connection expected
                        sock_read=15,  # 15 seconds - data should arrive quickly
                        sock_connect=10,  # 10 seconds - socket connection
                    )

                    self._session = aiohttp.ClientSession(
                        connector=self.tcp_connector,
                        trace_configs=[trace_config],
                        timeout=timeout,
                    )

        try:
            yield self._session
        except Exception as e:
            # Handle any session-related errors
            logger.error(f"Session error: {e}")
            logger.exception(e)
            raise

    async def close(self):
        """Close the session when shutting down."""
        if self._session is not None:
            await self._session.close()
            self._session = None
        if self.tcp_connector is not None:
            await self.tcp_connector.close()
            self.tcp_connector = None


class ConnectionPooling:
    def __init__(self):
        self.connection_pool_sessions: dict[str, ConnectionPoolingSession] = {}

    def append_new_client_session(self, key, timeout):
        self.connection_pool_sessions[key] = ConnectionPoolingSession(timeout)

    async def close(self):
        for key in self.connection_pool_sessions:
            await self.connection_pool_sessions[key].close()
