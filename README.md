# Idum-Proxy

Idum-Proxy is the easiest and quickest way to deploy a web proxy. 
Free and open-source.


## Features

Idum-Proxy offers many features:


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

## Install the package

```bash
pip install idum_proxy
```

Or with uv:

```bash
uv add idum_proxy
```

## Quick Start

### Basic Pattern Matching

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
          "url": "http://www.example.com"
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

```python
from idum_proxy import IdumProxy

if __name__ == "__main__":
    idum_proxy: IdumProxy = IdumProxy(config_file='proxy.json')
    idum_proxy.serve(host='0.0.0.0', port=8091)
```


## Build

Docker image

```bash
docker build -t idum-proxy -f dockerfiles/idum_proxy.Dockerfile .
docker run  -p 8080:8080 idum-proxy
```

## License

This project is licensed under the MIT License.