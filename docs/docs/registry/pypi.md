# Pypi

## Configure the remote repository

```json
{
  "identifier": "pypi-remote-official",
  "prefix": "/pypi-remote-official",
  "match": "/pypi-remote-official/**",
  "backends": [
    {
      "https": [
        {
          "id": "pypi-primary",
          "url": "https://pypi.org/simple",
          "ssl": true
        }
      ]
    }
  ],
  "upstream": {
    "proxy": {
      "enabled": true,
      "timeout_seconds": 60
    },
    "cache": {
      "file": {
        "enabled": true,
        "path": ".cache/pypi/pypi-remote-official",
        "ttl": 43200,
        "max_size_mb": 256,
        "max_entries": 2500
      }
    }
  },
  "transformers": {
    "response": {
      "enabled": true,
      "textReplacements": [
        {
          "oldvalue": "https://pypi.org/simple",
          "newvalue": "http://0.0.0.0:8080/pypi-remote-official"
        },
        {
          "oldvalue": "/simple",
          "newvalue": "/pypi-remote-official"
        }
      ]
    }
  }
}
```

## Configure a local repository

```json
{
  "identifier": "pypi-demo-local",
  "prefix": "/pypi-demo-local",
  "match": "/pypi-demo-local/**",
  "upstream": {
    "file": {
      "enabled": true,
      "path": ".files/pypi/pypi-demo-local"
    }
  }
}
```

## Configure a virtual repository

```json
{
  "prefix": "/pypi-virtual-all",
  "match": "/pypi-virtual-all/**",
  "upstream": {
    "virtual": {
      "sources": [
        "pypi-demo-local",
        "pypi-remote-official"
      ],
      "strategy": "first-match"
    }
  }
}
```