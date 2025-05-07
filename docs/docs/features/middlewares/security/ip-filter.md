# IP Filter

The IP Filter middleware in idum-proxy provides network-level access control by allowing or blocking requests based on client IP addresses. This security feature helps protect your application from unauthorized access and potential attacks from specific IP addresses or ranges.

## Configuration

IP filtering is configured in the JSON configuration file as follows:

```json
{
  "middlewares": {
    "security": {
      "ip_filter": {
        "enabled": true,
        "blacklist": [
          "*.0.0.2"
        ]
      }
    }
  }
}
```

## Configuration Options

| Option      | Type    | Default | Description                                           |
|-------------|---------|---------|-------------------------------------------------------|
| `enabled`   | boolean | `true`  | Enables or disables the IP filter middleware          |
| `blacklist` | array   | `[]`    | List of IP addresses or patterns to block             |
| `whitelist` | array   | `[]`    | List of IP addresses or patterns to explicitly allow  |

## Filtering Behavior

The IP Filter middleware processes requests in the following order:

1. If the feature is disabled (`enabled: false`), all requests pass through unaffected
2. If a `whitelist` is provided and non-empty:
   - If the client IP matches any entry in the `whitelist`, the request is allowed
   - If the client IP doesn't match any entry in the `whitelist`, the request is blocked (returns 403 Forbidden)
3. If only a `blacklist` is provided (or `whitelist` is empty):
   - If the client IP matches any entry in the `blacklist`, the request is blocked (returns 403 Forbidden)
   - If the client IP doesn't match any entry in the `blacklist`, the request is allowed

## IP Pattern Formats

idum-proxy supports several formats for specifying IP addresses in the blacklist and whitelist:

1. **Exact IP address**: `"192.168.1.1"`
2. **CIDR notation**: `"192.168.1.0/24"` (matches all IPs in the range 192.168.1.0 to 192.168.1.255)
3. **Wildcard pattern**: `"192.168.*.*"` or `"*.0.0.2"` (using `*` as a wildcard for any number in an octet)
4. **IP ranges**: `"192.168.1.1-192.168.1.10"` (matches all IPs in the inclusive range)

## Examples

### Blocking Specific IP Addresses

```json
"ip_filter": {
  "enabled": true,
  "blacklist": [
    "192.168.1.1",
    "10.0.0.5",
    "172.16.0.100"
  ]
}
```

### Blocking IP Ranges

```json
"ip_filter": {
  "enabled": true,
  "blacklist": [
    "192.168.1.0/24",
    "10.0.0.0/16",
    "*.0.0.2"
  ]
}
```

### Allowing Only Specific IPs (Whitelist Mode)

```json
"ip_filter": {
  "enabled": true,
  "whitelist": [
    "192.168.1.10",
    "192.168.1.11",
    "10.0.0.5"
  ],
  "blacklist": []
}
```

### Mixed Approach (Whitelist with Exceptions)

```json
"ip_filter": {
  "enabled": true,
  "whitelist": [
    "192.168.1.0/24"  // Allow the entire subnet
  ],
  "blacklist": [
    "192.168.1.13"    // Except this specific IP
  ]
}
```

## Special Considerations

### Private Networks

By default, idum-proxy treats private network ranges (e.g., 10.0.0.0/8, 192.168.0.0/16) like any other IP address. If your application is deployed within a private network, be careful not to inadvertently block legitimate internal traffic.

### Proxy Servers and CDNs

When your application is behind a load balancer, proxy server, or CDN, the client IP address may be replaced with the IP of the intermediary service. In these cases:

1. Configure your proxy to forward the original client IP (usually via `X-Forwarded-For` or similar headers)
2. Configure idum-proxy to use the appropriate header for client IP detection

### IPv6 Support

The IP Filter supports both IPv4 and IPv6 addresses. IPv6 addresses should be specified in standard notation:

```json
"blacklist": [
  "2001:db8:1234:5678:abcd:ef01:2345:6789",
  "2001:db8:1234::/48"
]
```

## Performance Impact

The IP Filter middleware performs efficiently with minimal overhead:

- IP address parsing and matching is optimized for performance
- CIDR and range checks use efficient algorithms
- Wildcard patterns are converted to optimized comparison functions at startup

Even with large blacklists or whitelists, the performance impact is typically negligible.

## Security Recommendations

1. **Default Deny**: For high-security applications, use a whitelist approach (empty blacklist, specific whitelist)
2. **Block Known Malicious IPs**: Regularly update your blacklist with known malicious IP addresses
3. **Use with Rate Limiting**: Combine IP filtering with rate limiting for better protection
4. **Monitor Logs**: Regularly review logs for blocked IP attempts to identify attack patterns
5. **Consider Geolocation**: For region-specific services, consider blocking IP ranges by country