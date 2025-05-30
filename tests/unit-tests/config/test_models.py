import pytest
from http import HTTPStatus, HTTPMethod
from pydantic import ValidationError

from idum_proxy.config.models import (
    RetryConfig,
    RateLimitRequests,
    RateLimitBurst,
    RateLimit,
    HttpsBackend,
    TcpBackend,
    CommandBackend,
    HealthCheck,
    StickySessions,
    LoadBalancing,
    ProtocolHeaders,
    HttpProtocolConfig,
    CircuitBreaker,
    FileCacheConfig,
    MemoryCacheConfig,
    CacheMiddleware,
    RedirectConfig,
    MockResponseTemplate,
    CronJob,
    Backends,
    UpstreamConfig,
    PerformanceMiddleware,
    Bot,
    BotFilterMiddleware,
    SecurityMiddleware,
    Middleware,
    TextReplacements,
    ResponseTransformer,
    Transformers,
    Endpoint,
    Config,
)


class TestRetryConfig:
    def test_retry_config_creation(self):
        retry = RetryConfig(count=3, delay_ms=1000, status_codes=[500, 502, 503])
        assert retry.count == 3
        assert retry.delay_ms == 1000
        assert retry.status_codes == [500, 502, 503]

    def test_retry_config_slots(self):
        retry = RetryConfig(count=3, delay_ms=1000, status_codes=[500])
        # Test that slots work by attempting to add new attribute
        with pytest.raises(AttributeError):
            retry.new_attr = "test"


class TestRateLimit:
    def test_rate_limit_creation(self):
        requests = RateLimitRequests(per_hour=1000, per_minute=100)
        burst = RateLimitBurst(max=50)
        rate_limit = RateLimit(requests=requests, burst=burst)

        assert rate_limit.requests.per_hour == 1000
        assert rate_limit.requests.per_minute == 100
        assert rate_limit.burst.max == 50


class TestHttpsBackend:
    def test_https_backend_defaults(self):
        backend = HttpsBackend(url="https://example.com")
        assert backend.url == "https://example.com"
        assert backend.id is None
        assert backend.weight == 0
        assert backend.ssl is True
        assert backend.timeout == 30
        assert backend.retries is None
        assert backend.rate_limiting is None
        assert backend.headers == {}
        assert backend.methods == ["GET"]

    def test_https_backend_with_all_params(self):
        retry = RetryConfig(count=3, delay_ms=1000, status_codes=[500])
        requests = RateLimitRequests(per_hour=1000, per_minute=100)
        burst = RateLimitBurst(max=50)
        rate_limit = RateLimit(requests=requests, burst=burst)

        backend = HttpsBackend(
            url="https://api.example.com",
            id="backend-1",
            weight=10,
            ssl=False,
            timeout=60,
            retries=retry,
            rate_limiting=rate_limit,
            headers={"Authorization": "Bearer token"},
            methods=[HTTPMethod.GET, HTTPMethod.POST],
        )

        assert backend.url == "https://api.example.com"
        assert backend.id == "backend-1"
        assert backend.weight == 10
        assert backend.ssl is False
        assert backend.timeout == 60
        assert backend.retries == retry
        assert backend.rate_limiting == rate_limit
        assert backend.headers == {"Authorization": "Bearer token"}
        assert backend.methods == [HTTPMethod.GET, HTTPMethod.POST]


class TestTcpBackend:
    def test_tcp_backend_creation(self):
        backend = TcpBackend(id="tcp-1", host="localhost", port=8080, weight=5)
        assert backend.id == "tcp-1"
        assert backend.host == "localhost"
        assert backend.port == 8080
        assert backend.weight == 5

    def test_tcp_backend_default_weight(self):
        backend = TcpBackend(id="tcp-1", host="localhost", port=8080)
        assert backend.weight == 0


class TestCommandBackend:
    def test_command_backend_creation(self):
        backend = CommandBackend(id="cmd-1", command="echo 'hello'")
        assert backend.id == "cmd-1"
        assert backend.command == "echo 'hello'"


class TestHealthCheck:
    def test_health_check_creation(self):
        health_check = HealthCheck(
            path="/health",
            interval_seconds=30,
            timeout_seconds=5,
            healthy_threshold=2,
            unhealthy_threshold=3,
        )
        assert health_check.path == "/health"
        assert health_check.interval_seconds == 30
        assert health_check.timeout_seconds == 5
        assert health_check.healthy_threshold == 2
        assert health_check.unhealthy_threshold == 3


