import time
import asyncio

from starlette.requests import Request
from starlette.types import Scope, Receive, Send, ASGIApp

from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config


class InMemoryCacheMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        config: Config,
        ttl: int = 60,
        exclude_paths: list[str] | None = None,
        exclude_methods: list[str] | None = None,
    ):
        """
        Initialize the in-memory cache middleware.

        Args:
            app: The ASGI application
            ttl: Time to live in seconds for cached items (default: 60s)
            exclude_paths: List of paths to exclude from caching
            exclude_methods: List of HTTP methods to exclude from caching
        """
        self.app = app
        self.ttl = ttl
        self.exclude_paths = exclude_paths or []
        self.exclude_methods = exclude_methods or ["POST", "PUT", "DELETE", "PATCH"]
        # Cache structure: {cache_key: {"data": response_data, "expires_at": timestamp}}
        self.cache = {}
        self.config = config

        """
        # Register cleanup task
        @app.on_event("startup")
        async def start_cache_cleanup():
            self.cleanup_task = app.add_task(self._cleanup_expired_cache())

        @app.on_event("shutdown")
        async def stop_cache_cleanup():
            self.cleanup_task.cancel()
        """

    async def _cleanup_expired_cache(self):
        """Periodically remove expired items from cache"""
        while True:
            try:
                current_time = time.time()
                keys_to_remove = []

                for key, value in self.cache.items():
                    if value["expires_at"] < current_time:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.cache[key]

                await async_logger.debug(
                    f"Cache cleanup: removed {len(keys_to_remove)} expired items"
                )
                await asyncio.sleep(
                    self.ttl / 2
                )  # Run cleanup at half the TTL interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                await async_logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    """
    def _generate_cache_key(self, request: Request) -> str:
        Generate a unique cache key based on request method, path, and query params
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()
    """

    def _should_cache(self, request: Request) -> bool:
        """Determine if the request should be cached"""
        # Don't cache excluded methods
        if request.method in self.exclude_methods:
            return False

        # Don't cache excluded paths
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return False

        return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await async_logger.info("Call InMemoryCacheMiddleware")

        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
        return
        """
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        current_time = time.time()

        # Check if we have a valid cached response
        if (
            cache_key in self.cache
            and self.cache[cache_key]["expires_at"] > current_time
        ):
            cached_data = self.cache[cache_key]["data"]
            logger.debug(f"Cache hit: {request.url.path}")
            return JSONResponse(content=cached_data)

        # No cache hit, get the response from the application
        response = await call_next(request)

        # Only cache successful JSON responses
        if (
            response.status_code == 200
            and response.headers.get("content-type") == "application/json"
        ):
            # Need to read the response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Parse JSON data from response
            import json

            response_data = json.loads(response_body.decode())

            # Store in cache
            self.cache[cache_key] = {
                "data": response_data,
                "expires_at": current_time + self.ttl,
            }
            logger.debug(f"Cache set: {request.url.path}")

            # Return a new response with the same data
            return JSONResponse(
                content=response_data,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        return response
        """
