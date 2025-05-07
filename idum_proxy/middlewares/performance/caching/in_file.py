import json
import time
from pathlib import Path
from typing import Any

import aiofiles
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send
import asyncio
import os
import hashlib
from antpathmatcher import AntPathMatcher
from functools import lru_cache
from base64 import b64encode, b64decode
from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config


class InFileCacheMiddleware:
    """
    ASGI middleware that caches responses in the file system.
    Uses Ant-style path matching for determining which paths to cache.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Config,
        ttl: int = 86400,  # 24 hours in seconds
        max_size_mb: int = 1024,
        max_entries: int = 10000,
        cleanup_interval: int = 3600,  # 1 hour
    ) -> None:
        self.app = app
        self.config = config
        self.ttl = ttl
        self.max_size_mb = max_size_mb
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self.antpathmatcher = AntPathMatcher()
        self.cache_dir = Path(".cache/pip")

        # Cache config (to avoid deep property checks on every request)
        self.cache_enabled = False
        self.include_patterns = []
        asyncio.create_task(self._load_config())

        # Memory cache for content (critical optimization)
        self.content_cache = {}  # {cache_key: (timestamp, cache_data)}
        self.content_cache_max_size = 1000  # Limit cache size

        # Ensure cache directory exists - do it in a non-blocking way
        asyncio.create_task(self._ensure_cache_dir())

        # Create a cleanup lock to prevent concurrent cleanup
        self.cleanup_lock = asyncio.Lock()

        # Start background tasks
        self.cleanup_task = None
        if self.cache_enabled:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Profiling stats
        self.hits = 0
        self.misses = 0
        self.memory_hits = 0

    async def _ensure_cache_dir(self):
        """Ensure cache directory exists in a non-blocking way"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: os.makedirs(self.cache_dir, exist_ok=True)
        )

    async def _load_config(self):
        """Load and cache configuration settings"""
        config = self.config

        try:
            if (
                hasattr(config, "middlewares")
                and hasattr(config.middlewares, "performance")
                and hasattr(config.middlewares.performance, "cache")
                and hasattr(config.middlewares.performance.cache, "file")
                and config.middlewares.performance
                and config.middlewares.performance.cache
                and config.middlewares.performance.cache.file
                and config.middlewares.performance.cache.file.enabled is True
            ):
                self.cache_enabled = True
                cache_file_config = config.middlewares.performance.cache.file
                self.include_patterns = cache_file_config.include_patterns
            else:
                self.cache_enabled = False
                self.include_patterns = []
        except Exception as e:
            await async_logger.error(f"Error loading cache config: {e}")
            self.cache_enabled = False
            self.include_patterns = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Quick bailout conditions
        if (
            not self.cache_enabled
            or scope["type"] != "http"
            or scope["method"] != "GET"
        ):
            await self.app(scope, receive, send)
            return

        # Check if path should be cached based on patterns (use cached function)
        path = scope["path"]
        if not self._should_cache_path(path):
            await self.app(scope, receive, send)
            return

        # Generate cache key
        query_string = scope.get("query_string", b"").decode()
        cache_key = self._generate_cache_key(path, query_string)

        # Check memory cache first (fastest)
        """
        curr_time = time.time()
        if cache_key in self.content_cache:
            timestamp, cache_data = self.content_cache[cache_key]
            if curr_time - timestamp <= self.ttl:
                logger.info(f"Memory cache hit for {path}")
                self.hits += 1
                self.memory_hits += 1
                await self._send_cached_response(cache_data, send)
                return
        """

        # Check file cache
        cache_file = self.cache_dir / cache_key
        cache_data = await self._get_cached_response(cache_file, cache_key)
        if cache_data:
            await async_logger.info(f"File cache hit for {path}")
            self.hits += 1
            cache_data["content"] = b64decode(cache_data["content"])
            await self._send_cached_response(cache_data, send)
            return

        # Cache miss
        self.misses += 1

        # Process the request through the app and capture the response
        response_sent = False
        response_body = bytearray()

        async def send_wrapper(message):
            nonlocal response_sent, response_body

            if message["type"] == "http.response.start":
                # Store response headers and status for caching
                self.response_status = message["status"]
                self.response_headers = MutableHeaders(raw=message.get("headers", []))
                response_sent = True

            elif message["type"] == "http.response.body" and response_sent:
                # Only cache successful responses
                if 200 <= self.response_status < 400:
                    body = message.get("body", b"")
                    more_body = message.get("more_body", False)

                    # Collect body chunks
                    if body:
                        response_body.extend(body)

                    # Only cache complete responses
                    if not more_body and response_body:
                        # Don't wait for caching to complete
                        asyncio.create_task(
                            self._cache_response(
                                cache_key,
                                cache_file,
                                self.response_status,
                                dict(self.response_headers),
                                bytes(response_body),
                            )
                        )

            # Forward the message to the client
            await send(message)

        # Process the request with our wrapper
        await self.app(scope, receive, send_wrapper)

    @lru_cache(maxsize=1000)
    def _should_cache_path(self, path: str) -> bool:
        """Optimized path matching with caching"""
        for pattern in self.include_patterns:
            if self.antpathmatcher.match(pattern, path):
                return True
        return False

    @staticmethod
    def _generate_cache_key(path: str, query_string: str) -> str:
        """Generate a unique cache key based on request path and query string."""
        key_base = f"{path}?{query_string}" if query_string else path
        return hashlib.md5(key_base.encode()).hexdigest()

    async def _get_cached_response(
        self, cache_file: Path, cache_key: str
    ) -> dict | None:
        """Optimized cache reading with memory caching"""
        try:
            # Check if file exists using async io
            loop = asyncio.get_event_loop()
            file_exists = await loop.run_in_executor(None, os.path.exists, cache_file)
            if not file_exists:
                return None

            # Read cache data
            async with aiofiles.open(cache_file, "rb") as f:
                content = await f.read()
                cache_data = json.loads(content)

            # Check if cache has expired
            curr_time = time.time()
            if curr_time - cache_data["timestamp"] > self.ttl:
                # Expired - schedule deletion but don't wait
                asyncio.create_task(self._delete_file(cache_file))
                return None

            # Cache in memory for faster access next time
            self.content_cache[cache_key] = (curr_time, cache_data)

            # Keep memory cache size in check
            if len(self.content_cache) > self.content_cache_max_size:
                # Remove 20% of the oldest entries
                to_remove = int(self.content_cache_max_size * 0.2)
                oldest_keys = sorted(
                    self.content_cache.keys(), key=lambda k: self.content_cache[k][0]
                )[:to_remove]
                for k in oldest_keys:
                    self.content_cache.pop(k, None)

            return cache_data

        except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
            await async_logger.debug(f"Cache read error: {e}")
            return None

    async def _delete_file(self, file_path: Path) -> None:
        """Delete file asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            if await loop.run_in_executor(None, os.path.exists, file_path):
                await loop.run_in_executor(None, os.remove, file_path)
        except Exception as e:
            await async_logger.error(f"Error deleting file: {e}")

    async def _send_cached_response(self, cache_data: dict, send: Send) -> None:
        """Send a cached response to the client."""
        # Reconstruct headers
        headers = []
        for name, value in cache_data["headers"].items():
            if isinstance(value, list):
                for v in value:
                    headers.append((name.encode(), v.encode()))
            else:
                if name == "content-length":
                    headers.append((name.encode(), str(len(cache_data["content"]))))
                else:
                    headers.append((name.encode(), value.encode()))

        # Add cache status header
        headers.append((b"x-cache-status", b"HIT"))

        # Send response
        await send(
            {
                "type": "http.response.start",
                "status": cache_data["status_code"],
                "headers": headers,
            }
        )

        # Send response body
        content = cache_data["content"]
        if isinstance(content, str):
            content = content.encode()

        await send({"type": "http.response.body", "body": content})

    async def _cache_response(
        self,
        cache_key: str,
        cache_file: Path,
        status_code: int,
        headers: dict[str, str | list[str]],
        body: bytes,
    ) -> None:
        """Cache the response data to file asynchronously."""
        try:
            # Store response data
            cache_data = {
                "timestamp": time.time(),
                "status_code": status_code,
                "content": b64encode(body).decode(),
                "headers": headers,
            }

            # Store in memory cache
            self.content_cache[cache_key] = (time.time(), cache_data)

            # Write to cache file
            content = json.dumps(cache_data)
            loop = asyncio.get_event_loop()

            # Ensure directory exists (might be needed if cache is cleared)
            await loop.run_in_executor(
                None, lambda: os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            )

            # Write file
            async with aiofiles.open(cache_file, "w") as f:
                await f.write(content)

            # Check if we need cleanup - but don't block on it
            total_entries = len(self.content_cache)
            if total_entries % 10 == 0:  # Only check periodically
                asyncio.create_task(self._maybe_cleanup_cache())

        except Exception as e:
            await async_logger.error(f"Error caching response: {e}")

    async def _maybe_cleanup_cache(self) -> None:
        """Non-blocking check if cleanup is needed"""
        if self.cleanup_lock.locked():
            return  # Skip if cleanup is already running

        # Use fast async checks
        try:
            loop = asyncio.get_event_loop()
            cache_count = await loop.run_in_executor(
                None, lambda: sum(1 for _ in self.cache_dir.glob("*"))
            )

            if cache_count > self.max_entries * 0.9:
                # Need to clean up, but don't wait for it
                asyncio.create_task(self._run_cleanup())
        except Exception as e:
            await async_logger.error(f"Error checking cache size: {e}")

    async def _run_cleanup(self) -> None:
        """Run cache cleanup with a lock to prevent concurrent cleanup"""
        if self.cleanup_lock.locked():
            return  # Another cleanup is already running

        async with self.cleanup_lock:
            try:
                # First remove expired entries from memory cache
                current_time = time.time()
                expired_keys = [
                    k
                    for k, (timestamp, _) in self.content_cache.items()
                    if current_time - timestamp > self.ttl
                ]

                for k in expired_keys:
                    self.content_cache.pop(k, None)

                # Then check disk cache (in background)
                await self._cleanup_cache()
            except Exception as e:
                await async_logger.error(f"Error in cleanup: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up expired items."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._run_cleanup()
                # Log stats
                await async_logger.info(
                    f"Cache stats: hits={self.hits}, memory_hits={self.memory_hits}, "
                    f"misses={self.misses}, cache_size={len(self.content_cache)}"
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                await async_logger.error(f"Error in cache cleanup loop: {e}")

    async def _cleanup_cache(self) -> None:
        """Clean up expired cache entries efficiently"""
        await async_logger.info("Running cache cleanup")
        loop = asyncio.get_event_loop()

        # Get all file info in one call using os.listdir (faster than glob)
        try:
            all_files = await loop.run_in_executor(None, os.listdir, self.cache_dir)
            current_time = time.time()
            files_removed = 0

            # Process files in batches
            batch_size = 50
            for i in range(0, len(all_files), batch_size):
                batch = all_files[i : i + batch_size]

                for filename in batch:
                    file_path = os.path.join(self.cache_dir, filename)

                    try:
                        # Fast check if this file is in our memory cache
                        if filename in self.content_cache:
                            timestamp, _ = self.content_cache[filename]
                            if current_time - timestamp <= self.ttl:
                                continue  # Still valid
                            else:
                                # Expired in memory, remove from both caches
                                self.content_cache.pop(filename, None)

                        # Check file
                        if not await loop.run_in_executor(
                            None, os.path.isfile, file_path
                        ):
                            continue

                        # Quick timestamp check without reading whole file
                        stat = await loop.run_in_executor(None, os.stat, file_path)

                        # Use mtime as a fast approximation
                        if (
                            current_time - stat.st_mtime > self.ttl * 1.1
                        ):  # Add 10% buffer
                            # Almost certainly expired, delete it
                            await loop.run_in_executor(None, os.remove, file_path)
                            files_removed += 1
                            continue

                        # If we're still not sure, check the content
                        if stat.st_size > 0:  # Skip empty files
                            # Read just enough to get the timestamp
                            async with aiofiles.open(file_path, "r") as f:
                                # Read just first 100 bytes to check for timestamp
                                try:
                                    data = await f.read(100)
                                    # Quick check for timestamp field without full parsing
                                    if '"timestamp":' in data:
                                        timestamp_pos = data.find('"timestamp":') + 12
                                        timestamp_end = data.find(",", timestamp_pos)
                                        if timestamp_end == -1:
                                            timestamp_end = data.find(
                                                "}", timestamp_pos
                                            )
                                        if timestamp_end > timestamp_pos:
                                            timestamp_str = data[
                                                timestamp_pos:timestamp_end
                                            ].strip()
                                            try:
                                                timestamp = float(timestamp_str)
                                                if current_time - timestamp > self.ttl:
                                                    await loop.run_in_executor(
                                                        None, os.remove, file_path
                                                    )
                                                    files_removed += 1
                                            except ValueError:
                                                pass
                                except Exception as e:
                                    await async_logger.exception(e)
                                    # If reading fails, just delete the file
                                    await loop.run_in_executor(
                                        None, os.remove, file_path
                                    )
                                    files_removed += 1
                    except Exception as e:
                        await async_logger.debug(
                            f"Error checking cache file {filename}: {e}"
                        )

                # Yield after each batch
                await asyncio.sleep(0)

            await async_logger.info(f"Removed {files_removed} expired cache entries")

        except Exception as e:
            await async_logger.error(f"Error during cache cleanup: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the cache."""
        loop = asyncio.get_event_loop()

        try:
            # Get file count and size
            all_files = await loop.run_in_executor(None, os.listdir, self.cache_dir)

            total_size = 0
            for filename in all_files:
                try:
                    file_path = os.path.join(self.cache_dir, filename)
                    if await loop.run_in_executor(None, os.path.isfile, file_path):
                        stat = await loop.run_in_executor(None, os.stat, file_path)
                        total_size += stat.st_size
                except Exception as e:
                    await async_logger.exception(e)
                    pass
        except Exception as e:
            await async_logger.exception(e)

            all_files = []
            total_size = 0

        return {
            "entries": len(all_files),
            "memory_entries": len(self.content_cache),
            "size_bytes": total_size,
            "size_mb": total_size / (1024 * 1024),
            "max_entries": self.max_entries,
            "max_size_mb": self.max_size_mb,
            "ttl": self.ttl,
            "hits": self.hits,
            "memory_hits": self.memory_hits,
            "misses": self.misses,
            "hit_ratio": self.hits / (self.hits + self.misses)
            if (self.hits + self.misses) > 0
            else 0,
            "include_patterns": self.include_patterns,
            "cache_directory": str(self.cache_dir),
        }