class TestStickySessions:
    def test_sticky_sessions_creation(self):
        sticky = StickySessions(enabled=True, cookie_name="session_id", ttl_hours=24)
        assert sticky.enabled is True
        assert sticky.cookie_name == "session_id"
        assert sticky.ttl_hours == 24


class TestLoadBalancing:
    def test_load_balancing_creation(self):
        health_check = HealthCheck(
            path="/health",
            interval_seconds=30,
            timeout_seconds=5,
            healthy_threshold=2,
            unhealthy_threshold=3,
        )
        sticky = StickySessions(enabled=True, cookie_name="session_id", ttl_hours=24)

        lb = LoadBalancing(
            algorithm="round_robin", health_check=health_check, sticky_sessions=sticky
        )

        assert lb.algorithm == "round_robin"
        assert lb.health_check == health_check
        assert lb.sticky_sessions == sticky


class TestProtocolHeaders:
    def test_protocol_headers_creation(self):
        headers = ProtocolHeaders(**{"user-agent": "test-agent"})
        assert headers.user_agent == "test-agent"

    def test_protocol_headers_alias(self):
        headers = ProtocolHeaders(user_agent="test-agent")
        assert headers.user_agent == "test-agent"

    def test_protocol_headers_validation_error(self):
        with pytest.raises(ValidationError):
            ProtocolHeaders()  # Missing required field


class TestHttpProtocolConfig:
    def test_http_protocol_config_defaults(self):
        config = HttpProtocolConfig()
        assert config.methods == HTTPMethod.GET
        assert config.headers == {}

    def test_http_protocol_config_with_params(self):
        config = HttpProtocolConfig(
            methods=[HTTPMethod.GET, HTTPMethod.POST],
            headers={"Content-Type": "application/json"},
        )
        assert config.methods == [HTTPMethod.GET, HTTPMethod.POST]
        assert config.headers == {"Content-Type": "application/json"}


class TestCircuitBreaker:
    def test_circuit_breaker_creation(self):
        cb = CircuitBreaker(
            threshold=0.5, window_seconds=60, min_samples=10, reset_timeout_seconds=30
        )
        assert cb.threshold == 0.5
        assert cb.window_seconds == 60
        assert cb.min_samples == 10
        assert cb.reset_timeout_seconds == 30


class TestFileCacheConfig:
    def test_file_cache_config_defaults(self):
        cache = FileCacheConfig(
            path="/tmp/cache", ttl=3600, max_size_mb=100, max_entries=1000
        )
        assert cache.path == "/tmp/cache"
        assert cache.ttl == 3600
        assert cache.max_size_mb == 100
        assert cache.max_entries == 1000
        assert cache.enabled is True
        assert cache.include_patterns is None
        assert cache.exclude_patterns is None
        assert cache.cleanup_interval == "1h"

    def test_file_cache_config_with_patterns(self):
        cache = FileCacheConfig(
            path="/tmp/cache",
            ttl=3600,
            max_size_mb=100,
            max_entries=1000,
            include_patterns=["*.js", "*.css"],
            exclude_patterns=["*.tmp"],
        )
        assert cache.include_patterns == ["*.js", "*.css"]
        assert cache.exclude_patterns == ["*.tmp"]


class TestMemoryCacheConfig:
    def test_memory_cache_config_creation(self):
        cache = MemoryCacheConfig(
            max_items=1000, ttl=3600, include_patterns=["*.json"], max_item_size=1024
        )
        assert cache.max_items == 1000
        assert cache.ttl == 3600
        assert cache.include_patterns == ["*.json"]
        assert cache.max_item_size == 1024
        assert cache.enabled is True
        assert cache.exclude_patterns is None


class TestRedirectConfig:
    def test_redirect_config_defaults(self):
        redirect = RedirectConfig(location="https://example.com")
        assert redirect.location == "https://example.com"
        assert redirect.enabled is True
        assert redirect.status_code == HTTPStatus.FOUND
        assert redirect.preserve_path is True

    def test_redirect_config_custom(self):
        redirect = RedirectConfig(
            location="https://example.com",
            enabled=False,
            status_code=HTTPStatus.MOVED_PERMANENTLY,
            preserve_path=False,
        )
        assert redirect.location == "https://example.com"
        assert redirect.enabled is False
        assert redirect.status_code == HTTPStatus.MOVED_PERMANENTLY
        assert redirect.preserve_path is False


