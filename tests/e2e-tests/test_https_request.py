from idum_proxy import IdumProxy
import pytest
from idum_proxy.config.models import Config
import threading
import httpx
from http import HTTPStatus
import time
import logging
import socket


@pytest.mark.asyncio
async def test_https_request():
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
                            "url": "https://jsonplaceholder.typicode.com/posts",
                            "ssl": True,
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
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/1")
        assert response.status_code == HTTPStatus.OK
        assert response.json()["id"] == 1

        response = await client.get("/20")
        assert response.status_code == HTTPStatus.OK
        assert response.json()["id"] == 20
