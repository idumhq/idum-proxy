# Protocols

idum-proxy supports multiple protocols for proxying various types of network traffic. This document describes the configuration options for each supported protocol.

## HTTP/HTTPS

HTTP and HTTPS protocols are used for standard web traffic proxying. This is the most common use case for idum-proxy.

```json
{
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

### Configuration Options

| Option | Description |
|--------|-------------|
| `prefix` | The URL path prefix to match incoming requests |
| `match` | Pattern to match against the remaining path after the prefix |
| `backends.https.url` | Target URL to proxy requests to |
| `upstream.proxy.enabled` | Enables/disables proxying for this endpoint |

### Additional HTTP/HTTPS Options

```json
{
  "endpoints": [
    {
      "prefix": "/api",
      "match": "**/*",
      "backends": {
        "https": {
          "url": "https://api.example.com",
          "timeout": 30,
          "headers": {
            "X-Forwarded-Host": "{{request.host}}",
            "X-Custom-Header": "custom-value"
          },
          "tls": {
            "verify": true,
            "cert": "/path/to/cert.pem",
            "key": "/path/to/key.pem"
          }
        }
      },
      "upstream": {
        "proxy": {
          "enabled": true,
          "strip_prefix": true,
          "rewrite_response": {
            "headers": {
              "Server": "idum-proxy"
            }
          }
        }
      }
    }
  ]
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backends.https.timeout` | integer | 60 | Request timeout in seconds |
| `backends.https.headers` | object | {} | Additional headers to send to the backend |
| `backends.https.tls.verify` | boolean | true | Verify SSL certificates |
| `backends.https.tls.cert` | string | "" | Client certificate for TLS authentication |
| `backends.https.tls.key` | string | "" | Client key for TLS authentication |
| `upstream.proxy.strip_prefix` | boolean | false | Strip the prefix before forwarding to the backend |
| `upstream.proxy.rewrite_response.headers` | object | {} | Rewrite response headers |

## Exec

The Exec protocol allows idum-proxy to execute local commands or scripts and proxy requests to them.

```json
{
  "endpoints": [
    {
      "prefix": "/scripts",
      "match": "**/*",
      "backends": {
        "exec": {
          "command": "/usr/bin/python",
          "args": ["/path/to/script.py", "{{request.path}}"],
          "env": {
            "CUSTOM_ENV": "value"
          },
          "working_dir": "/path/to/workdir"
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

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backends.exec.command` | string | required | Command to execute |
| `backends.exec.args` | array | [] | Command arguments |
| `backends.exec.env` | object | {} | Environment variables to set |
| `backends.exec.working_dir` | string | current dir | Working directory for the command |
| `backends.exec.timeout` | integer | 60 | Execution timeout in seconds |

### Template Variables

In the `args` array, you can use template variables to pass request information:

- `{{request.path}}` - The full request path
- `{{request.method}}` - The HTTP method (GET, POST, etc.)
- `{{request.query.param}}` - A query parameter value
- `{{request.headers.name}}` - A request header value

## TCP

TCP protocol support allows idum-proxy to handle raw TCP connections for any TCP-based protocol.

```json
{
  "endpoints": [
    {
      "listen": "0.0.0.0:8080",
      "backends": {
        "tcp": {
          "address": "backend.example.com:9000",
          "timeout": 300
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

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `listen` | string | required | Interface and port to listen on |
| `backends.tcp.address` | string | required | Target address (host:port) |
| `backends.tcp.timeout` | integer | 300 | Connection timeout in seconds |
| `backends.tcp.buffer_size` | integer | 4096 | Buffer size for data transfer |

### TCP Load Balancing

```json
{
  "endpoints": [
    {
      "listen": "0.0.0.0:8080",
      "backends": {
        "tcp": {
          "addresses": [
            "backend1.example.com:9000",
            "backend2.example.com:9000"
          ],
          "load_balancing": "round_robin"
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

| Option | Type | Values | Description |
|--------|------|--------|-------------|
| `backends.tcp.addresses` | array | [] | List of backend addresses for load balancing |
| `backends.tcp.load_balancing` | string | "round_robin" | Load balancing algorithm (round_robin, least_conn, ip_hash) |

## UDP

UDP protocol support enables idum-proxy to handle stateless UDP traffic.

```json
{
  "endpoints": [
    {
      "listen": "0.0.0.0:53",
      "backends": {
        "udp": {
          "address": "8.8.8.8:53",
          "timeout": 5
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

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `listen` | string | required | Interface and port to listen on |
| `backends.udp.address` | string | required | Target address (host:port) |
| `backends.udp.timeout` | integer | 5 | Response timeout in seconds |
| `backends.udp.buffer_size` | integer | 4096 | Maximum UDP packet size |

### UDP Load Balancing

Similar to TCP, UDP also supports load balancing:

```json
{
  "endpoints": [
    {
      "listen": "0.0.0.0:53",
      "backends": {
        "udp": {
          "addresses": [
            "8.8.8.8:53",
            "8.8.4.4:53"
          ],
          "load_balancing": "random"
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

## SOCKS5

SOCKS5 protocol allows idum-proxy to function as a SOCKS5 proxy server, enabling traffic tunneling for various protocols.

```json
{
  "endpoints": [
    {
      "listen": "0.0.0.0:1080",
      "backends": {
        "socks5": {
          "auth": {
            "required": true,
            "users": [
              {
                "username": "user",
                "password": "pass"
              }
            ]
          },
          "allowed_destinations": [
            "*.example.com:*"
          ]
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

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `listen` | string | required | Interface and port to listen on |
| `backends.socks5.auth.required` | boolean | false | Require authentication |
| `backends.socks5.auth.users` | array | [] | List of authorized users |
| `backends.socks5.allowed_destinations` | array | ["*:*"] | Allowed destination patterns |
| `backends.socks5.bind_timeout` | integer | 30 | Timeout for bind operations |
| `backends.socks5.connect_timeout` | integer | 30 | Timeout for connect operations |

### SOCKS5 Authentication

SOCKS5 supports username/password authentication:

```json
"auth": {
  "required": true,
  "users": [
    {
      "username": "user1",
      "password": "password1"
    },
    {
      "username": "user2",
      "password": "password2"
    }
  ]
}
```

### SOCKS5 Destination Filtering

You can control which destinations can be accessed through the SOCKS5 proxy:

```json
"allowed_destinations": [
  "*.example.com:80",
  "*.example.com:443",
  "internal.network:*"
]
```

This uses a wildcard pattern format:
- `*` matches any character sequence within a segment
- `:*` matches any port
- `*:*` would allow any destination (default)

## Common Features

All protocols support these common features:

### Access Control

```json
"access_control": {
  "allow": ["192.168.1.0/24"],
  "deny": ["192.168.1.100"]
}
```

### Logging

```json
"logging": {
  "level": "info",
  "format": "json",
  "destination": "file",
  "file_path": "/var/log/idum-proxy/proxy.log"
}
```

### Rate Limiting

```json
"rate_limit": {
  "enabled": true,
  "requests_per_second": 10,
  "burst": 20
}
```

### TLS Termination

```json
"tls": {
  "enabled": true,
  "cert": "/path/to/cert.pem",
  "key": "/path/to/key.pem"
}
```