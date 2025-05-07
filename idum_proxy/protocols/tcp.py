import contextlib
from typing import Any

import asyncio
import logging


class TCPConnection:
    """TCP connection wrapper for use with async context managers."""

    def __init__(self, reader, writer, ssl_context: Any | None = None):
        """Initialize with StreamReader and StreamWriter."""
        self.reader = reader
        self.writer = writer
        self.logger = logging.getLogger(__name__)
        self.ssl_context = ssl_context

    async def send(self, data: bytes) -> bytes:
        """Send data and return the response.

        Args:
            data: Bytes to send

        Returns:
            Response bytes
        """
        try:
            self.writer.write(data)
            await self.writer.drain()

            # Read response
            response = await self.reader.read(65536)
            return response
        except Exception as e:
            self.logger.error(f"Failed to send/receive data: {e}")
            raise

    async def receive(self, size: int = 65536, timeout: float = None) -> bytes:
        """Receive data from the TCP connection.

        Args:
            size: Maximum number of bytes to read
            timeout: Read timeout in seconds, None for no timeout

        Returns:
            Received bytes
        """
        try:
            if timeout is not None:
                return await asyncio.wait_for(
                    self.reader.read(size),
                    timeout=timeout,
                )
            else:
                return await self.reader.read(size)
        except asyncio.TimeoutError:
            self.logger.error(f"Receive timed out after {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Failed to receive data: {e}")
            raise

    async def receive_exactly(self, size: int, timeout: float | None = None) -> bytes:
        """Receive exactly the specified number of bytes.

        Args:
            size: Exact number of bytes to read
            timeout: Read timeout in seconds, None for no timeout

        Returns:
            Received bytes
        """
        try:
            if timeout is not None:
                return await asyncio.wait_for(
                    self.reader.readexactly(size), timeout=timeout
                )
            else:
                return await self.reader.readexactly(size)
        except asyncio.IncompleteReadError as e:
            # Connection closed or EOF before receiving all bytes
            self.logger.error(
                f"Incomplete read: requested {size} bytes, got {len(e.partial)} bytes"
            )
            return e.partial
        except asyncio.TimeoutError:
            self.logger.error(f"Receive timed out after {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Failed to receive data: {e}")
            raise

    async def receive_until(
        self, separator: bytes, timeout: float | None = None
    ) -> bytes:
        """Receive data until a separator is found.

        Args:
            separator: Bytes sequence that separates chunks
            timeout: Read timeout in seconds, None for no timeout

        Returns:
            Received bytes including the separator
        """
        try:
            if timeout is not None:
                return await asyncio.wait_for(
                    self.reader.readuntil(separator), timeout=timeout
                )
            else:
                return await self.reader.readuntil(separator)
        except asyncio.IncompleteReadError as e:
            # Connection closed or EOF before finding separator
            self.logger.error(
                f"Incomplete read: separator not found, got {len(e.partial)} bytes"
            )
            return e.partial
        except asyncio.LimitOverrunError as e:
            # Buffer limit exceeded before finding separator
            self.logger.error("Buffer limit exceeded while looking for separator")
            # Read and return what's available
            return await self.reader.read(e.consumed + self.reader._limit)
        except asyncio.TimeoutError:
            self.logger.error(f"Receive timed out after {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Failed to receive data: {e}")
            raise

    async def send_only(self, data: bytes) -> None:
        """Send data without waiting for a response.

        Args:
            data: Bytes to send
        """
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            self.logger.error(f"Failed to send data: {e}")
            raise

    async def close(self):
        """Close the connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.logger.info("TCP connection closed")


class TCP:
    """TCP client for asynchronous socket communication."""

    def __init__(self, timeout: float = 30.0, proxy: Any | str = None):
        """Initialize the TCP client.

        Args:
            timeout: Connection timeout in seconds
            proxy: Optional proxy configuration
        """
        self.timeout = timeout
        self.proxy = proxy
        self.logger = logging.getLogger(__name__)

    @contextlib.asynccontextmanager
    async def connect(self, host: str, port: int):
        """Context manager for TCP connections.

        Args:
            host: Server hostname or IP address
            port: Server port

        Yields:
            TCPConnection object for sending/receiving data
        """
        reader = None
        writer = None

        try:
            if self.proxy:
                # Use proxy if configured
                proxy_host, proxy_port = self.proxy.get_tcp_proxy()
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(proxy_host, proxy_port),
                    timeout=self.timeout,
                )
                # Send CONNECT command to proxy
                writer.write(f"CONNECT {host}:{port} HTTP/1.1\r\n\r\n".encode())
                await writer.drain()

                # Read proxy response
                response = await reader.readuntil(b"\r\n\r\n")
                if b"200" not in response:
                    raise ConnectionError(
                        f"Proxy connection failed: {response.decode()}"
                    )
            else:
                # Direct connection
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=self.timeout
                )

            if not await self._check_connection_status(reader):
                raise ConnectionError("Connection failed")

            self.logger.info(f"Connected to TCP server at {host}:{port}")

            # Create and yield the connection wrapper
            conn = TCPConnection(reader, writer)
            yield conn

        except Exception as e:
            self.logger.error(f"TCP connection error: {e}")
            if writer:
                writer.close()
                await writer.wait_closed()
            raise
        finally:
            # Ensure connection is closed if not already
            if writer and not writer.is_closing():
                writer.close()
                await writer.wait_closed()
                self.logger.info("TCP connection closed")

    async def _check_connection_status(self, reader):
        transport = reader._transport
        if transport and transport.is_closing():
            return False
        return True
