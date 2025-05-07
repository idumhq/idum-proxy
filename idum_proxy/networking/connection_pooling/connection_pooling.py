import asyncio
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import ClientTimeout
import time
import uuid

from idum_proxy.async_logger import async_logger


class ConnectionPoolingSession:
    def __init__(self, timeout: float):
        self._session = None
        self._session_lock = asyncio.Lock()
        self.connection_reuse_count = 0
        self.connection_create_count = 0
        self.request_count = 0
        self._connection_map = {}
        self.timeout = timeout

    async def _on_request_start(self, session, context, params):
        request_id = str(uuid.uuid4())[:8]
        context.request_id = request_id
        context.start_time = time.time()
        self.request_count += 1
        await async_logger.info(
            f"Request started: {request_id} - {params.method} {params.url}"
        )

    async def _on_request_end(self, session, context, params):
        duration = time.time() - context.start_time
        await async_logger.info(
            f"Request completed: {context.request_id} in {duration:.3f}s"
        )
        await async_logger.info(
            f"Stats - Requests: {self.request_count}, "
            f"Connections created: {self.connection_create_count}, "
            f"Connections reused: {self.connection_reuse_count}"
        )

    async def _on_connection_create_start(self, session, context, params):
        await async_logger.info(
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
        await async_logger.info(
            f"New connection created: {conn_key} for request {getattr(context, 'request_id', 'unknown')}"
        )

    async def _on_connection_reuse(self, session, context, params):
        self.connection_reuse_count += 1
        conn_key = "a"  # id(params.transport)
        if conn_key in self._connection_map:
            self._connection_map[conn_key]["use_count"] += 1
            age = time.time() - self._connection_map[conn_key]["created_at"]
            use_count = self._connection_map[conn_key]["use_count"]
            await async_logger.info(
                f"Connection reused: {conn_key} for request {getattr(context, 'request_id', 'unknown')} "
                f"(use #{use_count}, age: {age:.1f}s, timeout: {self.timeout})"
            )
        else:
            await async_logger.info(f"Reusing untracked connection: {conn_key}")

    @asynccontextmanager
    async def get_session(self):
        """Get the shared client session, creating it if needed."""
        if self._session is None:
            async with self._session_lock:
                if self._session is None:
                    tcp_connector = aiohttp.TCPConnector(
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

                    self._session = aiohttp.ClientSession(
                        connector=tcp_connector,
                        trace_configs=[trace_config],
                        timeout=ClientTimeout(total=5, sock_connect=30),
                    )

        try:
            yield self._session
        except Exception as e:
            # Handle any session-related errors
            await async_logger.error(f"Session error: {e}")
            await async_logger.exception(e)
            raise

    async def close(self):
        """Close the session when shutting down."""
        if self._session is not None:
            await self._session.close()
            self._session = None


class ConnectionPooling:
    def __init__(self):
        self.connection_pool_sessions: dict[str, ConnectionPoolingSession] = {}

    def append_new_client_session(self, key, timeout):
        self.connection_pool_sessions[key] = ConnectionPoolingSession(timeout)

    async def close(self):
        for key in self.connection_pool_sessions:
            await self.connection_pool_sessions[key].close()
