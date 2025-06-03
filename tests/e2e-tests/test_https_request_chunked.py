from idum_proxy import IdumProxy
import pytest
from idum_proxy.config.models import Config
import threading
import httpx
import time
import logging
import socket


@pytest.mark.asyncio
async def test_https_request_chunked():
    config = {
        "version": "1.0",
        "name": "Idum Proxy",
        "server": {"type": "uvicorn"},
        "endpoints": [
            {
                "prefix": "/",
                "match": "**/*",
                "backends": [
                    {
                        "https": {
                            "id": "primary",
                            "url": "https://httpbun.com",
                            "ssl": True,
                            "mode": "stream",
                        }
                    }
                ],
                "upstream": {
                    "proxy": {
                        "enabled": True,
                    }
                },
            }
        ],
    }

    # Initialize the proxy
    idum_proxy: IdumProxy = IdumProxy(config=Config(**config))

    # Start proxy in a separate daemon thread
    proxy_thread = threading.Thread(
        target=idum_proxy.serve, daemon=True, name="IdumProxyThread"
    )
    proxy_thread.start()

    def wait_port_available(host: str, port: int):
        def _socket_test_connection():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)  # Add timeout to avoid blocking indefinitely
                result = s.connect_ex((host, port))
                s.close()
                return result == 0  # 0 means connection successful
            except Exception:
                return False

        while _socket_test_connection():
            logging.info(f"waiting for port {port}")
            time.sleep(1)

    wait_port_available(host="0.0.0.0", port=8080)

    transport = httpx.ASGITransport(app=idum_proxy.app)
    timeout = httpx.Timeout(300.0)  # 5 minutes

    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", timeout=timeout
    ) as client:
        async with client.stream(
            "GET",
            "/drip-lines",
            headers={"Accept": "application/text-stream"},
        ) as response:
            logging.info(f"Status code {response.status_code}")
            chunked = ""
            async for chunk in response.aiter_lines():
                chunked += chunk
                logging.info(f"Lined {chunk}")

    assert chunked == "**********"
