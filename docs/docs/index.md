# Welcome to Idum-Proxy

Idum Proxy is a lightweight reverse proxy with main features :

- Protocol Support: Handle HTTP, HTTPS, WebSockets, TCP/UDP, and SOCKS proxies
- Authentication: Support for various auth methods (Basic, Digest, NTLM, Kerberos)
- Connection Pooling: Efficient reuse of connections to improve performance
- Load Balancing: Distribute traffic across multiple proxies using algorithms like round-robin, least connections
- Health Checking: Automatic detection and recovery from failed proxies
- Caching: Store and reuse responses for identical requests
- Retry Mechanisms: Automatically retry failed requests with configurable backoff
- Circuit Breaking: Prevent cascading failures by detecting and isolating problematic services
- Metrics Collection: Track proxy performance, latency, error rates
- TLS/SSL Termination: Handle encryption/decryption to reduce backend load
- IP Rotation: Change public IP addresses for scraping or anonymity
- Geo-targeting: Route requests through proxies in specific geographic locations

## Idum-Proxy for python developers

### Install the package

=== "Installing with uv"
    ```bash
    uv add idum_proxy
    ```

=== "Installing with pip"
    ```bash
    pip install idum_proxy
    ```

### Simple example

proxy.json
```json
{
  "version": "1.0",
  "name": "Simple example",
  "endpoints": [
    {
      "prefix": "/",
      "match": "**/*",
      "backends": {
        "https": {
          "url": "https://sandbox.api.service.nhs.uk/hello-world/hello/world$"
        }
      },
      "upstream": {
        "proxy": {
          "enabled": true
        }
      }
    }
  ]
}
```

main.py
```python
from idum_proxy import IdumProxy
proxy:IdumProxy = IdumProxy(config_file='proxy.json')
proxy.serve(host='0.0.0.0', port=8091)
```

And open a browser to go to the url http://0.0.0.0:8091
or use the curl command in a terminal:
```bash
curl -X GET http://0.0.0.0:8091
```

Well done! you are ready to use Idum Proxy