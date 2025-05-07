# Mock

```json
{
  "upstream": {
    "echo": {
      "enabled": true,
      "add_headers": {
        "X-Echo-Service": "true",
        "X-Request-Time": "${timestamp}"
      },
      "response_delay_ms": 100
    }
  }
}
```