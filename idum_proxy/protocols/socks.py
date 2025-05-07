import asyncio
import socket
import struct
import logging
import ipaddress


class SocksProxy:
    """SOCKS protocol implementation for proxying TCP and UDP connections."""

    SOCKS4 = 4
    SOCKS5 = 5

    # SOCKS command codes
    CMD_CONNECT = 1
    CMD_BIND = 2
    CMD_UDP_ASSOCIATE = 3

    # SOCKS address types
    ATYP_IPV4 = 1
    ATYP_DOMAIN = 3
    ATYP_IPV6 = 4

    def __init__(
        self,
        host: str,
        port: int,
        version: int = 5,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the SOCKS proxy client.

        Args:
            host: Proxy server hostname or IP address
            port: Proxy server port
            version: SOCKS protocol version (4 or 5)
            username: Optional username for authentication
            password: Optional password for authentication
            timeout: Operation timeout in seconds
        """
        self.host = host
        self.port = port
        if version not in (self.SOCKS4, self.SOCKS5):
            raise ValueError(f"Unsupported SOCKS version: {version}")
        self.version = version
        self.username = username
        self.password = password
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    async def create_connection(self, target_host: str, target_port: int) -> tuple:
        """Create a TCP connection through the SOCKS proxy.

        Args:
            target_host: Target server hostname or IP address
            target_port: Target server port

        Returns:
            Tuple of (reader, writer) for the proxied connection
        """
        # Connect to the proxy server
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=self.timeout
            )
        except Exception as e:
            self.logger.error(f"Failed to connect to SOCKS proxy: {e}")
            raise

        try:
            # Perform SOCKS handshake based on version
            if self.version == self.SOCKS5:
                await self._socks5_handshake(reader, writer)
                await self._socks5_connect(reader, writer, target_host, target_port)
            else:  # SOCKS4
                await self._socks4_connect(reader, writer, target_host, target_port)

            self.logger.info(
                f"SOCKS{self.version} connection established to {target_host}:{target_port}"
            )
            return reader, writer

        except Exception as e:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception as e2:
                self.logger.error(f"SOCKS wait closed exception: {e2}")
                pass
            self.logger.error(f"SOCKS handshake failed: {e}")
            raise

    async def _socks5_handshake(self, reader, writer):
        """Perform SOCKS5 initial handshake with authentication if required.

        Args:
            reader: StreamReader for the proxy connection
            writer: StreamWriter for the proxy connection
        """
        # Initial handshake
        if self.username and self.password:
            # With authentication
            writer.write(
                struct.pack("!BBB", self.SOCKS5, 2, 0x00)
            )  # Support no auth and user/pass
            writer.write(struct.pack("!B", 0x02))  # User/pass auth method
            await writer.drain()
        else:
            # No authentication
            writer.write(struct.pack("!BBB", self.SOCKS5, 1, 0x00))  # Support no auth
            await writer.drain()

        # Read server's response
        resp = await reader.readexactly(2)
        version, method = struct.unpack("!BB", resp)

        if version != self.SOCKS5:
            raise ConnectionError(f"Unexpected SOCKS version: {version}")

        if method == 0xFF:
            raise ConnectionError("No acceptable authentication methods")

        # If username/password auth is selected
        if method == 0x02:
            if not self.username or not self.password:
                raise ConnectionError("Proxy requires authentication")

            # Perform username/password authentication
            writer.write(struct.pack("!B", 0x01))  # Auth version
            writer.write(struct.pack("!B", len(self.username)))
            writer.write(self.username.encode())
            writer.write(struct.pack("!B", len(self.password)))
            writer.write(self.password.encode())
            await writer.drain()

            # Read auth response
            auth_resp = await reader.readexactly(2)
            auth_version, status = struct.unpack("!BB", auth_resp)

            if status != 0x00:
                raise ConnectionError("Authentication failed")

    async def _socks5_connect(self, reader, writer, host, port):
        """Send SOCKS5 CONNECT command.

        Args:
            reader: StreamReader for the proxy connection
            writer: StreamWriter for the proxy connection
            host: Target hostname or IP address
            port: Target port
        """
        # Send connect command
        writer.write(
            struct.pack("!BBB", self.SOCKS5, self.CMD_CONNECT, 0x00)
        )  # Version, CMD, Reserved

        # Determine address type and format
        try:
            # Try to parse as IPv4
            addr = ipaddress.IPv4Address(host)
            writer.write(struct.pack("!B", self.ATYP_IPV4))
            writer.write(addr.packed)
        except ipaddress.AddressValueError:
            try:
                # Try to parse as IPv6
                addr = ipaddress.IPv6Address(host)
                writer.write(struct.pack("!B", self.ATYP_IPV6))
                writer.write(addr.packed)
            except ipaddress.AddressValueError:
                # Use domain name
                domain = host.encode("idna")
                writer.write(struct.pack("!B", self.ATYP_DOMAIN))
                writer.write(struct.pack("!B", len(domain)))
                writer.write(domain)

        # Write port
        writer.write(struct.pack("!H", port))
        await writer.drain()

        # Read response
        resp_header = await reader.readexactly(4)
        version, status, _, atyp = struct.unpack("!BBBB", resp_header)

        if version != self.SOCKS5:
            raise ConnectionError(f"Unexpected SOCKS version in response: {version}")

        if status != 0x00:
            error_messages = {
                0x01: "General failure",
                0x02: "Connection not allowed by ruleset",
                0x03: "Network unreachable",
                0x04: "Host unreachable",
                0x05: "Connection refused",
                0x06: "TTL expired",
                0x07: "Command not supported",
                0x08: "Address type not supported",
            }
            error = error_messages.get(status, f"Unknown error (code: {status})")
            raise ConnectionError(f"SOCKS5 server error: {error}")

        # Read and discard the bound address and port
        if atyp == self.ATYP_IPV4:
            await reader.readexactly(4 + 2)  # IPv4 + Port
        elif atyp == self.ATYP_IPV6:
            await reader.readexactly(16 + 2)  # IPv6 + Port
        elif atyp == self.ATYP_DOMAIN:
            domain_len = (await reader.readexactly(1))[0]
            await reader.readexactly(domain_len + 2)  # Domain + Port
        else:
            raise ConnectionError(f"Unsupported address type in response: {atyp}")

    async def _socks4_connect(self, reader, writer, host, port):
        """Send SOCKS4/4a CONNECT command.

        Args:
            reader: StreamReader for the proxy connection
            writer: StreamWriter for the proxy connection
            host: Target hostname or IP address
            port: Target port
        """
        # Determine if we can use SOCKS4 or need SOCKS4a (for hostnames)
        try:
            # Try to parse as IPv4
            addr = ipaddress.IPv4Address(host)
            ip_bytes = addr.packed
            domain = b""
            use_socks4a = False
        except ipaddress.AddressValueError:
            # Need to use SOCKS4a for non-IPv4 addresses
            ip_bytes = bytes([0, 0, 0, 1])  # 0.0.0.1 placeholder
            domain = host.encode("idna") + b"\x00"
            use_socks4a = True

            if self.version != self.SOCKS4:
                self.logger.warning("Forcing SOCKS4a for hostname resolution")

        # Build and send request
        writer.write(struct.pack("!BBH", self.SOCKS4, self.CMD_CONNECT, port))
        writer.write(ip_bytes)

        # User ID field (empty or username if provided)
        if self.username:
            writer.write(self.username.encode() + b"\x00")
        else:
            writer.write(b"\x00")

        # For SOCKS4a, append the hostname
        if use_socks4a:
            writer.write(domain)

        await writer.drain()

        # Read response
        resp = await reader.readexactly(8)
        version, status = resp[0], resp[1]

        if version != 0:
            raise ConnectionError(f"Invalid SOCKS4 response version: {version}")

        if status != 90:
            error_messages = {
                91: "Request rejected or failed",
                92: "Request rejected because SOCKS server cannot connect to identd on the client",
                93: "Request rejected because the client program and identd report different user-ids",
            }
            error = error_messages.get(status, f"Unknown error (code: {status})")
            raise ConnectionError(f"SOCKS4 server error: {error}")

    async def create_udp_socket(
        self, target_host: str | None = None, target_port: int = 0
    ):
        """Create a UDP association through the SOCKS proxy (SOCKS5 only).

        Args:
            target_host: Optional target hostname or IP for the association
            target_port: Optional target port for the association

        Returns:
            Tuple of (transport, protocol, proxy_socket) for UDP communication
        """
        if self.version != self.SOCKS5:
            raise ValueError("UDP association is only supported with SOCKS5")

        # Create a TCP control connection to the proxy
        reader, writer = await self.create_connection("0.0.0.0", 0)

        # Send UDP ASSOCIATE command
        writer.write(struct.pack("!BBB", self.SOCKS5, self.CMD_UDP_ASSOCIATE, 0x00))

        # We bind to 0.0.0.0 to let the proxy choose
        writer.write(struct.pack("!B", self.ATYP_IPV4))
        writer.write(socket.inet_aton("0.0.0.0"))
        writer.write(struct.pack("!H", 0))  # Port 0 = let proxy choose
        await writer.drain()

        # Read response
        resp_header = await reader.readexactly(4)
        version, status, _, atyp = struct.unpack("!BBBB", resp_header)

        if version != self.SOCKS5:
            writer.close()
            raise ConnectionError(f"Unexpected SOCKS version in response: {version}")

        if status != 0x00:
            writer.close()
            error_messages = {
                0x01: "General failure",
                0x02: "Connection not allowed by ruleset",
                0x03: "Network unreachable",
                0x04: "Host unreachable",
                0x05: "Connection refused",
                0x06: "TTL expired",
                0x07: "Command not supported",
                0x08: "Address type not supported",
            }
            error = error_messages.get(status, f"Unknown error (code: {status})")
            raise ConnectionError(f"SOCKS5 server error: {error}")

        # Read the proxy's UDP relay address and port
        proxy_addr = None
        proxy_port = None

        if atyp == self.ATYP_IPV4:
            addr_bytes = await reader.readexactly(4)
            proxy_addr = socket.inet_ntoa(addr_bytes)
            port_bytes = await reader.readexactly(2)
            proxy_port = struct.unpack("!H", port_bytes)[0]
        elif atyp == self.ATYP_IPV6:
            addr_bytes = await reader.readexactly(16)
            proxy_addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
            port_bytes = await reader.readexactly(2)
            proxy_port = struct.unpack("!H", port_bytes)[0]
        elif atyp == self.ATYP_DOMAIN:
            domain_len = (await reader.readexactly(1))[0]
            domain = await reader.readexactly(domain_len)
            proxy_addr = domain.decode("idna")
            port_bytes = await reader.readexactly(2)
            proxy_port = struct.unpack("!H", port_bytes)[0]
        else:
            writer.close()
            raise ConnectionError(f"Unsupported address type in response: {atyp}")

        self.logger.info(f"UDP association established via {proxy_addr}:{proxy_port}")

        # Create protocol for handling UDP datagrams
        class SocksUDPProtocol(asyncio.DatagramProtocol):
            def __init__(self, parent):
                self.parent = parent
                self.transport = None
                self.received_data = asyncio.Queue()

            def connection_made(self, transport):
                self.transport = transport

            def datagram_received(self, data, addr):
                # Parse SOCKS5 UDP header
                if len(data) < 10:  # Minimum header size
                    self.parent.logger.warning(
                        f"Received invalid UDP packet from {addr}"
                    )
                    return

                # Parse header: RSV(2) + FRAG(1) + ATYP(1) + ...
                _, _, frag, atyp = struct.unpack("!HBB", data[:4])

                if frag != 0:
                    self.parent.logger.warning("Fragmented UDP packets not supported")
                    return

                # Skip the SOCKS header and get the actual data
                if atyp == self.parent.ATYP_IPV4:
                    header_size = 4 + 4 + 2  # RSV+FRAG+ATYP + IPv4 + Port
                elif atyp == self.parent.ATYP_IPV6:
                    header_size = 4 + 16 + 2  # RSV+FRAG+ATYP + IPv6 + Port
                elif atyp == self.parent.ATYP_DOMAIN:
                    domain_len = data[4]
                    header_size = (
                        4 + 1 + domain_len + 2
                    )  # RSV+FRAG+ATYP + DomainLen + Domain + Port
                else:
                    return

                payload = data[header_size:]
                self.received_data.put_nowait(payload)

            def error_received(self, exc):
                self.parent.logger.error(f"UDP socket error: {exc}")

            def connection_lost(self, exc):
                if exc:
                    self.parent.logger.error(f"UDP connection lost: {exc}")

        # Create UDP socket
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: SocksUDPProtocol(self), remote_addr=(proxy_addr, proxy_port)
        )

        # Return both the UDP socket and the TCP control connection
        # The caller must keep the TCP connection alive for the UDP association to work
        return transport, protocol, writer

    async def send_udp(self, transport, host, port, data):
        """Send UDP datagram through the SOCKS proxy.

        Args:
            transport: UDP transport from create_udp_socket
            host: Target hostname or IP address
            port: Target port
            data: Bytes to send
        """
        # Build SOCKS5 UDP header
        packet = bytearray(struct.pack("!HB", 0, 0))  # RSV + FRAG

        # Determine address type and format
        try:
            # Try to parse as IPv4
            addr = ipaddress.IPv4Address(host)
            packet.extend(struct.pack("!B", self.ATYP_IPV4))
            packet.extend(addr.packed)
        except ipaddress.AddressValueError:
            try:
                # Try to parse as IPv6
                addr = ipaddress.IPv6Address(host)
                packet.extend(struct.pack("!B", self.ATYP_IPV6))
                packet.extend(addr.packed)
            except ipaddress.AddressValueError:
                # Use domain name
                domain = host.encode("idna")
                packet.extend(struct.pack("!B", self.ATYP_DOMAIN))
                packet.extend(struct.pack("!B", len(domain)))
                packet.extend(domain)

        # Add port and data
        packet.extend(struct.pack("!H", port))
        packet.extend(data)

        # Send the packet
        transport.sendto(packet)


# Example integration with the TCP class
class SocksTCP:
    """TCP client that connects through a SOCKS proxy."""

    def __init__(
        self,
        proxy_host: str,
        proxy_port: int,
        socks_version: int = 5,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the SOCKS TCP client.

        Args:
            proxy_host: SOCKS proxy hostname or IP
            proxy_port: SOCKS proxy port
            socks_version: SOCKS protocol version (4 or 5)
            username: Optional username for authentication
            password: Optional password for authentication
            timeout: Connection timeout in seconds
        """
        self.proxy = SocksProxy(
            host=proxy_host,
            port=proxy_port,
            version=socks_version,
            username=username,
            password=password,
            timeout=timeout,
        )
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._reader = None
        self._writer = None

    async def connect(self, host: str, port: int) -> None:
        """Connect to a server through the SOCKS proxy.

        Args:
            host: Target server hostname or IP address
            port: Target server port
        """
        try:
            self._reader, self._writer = await self.proxy.create_connection(host, port)
            self.logger.info(f"Connected to {host}:{port} via SOCKS proxy")
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            raise

    async def send(self, data: bytes) -> None:
        """Send data through the proxied connection.

        Args:
            data: Bytes to send
        """
        if not self._writer:
            raise RuntimeError("Not connected")

        try:
            self._writer.write(data)
            await self._writer.drain()
        except Exception as e:
            self.logger.error(f"Failed to send data: {e}")
            raise

    async def receive(self, size: int = -1) -> bytes:
        """Receive data from the proxied connection.

        Args:
            size: Number of bytes to read, -1 for all available

        Returns:
            Received bytes
        """
        if not self._reader:
            raise RuntimeError("Not connected")

        try:
            if size < 0:
                # Read available data
                data = await asyncio.wait_for(
                    self._reader.read(65536), timeout=self.timeout
                )
            else:
                # Read exactly n bytes
                data = await asyncio.wait_for(
                    self._reader.readexactly(size), timeout=self.timeout
                )
            return data
        except asyncio.IncompleteReadError as e:
            # Connection closed while reading
            return e.partial
        except Exception as e:
            self.logger.error(f"Failed to receive data: {e}")
            raise

    async def close(self) -> None:
        """Close the proxied connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._reader = None
            self._writer = None
            self.logger.info("Connection closed")


class SocksUDP:
    """UDP client that communicates through a SOCKS proxy."""

    def __init__(
        self,
        proxy_host: str,
        proxy_port: int,
        username: str = None,
        password: str = None,
        timeout: float = 30.0,
    ):
        """Initialize the SOCKS UDP client.

        Args:
            proxy_host: SOCKS proxy hostname or IP
            proxy_port: SOCKS proxy port
            username: Optional username for authentication
            password: Optional password for authentication
            timeout: Operation timeout in seconds
        """
        self.proxy = SocksProxy(
            host=proxy_host,
            port=proxy_port,
            version=5,  # UDP only works with SOCKS5
            username=username,
            password=password,
            timeout=timeout,
        )
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self._transport = None
        self._protocol = None
        self._control = None  # TCP control connection
        self._target_host = None
        self._target_port = None

    async def connect(self, host: str, port: int) -> None:
        """Create a UDP association through the SOCKS proxy.

        Args:
            host: Target hostname or IP address for the association
            port: Target port for the association
        """
        try:
            (
                self._transport,
                self._protocol,
                self._control,
            ) = await self.proxy.create_udp_socket()
            self._target_host = host
            self._target_port = port
            self.logger.info(f"UDP association created for {host}:{port}")
        except Exception as e:
            self.logger.error(f"Failed to create UDP association: {e}")
            raise

    async def send(self, data: bytes) -> None:
        """Send a UDP datagram through the SOCKS proxy.

        Args:
            data: Bytes to send
        """
        if not self._transport:
            raise RuntimeError("UDP association not created")

        try:
            await self.proxy.send_udp(
                self._transport, self._target_host, self._target_port, data
            )
        except Exception as e:
            self.logger.error(f"Failed to send datagram: {e}")
            raise

    async def receive(self) -> bytes:
        """Receive a UDP datagram.

        Returns:
            Received bytes
        """
        if not self._protocol:
            raise RuntimeError("UDP association not created")

        try:
            data = await asyncio.wait_for(
                self._protocol.received_data.get(), timeout=self.timeout
            )
            return data
        except asyncio.TimeoutError:
            self.logger.error(f"UDP receive timed out after {self.timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Failed to receive datagram: {e}")
            raise

    async def close(self) -> None:
        """Close the UDP association."""
        if self._transport:
            self._transport.close()
            self._transport = None

        if self._control:
            self._control.close()
            await self._control.wait_closed()
            self._control = None

        self._protocol = None
        self.logger.info("UDP association closed")
