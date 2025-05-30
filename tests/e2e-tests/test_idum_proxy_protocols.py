"""
    documentation: https://tcpbin.com/


idum_proxy = IdumProxy("idum_proxy/default.json")


@pytest.mark.asyncio
async def test_idum_proxy_https_request():
    response = await idum_proxy.config.https_request(
        prefix="/", url="https://www.google.fr", method="GET"
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_idum_proxy_tcp():
    # Port 4242 is "TCP echo"
    async with idum_proxy.tcp_connect(host="tcpbin.com", port=4242) as tcp_conn:
        response = await tcp_conn.send(b"Hello server!\n")
        assert response == b"Hello server!\n"

        response = await tcp_conn.send_only(b"Hello World!\n")
        assert response is None

        response = await tcp_conn.receive()
        assert response == b"Hello World!\n"


@pytest.mark.asyncio
async def test_idum_proxy_tls_invalid_certificate_valid():
    async with idum_proxy.tls_connect(host="google.fr", port=443) as tls_conn:
        response = await tls_conn.send(b"GET /\n")
        assert response != b""
        # print(response)


@pytest.mark.asyncio
async def test_idum_proxy_tls_invalid_certificate_expired():
    with pytest.raises(ssl.SSLCertVerificationError) as excinfo:
        async with idum_proxy.tls_connect(host="expired.badssl.com", port=443):
            pytest.fail("TLS Connection must be closed")

    assert excinfo.value.reason == "CERTIFICATE_VERIFY_FAILED"
    assert excinfo.value.verify_message == "certificate has expired"


@pytest.mark.asyncio
async def test_idum_proxy_tls_invalid_self_signed_certificate():
    with pytest.raises(ssl.SSLCertVerificationError) as excinfo:
        async with idum_proxy.tls_connect(host="self-signed.badssl.com", port=443):
            pytest.fail("TLS Connection must be closed")

    assert excinfo.value.reason == "CERTIFICATE_VERIFY_FAILED"
    assert excinfo.value.verify_message == "self-signed certificate"


@pytest.mark.asyncio
async def test_idum_proxy_tls_invalid_non_existant_certificate():
    with pytest.raises(socket.gaierror):
        async with idum_proxy.tls_connect(host="nonexistent.example.com", port=443):
            pytest.fail("TLS Connection should have failed but succeeded")


@pytest.mark.asyncio
async def test_idum_proxy_tls_letsencrypt():
    # Port 4243 is "TCP echo with TLS encryption"
    async with idum_proxy.tls_connect(host="tcpbin.com", port=4243) as tls_conn:
        response = await tls_conn.send(b"Hello server!\n")
        assert response == b"Hello server!\n"

        response = await tls_conn.send_only(b"Hello World!\n")
        assert response is None

        response = await tls_conn.receive()
        assert response == b"Hello World!\n"


@pytest.mark.asyncio
async def test_idum_proxy_tls_lack_certificates():
    "certificate are mandatory but not sent, the transport is closed by the server"
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True

    ssl_context.load_verify_locations(certifi.where())
    with pytest.raises(ConnectionError):
        async with idum_proxy.tls_connect(
            host="tcpbin.com", port=4244, ssl_context=ssl_context
        ):
            pytest.fail("TLS Connection should be closed")


@pytest.mark.asyncio
async def test_idum_proxy_tls_valid():
    # curl -s https://tcpbin.com/api/client-cert > pair.json
    # cat pair.json | jq ".key" -r > client_key.pem
    # cat pair.json | jq ".cert" -r > client_cert.pem
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.load_cert_chain(
        certfile="tests/client_cert.pem", keyfile="tests/client_key.pem"
    )
    # To authenticate on port 4244, you will need a valid client certificate and key.
    # Please note that the CA used for this purpose is an open CA, meaning it should not be trusted for anything other
    # than this service.

    # ssl_context.load_verify_locations("tests/ca-cert.pem")
    ssl_context.load_verify_locations(certifi.where())

    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True

    # Port 4244 is "TCP echo with mutual authentication"

    async with idum_proxy.tls_connect(
        host="tcpbin.com", port=4244, ssl_context=ssl_context
    ) as tls_conn:
        response = await tls_conn.send(b"Hello server!\n")
        assert response == b"Hello server!\n"

        response = await tls_conn.send_only(b"Hello World!\n")
        assert response is None

        response = await tls_conn.receive()
        assert response == b"Hello World!\n"
"""
