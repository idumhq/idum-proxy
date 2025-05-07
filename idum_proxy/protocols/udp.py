from typing import Any

import asyncio
import logging


class UDP:
    """UDP client for asynchronous datagram communication."""

    def __init__(self, timeout: float = 30.0, proxy: Any | None = None):
        """Initialize the UDP client.

        Args:
            timeout: Operation timeout in seconds
            proxy: Optional proxy configuration
        """
        self.timeout = timeout
        self.proxy = proxy
        self.logger = logging.getLogger(__name__)
        self._transport = None
        self._protocol = None
        self._remote_addr = None
        self._loop = None

    async def connect(self, host: str, port: int) -> None:
        """Create a UDP socket and store the remote address.

        Args:
            host: Remote hostname or IP address
            port: Remote port
        """
        try:
            self._loop = asyncio.get_event_loop()

            # Create datagram endpoint
            class UDPClientProtocol(asyncio.DatagramProtocol):
                def __init__(self, parent):
                    self.parent = parent
                    self.transport = None
                    self.received_data = asyncio.Queue()

                def connection_made(self, transport):
                    self.transport = transport

                def datagram_received(self, data, addr):
                    self.received_data.put_nowait(data)

                def error_received(self, exc):
                    self.parent.logger.error(f"UDP error: {exc}")

                def connection_lost(self, exc):
                    if exc:
                        self.parent.logger.error(f"UDP connection lost: {exc}")

            if self.proxy:
                # If proxy is configured, use SOCKS protocol for UDP
                # Note: UDP proxying is more complex, this is a simplified implementation
                proxy_host, proxy_port = self.proxy.get_udp_proxy()
                transport, protocol = await self._loop.create_datagram_endpoint(
                    lambda: UDPClientProtocol(self),
                    remote_addr=(proxy_host, proxy_port),
                )
                # UDP proxy setup would require additional SOCKS handshake
            else:
                transport, protocol = await self._loop.create_datagram_endpoint(
                    lambda: UDPClientProtocol(self), remote_addr=(host, port)
                )

            self._transport = transport
            self._protocol = protocol
            self._remote_addr = (host, port)

            self.logger.info(f"UDP socket created for {host}:{port}")
        except Exception as e:
            self.logger.error(f"UDP socket creation error: {str(e)}")
            raise

    async def send(self, data: bytes) -> None:
        """Send a UDP datagram.

        Args:
            data: Bytes to send
        """
        if not self._transport:
            raise RuntimeError("UDP socket not created")

        try:
            if self.proxy:
                # For proxy, we might need to encapsulate the packet
                # This is a simplified implementation
                self._transport.sendto(data)
            else:
                self._transport.sendto(data)
        except Exception as e:
            self.logger.error(f"Failed to send datagram: {str(e)}")
            raise

    async def receive(self) -> bytes:
        """Receive a UDP datagram.

        Returns:
            Received bytes
        """
        if not self._protocol:
            raise RuntimeError("UDP socket not created")

        try:
            # Get data from the protocol's queue with timeout
            data = await asyncio.wait_for(
                self._protocol.received_data.get(), timeout=self.timeout
            )
            return data
        except asyncio.TimeoutError:
            self.logger.error(f"UDP receive timed out after {self.timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Failed to receive datagram: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the UDP socket."""
        if self._transport:
            self._transport.close()
            self._transport = None
            self._protocol = None
            self.logger.info("UDP socket closed")
