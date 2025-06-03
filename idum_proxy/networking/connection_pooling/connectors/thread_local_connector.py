# Thread-local storage (simplest)
import threading

from aiohttp import TCPConnector


class ThreadLocalConnector:
    """Thread-safe connector storage using threading.local()"""

    def __init__(self):
        self._local = threading.local()

    def get_connector(self) -> TCPConnector:
        """Get connector for current thread"""
        if not hasattr(self._local, "connector"):
            self._local.connector = TCPConnector(
                ssl=True,
                keepalive_timeout=75,
                limit=10,
                limit_per_host=5,
                # ssl_shutdown_timeout=SSL_SHUTDOWN_TIMEOUT,
            )
        return self._local.connector

    async def cleanup_current_thread(self):
        """Cleanup connector for current thread"""
        if hasattr(self._local, "connector"):
            await self._local.connector.close()
            delattr(self._local, "connector")


# Global instances (these are SAFE because they create separate connectors per thread/loop)
thread_local_connector = ThreadLocalConnector()
