# What is Idum-Proxy ?

Idum Proxy is a lightweight reverse proxy with cool features :

* protocols : https, tcp, tls, exec,

## Idum-Proxy for python developers

### Install the package

* uv add idum_proxy
* pip install idum_proxy

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