class TestMockResponseTemplate:
    def test_mock_response_template_defaults(self):
        template = MockResponseTemplate()
        assert template.status_code == 200
        assert template.headers is None
        assert template.body is None
        assert template.content_type == "application/json"
        assert template.delay_ms == 0

    def test_mock_response_template_custom(self):
        template = MockResponseTemplate(
            status_code=404,
            headers={"Content-Type": "text/plain"},
            body="Not found",
            content_type="text/plain",
            delay_ms=500,
        )
        assert template.status_code == 404
        assert template.headers == {"Content-Type": "text/plain"}
        assert template.body == "Not found"
        assert template.content_type == "text/plain"
        assert template.delay_ms == 500


class TestCronJob:
    def test_valid_cron_schedule(self):
        job = CronJob(
            schedule="0 9 * * 1", command="backup.sh", description="Daily backup"
        )
        assert job.schedule == "0 9 * * 1"
        assert job.command == "backup.sh"
        assert job.description == "Daily backup"

    def test_invalid_cron_schedule(self):
        with pytest.raises(ValidationError) as exc_info:
            CronJob(schedule="invalid", command="backup.sh", description="Daily backup")
        assert "Invalid cron schedule format" in str(exc_info.value)

    def test_cron_schedule_edge_cases(self):
        # Test valid edge cases
        valid_schedules = [
            "* * * * *",  # Every minute
            "0 0 1 1 0",  # Specific date
            "59 23 31 12 6",  # Max values
        ]

        for schedule in valid_schedules:
            job = CronJob(schedule=schedule, command="test.sh", description="Test job")
            assert job.schedule == schedule

    def test_cron_schedule_invalid_cases(self):
        invalid_schedules = [
            "60 * * * *",  # Invalid minute
            "* 24 * * *",  # Invalid hour
            "* * 32 * *",  # Invalid day
            "* * * 13 *",  # Invalid month
            "* * * * 7",  # Invalid weekday
            "* * * *",  # Too few fields
            "* * * * * *",  # Too many fields
        ]

        for schedule in invalid_schedules:
            with pytest.raises(ValidationError):
                CronJob(schedule=schedule, command="test.sh", description="Test job")


class TestBot:
    def test_bot_creation(self):
        bot = Bot(name="GoogleBot", **{"user-agent": "Googlebot/2.1"})
        assert bot.name == "GoogleBot"
        assert bot.user_agent == "Googlebot/2.1"

    def test_bot_alias(self):
        bot = Bot(name="GoogleBot", user_agent="Googlebot/2.1")
        assert bot.name == "GoogleBot"
        assert bot.user_agent == "Googlebot/2.1"


class TestBotFilterMiddleware:
    def test_bot_filter_middleware_creation(self):
        bots = [Bot(name="BadBot", user_agent="BadBot/1.0")]
        middleware = BotFilterMiddleware(blacklist=bots)
        assert middleware.blacklist == bots
        assert middleware.enabled is True
        assert middleware.whitelist == []

    def test_bot_filter_middleware_with_whitelist(self):
        blacklist = [Bot(name="BadBot", user_agent="BadBot/1.0")]
        whitelist = [Bot(name="GoodBot", user_agent="GoodBot/1.0")]
        middleware = BotFilterMiddleware(
            blacklist=blacklist, whitelist=whitelist, enabled=False
        )
        assert middleware.blacklist == blacklist
        assert middleware.whitelist == whitelist
        assert middleware.enabled is False


class TestEndpoint:
    def test_endpoint_creation(self):
        upstream = UpstreamConfig()
        endpoint = Endpoint(prefix="/api", match="/*", upstream=upstream)
        assert endpoint.prefix == "/api"
        assert endpoint.match == "/*"
        assert endpoint.upstream == upstream
        assert endpoint.identifier is None
        assert endpoint.weight == 100
        assert endpoint.backends is None
        assert endpoint.timeout == 30

    def test_endpoint_with_all_params(self):
        upstream = UpstreamConfig()
        backends = Backends()
        transformers = Transformers(
            response=ResponseTransformer(
                enabled=True,
                textReplacements=[TextReplacements(oldvalue="old", newvalue="new")],
            )
        )

        endpoint = Endpoint(
            prefix="/api/v1",
            match="/users/*",
            upstream=upstream,
            identifier="users-endpoint",
            weight=200,
            backends=backends,
            transformers=transformers,
            timeout=60.0,
        )

        assert endpoint.prefix == "/api/v1"
        assert endpoint.match == "/users/*"
        assert endpoint.upstream == upstream
        assert endpoint.identifier == "users-endpoint"
        assert endpoint.weight == 200
        assert endpoint.backends == backends
        assert endpoint.transformers == transformers
        assert endpoint.timeout == 60.0


