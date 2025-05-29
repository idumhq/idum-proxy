# Maven

## Configure the remote repository

```json
{
  "identifier": "maven-remote-central",
  "prefix": "/maven-remote-central",
  "match": "/maven-remote-central/**",
  "backends": [
    {
      "https": [
        {
          "id": "maven-central",
          "url": "https://repo1.maven.org/maven2",
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
        "path": ".cache/maven/maven-remote-central",
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
          "oldvalue": "href=\"",
          "newvalue": "href=\"${path}"
        }
      ]
    }
  }
}
```