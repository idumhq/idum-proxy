from contextvars import ContextVar

from aiohttp import TCPConnector


def get_context_connector() -> TCPConnector:
    """Get connector from async context"""
    connector = _connector_context.get()
    if connector is None:
        connector = TCPConnector(
            ssl=True,
            keepalive_timeout=75,
            limit=10,
            limit_per_host=5,
            # ssl_shutdown_timeout=SSL_SHUTDOWN_TIMEOUT
        )
        _connector_context.set(connector)
    return connector


# ContextVar for async contexts (recommended for async apps)
_connector_context: ContextVar[TCPConnector | None] = ContextVar(
    "connector", default=None
)