class TestConfig:
    def test_config_creation(self):
        endpoint = Endpoint(prefix="/api", match="/*", upstream=UpstreamConfig())

        config = Config(name="test-proxy", version="1.0.0", endpoints=[endpoint])

        assert config.name == "test-proxy"
        assert config.version == "1.0.0"
        assert config.endpoints == [endpoint]
        assert config.timeout is None
        assert config.ssl is None
        assert config.middlewares is None

    def test_config_with_all_params(self):
        endpoint = Endpoint(prefix="/api", match="/*", upstream=UpstreamConfig())

        middleware = Middleware(
            performance=PerformanceMiddleware(), security=SecurityMiddleware()
        )

        config = Config(
            name="full-proxy",
            version="2.0.0",
            endpoints=[endpoint],
            timeout="30s",
            ssl=True,
            middlewares=middleware,
        )

        assert config.name == "full-proxy"
        assert config.version == "2.0.0"
        assert config.endpoints == [endpoint]
        assert config.timeout == "30s"
        assert config.ssl is True
        assert config.middlewares == middleware

    def test_config_validation_error(self):
        with pytest.raises(ValidationError):
            Config()  # Missing required fields

    def test_config_from_json(self):
        json_data = {
            "name": "json-proxy",
            "version": "1.0.0",
            "endpoints": [{"prefix": "/api", "match": "/*", "upstream": {}}],
        }

        config = Config(**json_data)
        assert config.name == "json-proxy"
        assert config.version == "1.0.0"
        assert len(config.endpoints) == 1
        assert config.endpoints[0].prefix == "/api"


class TestDataclassSlots:
    """Test that dataclasses with slots=True work correctly"""

    def test_dataclass_slots_prevent_new_attributes(self):
        retry = RetryConfig(count=3, delay_ms=1000, status_codes=[500])

        # Should not be able to add new attributes
        with pytest.raises(AttributeError):
            retry.new_attribute = "test"

    def test_dataclass_slots_memory_efficiency(self):
        """Test that slots reduce memory usage"""
        retry = RetryConfig(count=3, delay_ms=1000, status_codes=[500])

        # Slots should not have __dict__
        assert not hasattr(retry, "__dict__")


class TestComplexIntegration:
    """Integration tests with complex nested structures"""

    def test_full_config_integration(self):
        """Test creating a complete config with all components"""

        # Create retry config
        retry = RetryConfig(count=3, delay_ms=1000, status_codes=[500, 502])

        # Create rate limiting
        requests = RateLimitRequests(per_hour=1000, per_minute=100)
        burst = RateLimitBurst(max=50)
        rate_limit = RateLimit(requests=requests, burst=burst)

        # Create HTTPS backend
        https_backend = HttpsBackend(
            url="https://api.example.com",
            id="api-backend",
            weight=10,
            retries=retry,
            rate_limiting=rate_limit,
            headers={"Authorization": "Bearer token"},
        )

        # Create backends
        backends = Backends(https=https_backend)

        # Create middleware
        cache_middleware = CacheMiddleware(
            enabled=True,
            file=FileCacheConfig(
                path="/tmp/cache", ttl=3600, max_size_mb=100, max_entries=1000
            ),
        )

        performance_middleware = PerformanceMiddleware(cache=cache_middleware)
        middleware = Middleware(performance=performance_middleware)

        # Create endpoint
        endpoint = Endpoint(
            prefix="/api/v1",
            match="/*",
            upstream=UpstreamConfig(),
            backends=backends,
            weight=100,
        )

        # Create full config
        config = Config(
            name="integration-test",
            version="1.0.0",
            endpoints=[endpoint],
            middlewares=middleware,
        )

        # Verify the complete structure
        assert config.name == "integration-test"
        assert len(config.endpoints) == 1
        assert config.endpoints[0].backends.https.url == "https://api.example.com"
        assert config.endpoints[0].backends.https.retries.count == 3
        assert config.middlewares.performance.cache.enabled is True


if __name__ == "__main__":
    pytest.main([__file__])
