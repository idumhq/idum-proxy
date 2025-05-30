# Simple Reverse Proxy Example

This example demonstrates how to create a basic reverse proxy using `idum_proxy`. We'll proxy requests to the JSONPlaceholder API, which provides free fake REST API endpoints for testing and prototyping.

## Prerequisites

- Python 3.13+
- `uv` package manager

## Setup Instructions

### 1. Initialize the Project

Create a new Python project using `uv`:

```bash
uv init reverse-proxy-demo
cd reverse-proxy-demo
```

Add the required dependency:

```bash
uv add idum_proxy
```

### 2. Configuration File

Create a `proxy.json` file in your project root with the following configuration:

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

**Configuration Breakdown:**

- `prefix: "/"` - Routes all requests starting from the root path
- `match: "**/*"` - Matches all paths and subpaths using glob pattern
- `backends.https.url` - The target API endpoint we're proxying to
- `upstream.proxy.enabled` - Enables proxy functionality for this endpoint

### 3. Application Code

Replace the contents of `main.py` with:

```python
from idum_proxy import IdumProxy

proxy: IdumProxy = IdumProxy(config_file='proxy.json')
proxy.serve(host='0.0.0.0', port=8091)
```

**Code Explanation:**

- Creates an `IdumProxy` instance with our configuration file
- Starts the proxy server on all interfaces (`0.0.0.0`) at port `8091`

### 4. Running the Proxy

Start the application:

```bash
uv run python main.py
```

You should see output indicating the server has started successfully.

## Testing the Proxy

### Basic Test

Open your browser and navigate to:
```
http://localhost:8091
```

You should see the JSON response from the JSONPlaceholder posts endpoint:

```json
[
  {
    "userId": 1,
    "id": 1,
    "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
    "body": "quia et suscipit suscipit recusandae consequuntur expedita et cum reprehenderit molestiae ut ut quas totam nostrum rerum est autem sunt rem eveniet architecto"
  },
  ...
]
```

### Command Line Testing

You can also test using `curl`:

```bash
# Get all posts
curl http://localhost:8091

# Get specific post
curl http://localhost:8091/1
```

## Next Steps

Now that you have a working reverse proxy, you can:

- **Add Multiple Backends**: Configure load balancing between multiple servers
- **Implement Path Rewriting**: Modify request paths before forwarding
- **Add Middleware**: Include authentication, rate limiting, or logging
- **Configure HTTPS**: Set up SSL/TLS termination
- **Add Health Checks**: Monitor backend service availability

## Troubleshooting

**Common Issues:**

- **Port Already in Use**: Change the port number in `main.py` if 8091 is occupied
- **Configuration Errors**: Validate your `proxy.json` syntax using a JSON validator
- **Network Issues**: Ensure you have internet connectivity to reach the JSONPlaceholder API
- **Firewall Blocking**: Check if your firewall allows connections on port 8091

**Debugging Tips:**

- Check the console output for error messages when starting the proxy
- Verify the JSONPlaceholder API is accessible directly: `curl https://jsonplaceholder.typicode.com/posts`
- Test with simple tools like `curl` before using browsers

## Conclusion

Congratulations! You've successfully created your first reverse proxy. The proxy is now forwarding all requests to the JSONPlaceholder API, demonstrating the basic concepts of request routing and backend forwarding that form the foundation of more complex proxy configurations.