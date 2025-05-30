<h1 align="center">
  <a href="https://github.com/idumhq/idum-proxy">
    <img src="https://raw.githubusercontent.com/idumhq/idum-proxy/refs/heads/main/docs/docs/assets/logo.png" alt="Master">
  </a>
<br>
</h1>
<h1 align="center">
IDUM-PROXY
</h1>


<p align="center"><i>Idum-Proxy is the easiest and quickest way to deploy a web proxy.</i></p>

****

<!-- Project Status Badges -->
![License](https://img.shields.io/badge/license-BSL-blue.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)

<!-- Technology Badges 
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Asyncio](https://img.shields.io/badge/Asyncio-FFD43B?style=flat&logo=python&logoColor=blue)
-->
<!-- Protocol Support Badges -->
![HTTP](https://img.shields.io/badge/HTTP-✅-green)
![HTTPS](https://img.shields.io/badge/HTTPS-✅-green)
![WebSocket](https://img.shields.io/badge/WebSocket-✅-green)
![SOCKS5](https://img.shields.io/badge/SOCKS5-✅-green)
![TCP/UDP](https://img.shields.io/badge/TCP%2FUDP-✅-green)

<!-- Installation Badge 
![PyPI](https://img.shields.io/pypi/v/idum-proxy?logo=pypi&logoColor=white)
![Downloads](https://img.shields.io/pypi/dm/idum-proxy?logo=pypi&logoColor=white)
-->
<!-- Social Badges
![GitHub stars](https://img.shields.io/github/stars/idumhq/idum-proxy?style=social)
![GitHub forks](https://img.shields.io/github/forks/idumhq/idum-proxy?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/idumhq/idum-proxy?style=social)
 -->
<!-- Custom Style Badges 
![Proxy](https://img.shields.io/badge/🌐_Proxy-Server-4F46E5?style=for-the-badge)
![Performance](https://img.shields.io/badge/⚡_High-Performance-10B981?style=for-the-badge)
![Security](https://img.shields.io/badge/🔒_Secure-Authentication-DC2626?style=for-the-badge)
-->

****

## ✨ Features

Idum-Proxy offers many features:

- 🔒 Protocol Support: Handle HTTP, HTTPS, WebSockets, TCP/UDP, and SOCKS proxies
- 🔐 Authentication: Support for various auth methods (Basic, Digest, NTLM, Kerberos)
- 🔄 Connection Pooling: Efficient reuse of connections to improve performance
- ⚖️ Load Balancing: Distribute traffic across multiple proxies
- 🏥 Health Checking: Automatic detection and recovery from failed proxies
- 💾 Caching: Store and reuse responses for identical requests
- 🔄 Retry Mechanisms: Automatically retry failed requests
- 🔧 Circuit Breaking: Prevent cascading failures
- 📊 Metrics Collection: Track proxy performance, latency, error rates
- 🔐 TLS/SSL Termination: Handle encryption/decryption
- 🌍 IP Rotation: Change public IP addresses for scraping
- 🎯 Geo-targeting: Route requests through proxies in specific locations




## 🚀 Quick Start

## Installation

```bash
pip install idum_proxy
```

Or with uv:

```bash
uv add idum_proxy
```

### Basic Usage

```python
from idum_proxy import IdumProxy

if __name__ == "__main__":
    idum_proxy: IdumProxy = IdumProxy(config_file='proxy.json')
    idum_proxy.serve(host='0.0.0.0', port=8091)
```

📋 Configuration Example

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
          "url": "https://jsonplaceholder.typicode.com/posts"
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




## 🐳 Docker Usage


```bash
docker build -t idum-proxy -f dockerfiles/idum_proxy.Dockerfile .
docker run  -p 8080:8080 idum-proxy
```

## 📄 License

[Business Source License 1.1](LICENSE)