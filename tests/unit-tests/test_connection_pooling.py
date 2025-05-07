import pytest
from aiohttp import TCPConnector


import aiohttp
import asyncio
import time
import os
import socket
import platform


@pytest.mark.asyncio
async def test_connection_pooling():
    # Create connector with a short keepalive_timeout for demonstration

    class CustomTCPConnector(aiohttp.TCPConnector):
        async def _create_connection(self, req, traces, timeout):
            """Override the connection creation to set socket options."""
            connection = await super()._create_connection(req, traces, timeout)

            # Get the transport
            transport = connection.transport
            if transport is not None:
                sock = transport.get_extra_info("socket")
                if sock is not None:
                    # Enable TCP keepalive
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                    # Set platform-specific options
                    system = platform.system()
                    if system == "Linux":
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)  # type: ignore[attr-defined]
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)  # type: ignore[attr-defined]
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)  # type: ignore[attr-defined]
                    elif system == "Darwin":  # macOS
                        # TCP_KEEPALIVE is available on macOS
                        try:
                            TCP_KEEPALIVE = getattr(socket, "TCP_KEEPALIVE", 0x10)
                            sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 60)  # type: ignore[attr-defined]
                        except OSError as exc:
                            print(f"Failed to set TCP_KEEPALIVE: {exc}")

            return connection

    tcp_connector = TCPConnector(
        keepalive_timeout=1, limit=10, force_close=False, enable_cleanup_closed=True
    )

    print(f"Starting with PID: {os.getpid()}")

    async with aiohttp.ClientSession(connector=tcp_connector) as session:
        # First request - creates a new connection
        print(f"[{time.time()}] Making first request")
        async with session.get(
            "https://httpbin.org/get", headers={"Content-Encoding": "gzip"}
        ) as resp:
            print(f"[{time.time()}] First response received")
            await resp.text()

        # Wait 5 seconds - less than keepalive_timeout
        print(f"[{time.time()}] Waiting 1 second...")
        await asyncio.sleep(0.01)

        # Second request - should reuse the existing connection
        print(f"[{time.time()}] Making second request")
        async with session.get("https://httpbin.org/get") as resp:
            print(f"[{time.time()}] Second response received")
            await resp.text()

        # Wait 15 seconds - more than keepalive_timeout
        print(f"[{time.time()}] Waiting...")
        await asyncio.sleep(1)

        # Third request - should create a new connection since the old one timed out
        print(f"[{time.time()}] Making third request")
        async with session.get("https://httpbin.org/get") as resp:
            print(f"[{time.time()}] Third response received")
            await resp.text()
        await asyncio.sleep(0.01)
