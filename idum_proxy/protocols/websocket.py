import aiohttp
import logging
import asyncio


class WebSocket:
    """WebSocket client for asynchronous communication."""

    def __init__(self, ssl: bool = True, timeout: float = 30.0):
        """Initialize the WebSocket client.

        Args:
            ssl: Whether to use SSL verification
            timeout: Connection timeout in seconds
            proxy: Optional proxy configuration
        """
        self.ssl = ssl
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._ws = None

    async def connect(self, url: str, headers: dict = None) -> None:
        """Connect to a WebSocket server.

        Args:
            url: WebSocket URL (ws:// or wss://)
            headers: Optional connection headers
        """
        try:
            session = aiohttp.ClientSession()
            self._ws = await session.ws_connect(
                url,
                ssl=self.ssl,
                headers=headers,
                timeout=self.timeout,
            )
            self.logger.info(f"Connected to WebSocket at {url}")
        except aiohttp.ClientError as e:
            self.logger.error(f"WebSocket connection error: {str(e)}")
            raise
        except asyncio.TimeoutError:
            self.logger.error(f"WebSocket connection timed out after {self.timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise

    async def send(self, data: any) -> None:
        """Send data through the WebSocket connection.

        Args:
            data: Data to send (string, bytes or JSON-serializable object)
        """
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        try:
            if isinstance(data, dict):
                await self._ws.send_json(data)
            elif isinstance(data, str):
                await self._ws.send_str(data)
            elif isinstance(data, bytes):
                await self._ws.send_bytes(data)
            else:
                raise TypeError(f"Unsupported data type: {type(data)}")
        except Exception as e:
            self.logger.error(f"Failed to send data: {str(e)}")
            raise

    async def receive(self) -> dict:
        """Receive data from the WebSocket connection.

        Returns:
            Dictionary with message type and data
        """
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        try:
            msg = await self._ws.receive(timeout=self.timeout)

            if msg.type == aiohttp.WSMsgType.TEXT:
                return {"type": "text", "data": msg.data}
            elif msg.type == aiohttp.WSMsgType.BINARY:
                return {"type": "binary", "data": msg.data}
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                return {"type": "closed", "data": None}
            elif msg.type == aiohttp.WSMsgType.ERROR:
                return {"type": "error", "data": str(msg.data)}
            else:
                return {"type": "unknown", "data": msg.data}
        except Exception as e:
            self.logger.error(f"Failed to receive data: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            await self._ws._session.close()  # Close the underlying session
            self._ws = None
            self.logger.info("WebSocket connection closed")
