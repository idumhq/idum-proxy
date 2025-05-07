# Bot Filter

The Bot Filter middleware in idum-proxy provides protection against unauthorized and malicious bot traffic. It allows you to create blacklists and whitelists to control which bots can access your application.

## Configuration

Bot filtering is configured in the JSON configuration file as follows:

```json
{
  "middlewares": {
    "security": {
      "bot_filter": {
        "enabled": true,
        "blacklist": [
          {
            "name": "googlebot",
            "user-agent": "crawl-***-***-***-***.googlebot.com"
          }
        ],
        "whitelist": []
      }
    }
  }
}
```

## Configuration Options

| Option        | Type    | Default | Description                                              |
|---------------|---------|---------|----------------------------------------------------------|
| `enabled`     | boolean | `true`  | Enables or disables the bot filter middleware            |
| `blacklist`   | array   | `[]`    | List of bot definitions to block                         |
| `whitelist`   | array   | `[]`    | List of bot definitions to explicitly allow              |

## Bot Definition Format

Each bot in the blacklist or whitelist is defined with the following properties:

| Property      | Type   | Required | Description                                               |
|---------------|--------|----------|-----------------------------------------------------------|
| `name`        | string | Yes      | Identifier for the bot (for logging and reference)        |
| `user-agent`  | string | No       | Pattern to match against the User-Agent header            |
| `ip`          | string | No       | IP address or CIDR range to match against client IP       |
| `referer`     | string | No       | Pattern to match against the Referer header               |
| `path`        | string | No       | URL path pattern to apply this rule to                    |

At least one matching criterion (`user-agent`, `ip`, or `referer`) must be provided.

## Filtering Behavior

The Bot Filter middleware processes requests in the following order:

1. If the feature is disabled (`enabled: false`), all requests pass through unaffected
2. If the request matches any entry in the `whitelist`, it is allowed to proceed
3. If the request matches any entry in the `blacklist`, it is blocked (returns 403 Forbidden)
4. If the request doesn't match any rule, it is allowed to proceed

## Pattern Matching

idum-proxy supports different pattern matching techniques for different fields:

- **`user-agent`**: Supports wildcard patterns with `*` (e.g., `"crawl-*-*.googlebot.com"`)
- **`ip`**: Supports exact IP addresses or CIDR notation (e.g., `"192.168.1.1"` or `"192.168.1.0/24"`)
- **`referer`**: Supports wildcard patterns with `*` (e.g., `"*.example.com/*"`)
- **`path`**: Supports wildcard patterns with `*` (e.g., `"/api/*"`)

## Examples

### Blocking Known Bad Bots

```json
"bot_filter": {
  "enabled": true,
  "blacklist": [
    {
      "name": "fake-googlebot",
      "user-agent": "*googlebot*",
      "ip": "192.168.1.100"
    },
    {
      "name": "scraper-bot",
      "user-agent": "*scraper*"
    },
    {
      "name": "malicious-crawler",
      "user-agent": "*crawler*",
      "path": "/admin/*"
    }
  ],
  "whitelist": []
}
```

### Allowing Only Specific Bots

```json
"bot_filter": {
  "enabled": true,
  "blacklist": [
    {
      "name": "all-bots",
      "user-agent": "*bot*"
    }
  ],
  "whitelist": [
    {
      "name": "google",
      "user-agent": "*googlebot*",
      "ip": "66.249.66.0/24"
    },
    {
      "name": "bing",
      "user-agent": "*bingbot*"
    }
  ]
}
```

### Protecting Specific Paths

```json
"bot_filter": {
  "enabled": true,
  "blacklist": [
    {
      "name": "any-bot-on-private-paths",
      "user-agent": "*bot*",
      "path": "/private/*"
    },
    {
      "name": "any-bot-on-admin",
      "user-agent": "*bot*",
      "path": "/admin/*"
    }
  ],
  "whitelist": []
}
```

## Logs and Monitoring

When a bot is blocked by the filter, idum-proxy logs the event with the following information:

- Bot name from the matching rule
- Client IP address
- User-Agent header
- Request path
- Matched rule details

These logs can be used to monitor bot activity and refine your filtering rules.

## Best Practices

1. **Start with monitoring**: Initially deploy with minimal blocking to observe patterns
2. **Verify legitimate bots**: For search engines, verify their authenticity by reverse DNS lookup
3. **Be specific**: Target specific bot behaviors rather than broad patterns
4. **Whitelist good bots**: Explicitly whitelist legitimate bots you want to allow
5. **Regularly update rules**: Bot patterns change regularly, keep your rules current
6. **Monitor false positives**: Watch for legitimate traffic being blocked

## Security Considerations

- Bot filtering should be used as part of a larger security strategy
- Sophisticated bots can spoof User-Agent headers and IP addresses
- Consider combining with rate limiting and behavioral analysis for better protection
- For critical applications, consider using CAPTCHA or JavaScript challenges in addition to bot filtering