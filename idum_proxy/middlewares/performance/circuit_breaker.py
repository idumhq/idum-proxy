from http import HTTPStatus
import time

from antpathmatcher import AntPathMatcher
from starlette.types import ASGIApp, Receive, Scope, Send


from starlette.responses import Response

from idum_proxy.async_logger import async_logger
from idum_proxy.config.models import Config


class CircuitBreakingMiddleware:
    """Performance middleware for implementing circuit breaking patterns in the API proxy.

    This middleware improves system reliability and performance by:
    1. Skipping processing for configured paths to reduce load
    2. Implementing circuit breaking to prevent cascading failures
    3. Managing traffic during high load situations
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Config,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.config = config
        self.antpathmatcher = AntPathMatcher()
        self.exclude_paths = exclude_paths or []

        # Performance tracking
        self.failure_counts = {}
        self.response_times = {}
        self.last_reset_time = time.time()
        self.reset_interval = 60  # Reset counters every 60 seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        await async_logger.info("Call CircuitBreakingMiddleware")

        config = self.config
        path = scope["path"].lstrip("/")

        # Reset counters if needed
        current_time = time.time()
        if current_time - self.last_reset_time > self.reset_interval:
            await self._reset_counters()

        # Check if circuit breaking is enabled in config
        if (
            hasattr(config, "middlewares")
            and hasattr(config.middlewares, "performance")
            and hasattr(config.middlewares.performance, "circuit_breaking")
            and config.middlewares.performance
            and config.middlewares.performance.circuit_breaking
            and config.middlewares.performance.circuit_breaking.enabled is True
        ):
            # Resource optimization: Skip processing for defined paths
            if hasattr(config.middlewares.performance, "resource_filter") and hasattr(
                config.middlewares.performance.resource_filter, "skip_paths"
            ):
                skip_paths = config.middlewares.performance.resource_filter.skip_paths

                if any(
                    self.antpathmatcher.match(skip_path, path)
                    for skip_path in skip_paths
                ):
                    await async_logger.debug(
                        f"Resource optimization: skipping processing for path: {path}"
                    )
                    response = Response(
                        status_code=HTTPStatus.NO_CONTENT  # 204
                    )
                    await response(scope, receive, send)
                    return

            # Check if the path matches any exclude paths from parameters
            if any(
                self.antpathmatcher.match(exclude_path, path)
                for exclude_path in self.exclude_paths
            ):
                await async_logger.debug(
                    f"Path {path} excluded from circuit breaking by middleware parameter"
                )
                await self.app(scope, receive, send)
                return

            # Performance protection: Check if circuit breaker is triggered based on load metrics
            if self._is_circuit_open(path):
                await async_logger.warning(
                    f"Circuit breaker triggered for path: {path} - protecting system resources"
                )
                response = Response(
                    content="Service temporarily unavailable due to high load",
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,  # 503
                )
                await response(scope, receive, send)
                return

        # Wrap the send function to track performance metrics
        original_send = send
        start_time = time.time()

        async def wrapped_send(message):
            if message.get("type") == "http.response.start":
                status = message.get("status", 200)
                if status >= 500:
                    self._record_failure(path)

                response_time = time.time() - start_time
                self._record_response_time(path, response_time)

            await original_send(message)

        # Default behavior - pass through to the application with wrapped send
        await self.app(scope, receive, wrapped_send)

    def _is_circuit_open(self, path: str) -> bool:
        """
        Determine if the circuit is open for a specific path based on performance metrics.

        A circuit is considered open when:
        - Error rate exceeds threshold
        - Response times are too high
        - System load exceeds capacity

        Returns:
            bool: True if circuit is open (requests should be blocked), False otherwise
        """
        config = self.idum_proxy.config

        # Get thresholds from config or use defaults
        failure_threshold = 5
        response_time_threshold = 2.0  # seconds

        if hasattr(config.middlewares.performance.circuit_breaking, "thresholds"):
            thresholds = config.middlewares.performance.circuit_breaking.thresholds
            if hasattr(thresholds, "failure_count"):
                failure_threshold = thresholds.failure_count
            if hasattr(thresholds, "response_time"):
                response_time_threshold = thresholds.response_time

        # Check failure counts
        if (
            path in self.failure_counts
            and self.failure_counts[path] >= failure_threshold
        ):
            return True

        # Check response times
        if path in self.response_times:
            avg_response_time = sum(self.response_times[path]) / len(
                self.response_times[path]
            )
            if avg_response_time > response_time_threshold:
                return True

        # Check specific service configurations
        if hasattr(config.middlewares.performance.circuit_breaking, "services"):
            services = config.middlewares.performance.circuit_breaking.services
            for service in services:
                if (
                    hasattr(service, "path_pattern")
                    and hasattr(service, "is_open")
                    and self.antpathmatcher.match(service.path_pattern, path)
                ):
                    # Manual override from config
                    if service.is_open:
                        return True

                    # Check if service has specific thresholds
                    if (
                        hasattr(service, "thresholds")
                        and path in self.failure_counts
                        and hasattr(service.thresholds, "failure_count")
                        and self.failure_counts[path]
                        >= service.thresholds.failure_count
                    ):
                        return True

        return False

    def _record_failure(self, path: str) -> None:
        """Record a failure for the specified path"""
        if path not in self.failure_counts:
            self.failure_counts[path] = 1
        else:
            self.failure_counts[path] += 1

    def _record_response_time(self, path: str, response_time: float) -> None:
        """Record a response time for the specified path"""
        if path not in self.response_times:
            self.response_times[path] = [response_time]
        else:
            # Keep only the last 10 response times
            if len(self.response_times[path]) >= 10:
                self.response_times[path].pop(0)
            self.response_times[path].append(response_time)

    async def _reset_counters(self) -> None:
        """Reset all counters periodically"""
        self.failure_counts = {}
        self.response_times = {}
        self.last_reset_time = time.time()
        await async_logger.debug("Circuit breaker counters reset")
