# Demonstration
import logging

import pytest

from idum_proxy.networking.connection_pooling.http_client import HTTPClient
from idum_proxy.networking.connection_pooling.tracing.default_trace_handler import (
    TraceHandlers,
)

# Setup logging to see trace output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

trace_config = TraceHandlers(
    enable_logging=True,
    logger_name="test_http_client",
    log_level=logging.INFO,
)


@pytest.mark.asyncio
async def test_http_client_one_client():
    async with HTTPClient(trace_handlers=trace_config) as client:
        async with client.session.get("https://httpbin.org/get") as resp:
            print(f"{resp.status}")

        async with client.session.get("https://httpbin.org/get") as resp:
            print(f"{resp.status}")


@pytest.mark.asyncio
async def test_http_client_two_clients():
    async with HTTPClient(trace_handlers=trace_config) as client:
        async with client.session.get("https://httpbin.org/get") as resp:
            print(f"{resp.status}")

    async with HTTPClient(trace_handlers=trace_config) as client:
        async with client.session.get("https://httpbin.org/get") as resp:
            print(f"{resp.status}")
