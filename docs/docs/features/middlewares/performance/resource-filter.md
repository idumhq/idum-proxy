# Resource Filter

The Resource Filter configuration in idum-proxy allows you to exclude specific paths from normal proxy processing pipeline. This improves performance by bypassing middleware processing for common static files and standardized endpoints.

## Configuration

Resource filtering is configured in the JSON configuration file as follows:

```json
{
  "performance": {
    "resource_filter": {
      "enabled": true,
      "skip_paths": [
        "favicon.ico",
        ".well-known/**",
        "robots.txt"
      ]
    }
  }
}
```

## Configuration Options

| Option      | Type    | Default | Description                                                    |
|-------------|---------|---------|----------------------------------------------------------------|
| `enabled`   | boolean | `true`  | Enables or disables the resource filter functionality          |
| `skip_paths` | array   | `[]`    | List of paths or patterns that should bypass normal processing |

## Path Pattern Formats

The `skip_paths` configuration supports the following pattern formats:

1. **Exact Path Match**: `"favicon.ico"` - Matches this exact file only
2. **Directory Wildcard**: `".well-known/**"` - Matches any path under the `.well-known/` directory
3. **Extension Pattern**: `"*.jpg"` - Would match all JPEG files (not shown in example)
4. **Root Path**: `"/health"` - Exact match for a root-level path

## Examples

### Skipping Static File Extensions

To skip processing for common static files:

```json
"skip_paths": [
  "*.jpg",
  "*.png", 
  "*.gif",
  "*.css",
  "*.js"
]
```

### Skipping API Health Checks

To bypass proxy processing for monitoring endpoints:

```json
"skip_paths": [
  "/health",
  "/ping",
  "/status"
]
```

### Complex Pattern Example

To skip processing for a complex set of paths:

```json
"skip_paths": [
  "favicon.ico",
  ".well-known/**",
  "robots.txt",
  "static/**",
  "*.jpg",
  "*/assets/*",
  "/api/health"
]
```

## Performance Impact

Enabling resource filtering can significantly improve proxy performance, particularly for high-traffic websites. Common paths like `favicon.ico` can represent a substantial portion of requests but rarely benefit from full proxy processing.

Benchmarks show that properly configured resource filtering can reduce CPU utilization by 15-30% in typical web applications.