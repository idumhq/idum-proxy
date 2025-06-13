# Singleton with proper isolation
import threading

from aiohttp import TCPConnector

from idum_proxy.networking.connection_pooling.connectors.event_loop_connector_manager import (
    EventLoopConnectorManager,
)


class SafeConnectorSingleton:
    """Singleton that maintains separate connectors per thread/loop"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._manager = EventLoopConnectorManager()
        return cls._instance

    def get_connector(self) -> TCPConnector:
        return self._manager.get_connector()

    async def cleanup(self):
        await self._manager.cleanup_all()


# Global instances (these are SAFE because they create separate connectors per thread/loop)
safe_singleton = SafeConnectorSingleton()
