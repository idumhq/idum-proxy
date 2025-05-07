import asyncio
from typing import Any, AsyncGenerator
from idum_proxy.protocols.tcp import TCP, TCPConnection
import contextlib


class TLS(TCP):
    """TLS/SSL client for secure TCP communication."""

    def __init__(
        self, ssl_context=None, timeout: float = 30.0, proxy: Any | None = None
    ):
        """Initialize the TLS client.

        Args:
            ssl_context: SSL context for the connection
            timeout: Connection timeout in seconds
            proxy: Optional proxy configuration
        """
        super().__init__(timeout, proxy)
        self.connected = False

        # Create default SSL context if none provided
        if ssl_context is None:
            import ssl

            self.ssl_context = ssl.create_default_context()
        else:
            self.ssl_context = ssl_context

    """"""

    @contextlib.asynccontextmanager
    async def connect(self, host: str, port: int) -> AsyncGenerator[TCPConnection, Any]:
        """Connect to a TLS server.

        Args:
            host: Server hostname or IP address
            port: Server port
        """
        try:
            """
            if self.proxy:
                # Use proxy if configured
                proxy_host, proxy_port = self.proxy.get_tcp_proxy()
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(proxy_host, proxy_port),
                    timeout=self.timeout,
                )
                # Send CONNECT command to proxy
                self._writer.write(f"CONNECT {host}:{port} HTTP/1.1\r\n\r\n".encode())
                await self._writer.drain()

                # Read proxy response
                response = await self._reader.readuntil(b"\r\n\r\n")
                if b"200" not in response:
                    raise ConnectionError(
                        f"Proxy connection failed: {response.decode()}"
                    )

                # Start TLS over the proxy tunnel
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        sock=self._writer.get_extra_info("socket"),
                        ssl=self.ssl_context,
                        server_hostname=host,
                    ),
                    timeout=self.timeout,
                )
            else:
            """
            # Direct TLS connection

            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host,
                    port,
                    ssl=self.ssl_context,
                    server_hostname=host,
                ),
                timeout=self.timeout,
            )

            """
                # Get SSL connection information
                ssl_obj = self._writer.get_extra_info('ssl_object')
                if ssl_obj:
                    print(f"Using cipher: {ssl_obj.cipher()}")
                    print(f"TLS version: {ssl_obj.version()}")
                else:
                    print("Could not get SSL information")

                peercert = self._writer.get_extra_info("peercert")
                print(f"Peer cert: {peercert!r}")

                # Extract peer certificate details
                # peercert = self._writer.get_extra_info('peercert')
                # ssl_object = self._writer.get_extra_info('ssl_object')
                """

            if not await self._check_connection_status(self._reader):
                raise ConnectionError("Connection failed")

            self.logger.info(f"Connected to TLS server at {host}:{port}")

            # Create and yield the connection wrapper
            conn = TCPConnection(
                self._reader, self._writer, ssl_context=self.ssl_context
            )
            yield conn

            self.logger.info(f"Connected to TLS server at {host}:{port}")
        except asyncio.TimeoutError:
            self.logger.error(f"TLS connection timed out after {self.timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"TLS connection error: {str(e)}")
            raise
