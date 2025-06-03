# Event loop-based connectors (most robust)
import asyncio
import threading
import weakref
from typing import Dict

from aiohttp import TCPConnector


class EventLoopConnectorManager:
    """Manages connectors per event loop"""

    def __init__(self):
        self._connectors: Dict[int, TCPConnector] = {}
        self._lock = threading.Lock()

    def get_connector(self) -> TCPConnector:
        """Get connector for current event loop"""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            # No event loop running, use thread ID
            loop_id = threading.get_ident()

        with self._lock:
            if loop_id not in self._connectors:
                connector = TCPConnector(
                    ssl=True,
                    keepalive_timeout=75,
                    limit=10,
                    limit_per_host=5,
                    # ssl_shutdown_timeout=SSL_SHUTDOWN_TIMEOUT
                )
                self._connectors[loop_id] = connector

                # Cleanup when event loop closes (if possible)
                try:
                    loop = asyncio.get_running_loop()
                    # Use weak reference to avoid circular references
                    weak_manager = weakref.ref(self)

                    def cleanup():
                        manager = weak_manager()
                        if manager and loop_id in manager._connectors:
                            # Note: This is best effort - connector might not be closed properly
                            # if event loop is already closing
                            del manager._connectors[loop_id]

                    loop.add_signal_handler = lambda: None  # Placeholder for cleanup
                except RuntimeError:
                    pass  # No event loop or can't add cleanup

            return self._connectors[loop_id]

    async def cleanup_all(self):
        """Cleanup all connectors"""
        with self._lock:
            for connector in self._connectors.values():
                if not connector.closed:
                    await connector.close()
            self._connectors.clear()


# Global instances (these are SAFE because they create separate connectors per thread/loop)
event_loop_manager = EventLoopConnectorManager()
