
The Compression configuration in idum-proxy enables response compression to reduce bandwidth usage and improve page load times. By compressing responses before sending them to clients, idum-proxy can significantly reduce the size of transmitted data.

## Configuration

Compression is configured in the JSON configuration file as follows:

```json
{
  "performance": {
    "compression": {
      "enabled": true,
      "algorithm": "gzip",
      "compress_level": 9,
      "min_size": 500,
      "types": [
        "text/html",
        "text/css",
        "text/javascript",
        "application/json",
        "application/javascript",
        "text/plain"
      ]
    }
  }
}
```

## Configuration Options

|Option|Type|Default|Description|
|---|---|---|---|
|`enabled`|boolean|`true`|Enables or disables response compression|
|`algorithm`|string|`"gzip"`|Compression algorithm: either "gzip" or "brotli"|
|`compress_level`|integer|`9`|Compression level (1-9 for gzip, 1-11 for brotli)|
|`min_size`|integer|`500`|Minimum response size in bytes to apply compression|
|`types`|array of strings|_(see below)_|Content types that should be compressed|

## Default Content Types

By default, idum-proxy compresses the following content types:

- `text/html` - HTML documents
- `text/css` - CSS stylesheets
- `text/javascript` - JavaScript files
- `application/json` - JSON data
- `application/javascript` - JavaScript files (alternative content type)
- `text/plain` - Plain text documents

## Compression Behavior

When compression is enabled:

1. idum-proxy checks whether the client supports compression (via `Accept-Encoding` header)
2. If the response content type matches one in the `types` list
3. And the response size exceeds `min_size` bytes
4. Then the response is compressed using the specified `compress_level`
5. idum-proxy adds appropriate `Content-Encoding` headers to the response

## Compression Algorithms

idum-proxy supports two compression algorithms:

### Gzip

- **Default algorithm** - Widely supported by all browsers
- **Compression level**: 1-9 (9 is maximum compression)
- **Performance profile**: Faster compression speed but generally larger file sizes compared to Brotli
- **Use case**: Good general-purpose compression for all types of content

### Brotli

- **Modern algorithm** - Supported by all modern browsers (>96% of global users)
- **Compression level**: 1-11 (11 is maximum compression)
- **Performance profile**: Better compression ratios but slower compression speed
- **Use case**: Ideal for static cacheable content where compression time is less important

The proxy will automatically select the appropriate algorithm based on:

1. The configured `algorithm` setting
2. Client support (via `Accept-Encoding` header)
3. If a client doesn't support the configured algorithm, the proxy will fall back to a supported one when possible

## Minimum Size

The `min_size` parameter sets the threshold for applying compression:

- Responses smaller than this size will not be compressed
- This prevents the overhead of compression for very small responses
- The default value of 500 bytes is a good balance for most applications

## Content Types

The `types` array specifies which content types should be compressed:

- Only responses with a `Content-Type` that matches one in this list will be compressed
- Content types should be specified as MIME types (e.g., `text/html`)
- You can add custom content types to this list if needed

## Examples

### Using Brotli for Maximum Compression

```json
"compression": {
  "enabled": true,
  "algorithm": "brotli",
  "compress_level": 11,
  "min_size": 500,
  "types": [
    "text/html",
    "text/css",
    "text/javascript",
    "application/json",
    "application/javascript",
    "text/plain",
    "text/xml",
    "application/xml"
  ]
}
```

### Using Gzip with Balanced Compression for Large Responses Only

```json
"compression": {
  "enabled": true,
  "algorithm": "gzip",
  "compress_level": 6,
  "min_size": 10240,
  "types": [
    "text/html",
    "text/css",
    "application/json"
  ]
}
```

### Disable Compression

```json
"compression": {
  "enabled": false
}
```

## Performance Impact

- **Reduced bandwidth**:
    
    - Gzip typically reduces response sizes by 60-80% for text-based content
    - Brotli typically reduces response sizes by 70-90% for text-based content
- **Compression efficiency comparison**:
    
    |Content Type|Gzip (Level 9)|Brotli (Level 11)|
    |---|---|---|
    |HTML|~75%|~85%|
    |CSS|~80%|~90%|
    |JavaScript|~70%|~80%|
    |JSON|~80%|~85%|
    |SVG|~60%|~75%|
    
- **Processing overhead**:
    
    - Brotli requires more CPU time for compression, especially at higher levels
    - Gzip offers faster compression but less reduction in file size
    - Decompression speed is comparable between both algorithms
- **Ideal usage scenarios**:
    
    - For dynamic content: Use Gzip with level 6 (good balance)
    - For static cacheable content: Use Brotli with level 11 (maximum compression)
    - For high-traffic APIs: Use Gzip with level 1-4 (prioritize server performance)
    - For bandwidth-constrained environments: Use Brotli with level 9-11 (prioritize size reduction)

## Browser Support

- **Gzip**: Supported by virtually all browsers (>99.5% of global users)
- **Brotli**: Supported by all modern browsers (>96% of global users), including:
    - Chrome 51+ (May 2016)
    - Firefox 44+ (January 2016)
    - Edge 15+ (April 2017)
    - Safari 11+ (September 2017)
    - Opera 38+ (June 2016)

The proxy determines support by examining the `Accept-Encoding` header sent by the client:

- `Accept-Encoding: gzip` - Client supports gzip
- `Accept-Encoding: br` - Client supports Brotli
- `Accept-Encoding: br, gzip` - Client supports both (common in modern browsers)

If a client doesn't support the configured algorithm, idum-proxy will automatically fall back to a supported algorithm or send uncompressed content.