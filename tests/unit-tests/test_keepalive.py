import platform

import aiohttp
import asyncio
import logging
import time
import socket
import pytest


@pytest.mark.asyncio
async def test_keepalive():
    # Create connector with explicit keepalive settings
    sock_options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]

    # Set platform-specific options
    system = platform.system()
    if system == "Linux":
        sock_options.extend(
            [
                (
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPIDLE,
                    60,
                ),
            ]
        )
        sock_options.extend(
            [
                (
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPINTVL,
                    10,
                ),
            ]
        )
        sock_options.extend(
            [
                (
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPCNT,
                    3,
                ),
            ]
        )
    elif system == "Darwin":  # macOS
        # TCP_KEEPALIVE is available on macOS
        sock_options.extend(
            [
                (
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPALIVE,
                    60,
                ),  # Send keepalive after 60 seconds of idleness
            ]
        )

    connector = aiohttp.TCPConnector(
        limit=10,
        keepalive_timeout=60,  # 60 seconds
        force_close=False,
        enable_cleanup_closed=True,
        # Enable TCP keepalive packets
    )

    # Print the effective keepalive setting
    logging.info(f"Connector keepalive_timeout: {connector._keepalive_timeout}")

    async with aiohttp.ClientSession(connector=connector) as session:
        # First request
        logging.info(f"\n[{time.time()}] Making first request")
        async with session.get("https://httpbin.org/get") as resp:
            logging.info(f"[{time.time()}] Response status: {resp.status}")
            await resp.text()

        # Check active connections
        num_connections = len(connector._conns)
        logging.info(f"Active connections after first request: {num_connections}")
        if num_connections > 0:
            for key, connections in connector._conns.items():
                logging.info(
                    f"Connection pool for {key}: {len(connections)} connections"
                )

        # Wait 30 seconds - should be within keepalive_timeout
        logging.info("Waiting 2 seconds...")
        await asyncio.sleep(2)

        # Check if connections are still active
        num_connections = len(connector._conns)
        logging.info(f"Active connections after waiting: {num_connections}")

        # Second request - should reuse connection if keepalive works
        logging.info(f"\n[{time.time()}] Making second request")
        async with session.get("https://httpbin.org/get") as resp:
            logging.info(f"[{time.time()}] Response status: {resp.status}")
            await resp.text()

        # Check connections again
        num_connections = len(connector._conns)
        logging.info(f"Active connections after second request: {num_connections}")
