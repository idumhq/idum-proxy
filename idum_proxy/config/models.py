import re
from dataclasses import dataclass, field
from http import HTTPStatus, HTTPMethod
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


@dataclass(slots=True)
class RetryConfig:
    count: int
    delay_ms: int
    status_codes: list[int]


@dataclass(slots=True)
class RateLimitRequests:
    per_hour: int
    per_minute: int


@dataclass(slots=True)
class RateLimitBurst:
    max: int


@dataclass(slots=True)
class RateLimit:
    requests: RateLimitRequests
    burst: RateLimitBurst


@dataclass(slots=True)
class HttpsBackend:
    url: str
    id: str | None = None
    weight: int = 0
    ssl: bool = True
    timeout: int = 30
    retries: RetryConfig | None = None
    rate_limiting: RateLimit | None = None
    headers: dict[str, str] = field(default_factory=dict)
    methods: list[HTTPMethod] = field(default_factory=lambda: ["GET"])


@dataclass(slots=True)
class TcpBackend:
    id: str
    host: str
    port: int
    weight: int = 0


@dataclass(slots=True)
class CommandBackend:
    id: str
    command: str


@dataclass(slots=True)
class HealthCheck:
    path: str
    interval_seconds: int
    timeout_seconds: int
    healthy_threshold: int
    unhealthy_threshold: int


@dataclass(slots=True)
class StickySessions:
    enabled: bool
    cookie_name: str
    ttl_hours: int


@dataclass(slots=True)
class LoadBalancing:
    algorithm: str
    health_check: HealthCheck
    sticky_sessions: StickySessions | None = None


class ProtocolHeaders(BaseModel):
    user_agent: str = Field(..., alias="user-agent")

    class Config:
        populate_by_name = True


@dataclass(slots=True)
class HttpProtocolConfig:
    methods: list[HTTPMethod] = field(default_factory=lambda: HTTPMethod.GET)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Protocols:
    https: HttpProtocolConfig = field(default_factory=HttpProtocolConfig)


@dataclass(slots=True)
class CircuitBreaker:
    threshold: float
    window_seconds: int
    min_samples: int
    reset_timeout_seconds: int


@dataclass(slots=True)
class FileCacheConfig:
    path: str
    ttl: int
    max_size_mb: int
    max_entries: int
    enabled: bool = True
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    cleanup_interval: str = "1h"


@dataclass(slots=True)
class MemoryCacheConfig:
    max_items: int
    ttl: int
    include_patterns: list[str]
    max_item_size: int
    enabled: bool = True
    exclude_patterns: list[str] | None = None


@dataclass(slots=True)
class CacheMiddleware:
    enabled: bool = True
    file: FileCacheConfig | None = None
    memory: MemoryCacheConfig | None = None


@dataclass(slots=True)
class ResourceFilterMiddleware:
    skip_paths: list[str]
    enabled: bool = True


@dataclass(slots=True)
class CompressionMiddleware:
    types: list[str]
    enabled: bool = True
    compress_level: int = 9
    min_size: int = 500


@dataclass(slots=True)
class CircuitBreakerMiddleware:
    enabled: bool = True


@dataclass(slots=True)
class ProxyConfig:
    enabled: bool = True
    timeout_seconds: int = 30


@dataclass(slots=True)
class VirtualSourceConfig:
    sources: list[str]
    enabled: bool = True
    strategy: str = "first-match"


@dataclass(slots=True)
class FileBackendConfig:
    path: str
    enabled: bool = True


@dataclass(slots=True)
class RedirectConfig:
    location: str
    enabled: bool = True
    status_code: int = HTTPStatus.FOUND
    preserve_path: bool = True


@dataclass(slots=True)
class MockResponseTemplate:
    status_code: int = 200
    headers: dict[str, str] | None = None
    body: str | dict[str, Any] | None = None
    content_type: str = "application/json"
    delay_ms: int = 0


@dataclass(slots=True)
class MockConfig:
    path_templates: dict[str, MockResponseTemplate]
    enabled: bool = True
    default_response: MockResponseTemplate | None = None


@dataclass(slots=True)
class FunctionConfig:
    runtime: str
    handler: str
    code_path: str
    enabled: bool = True
    environment: dict[str, str] | None = None
    timeout_seconds: int = 30
    memory_mb: int = 128


@dataclass(slots=True)
class WebSocketConfig:
    enabled: bool = True
    ping_interval_seconds: int = 30
    timeout_seconds: int = 60
    max_frame_size: int = 1048576


@dataclass(slots=True)
class GraphQLConfig:
    schema_path: str
    resolvers: dict[str, str]
    enabled: bool = True
    introspection: bool = True
    playground: bool = False


@dataclass(slots=True)
class EchoConfig:
    enabled: bool = True
    add_headers: dict[str, str] | None = None
    response_delay_ms: int = 0


@dataclass(slots=True)
class ServiceMeshConfig:
    service_name: str
    namespace: str
    enabled: bool = True
    protocol: str = "http"
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class JobHistory:
    storage_type: str | None = None
    path: str | None = None
    retention_hours: int = 24


class CronJob(BaseModel):
    schedule: str = Field(..., description="Cron schedule expression")
    command: str = Field(..., description="Command to execute")
    description: str = Field(..., description="Human-readable job description")

    @field_validator("schedule")
    @classmethod
    def validate_cron_schedule(cls, v: str) -> str:
        """Validate cron schedule format (5 fields: minute hour day month weekday)"""
        cron_pattern = r"^(\*|([0-5]?\d)) (\*|([01]?\d|2[0-3])) (\*|([12]?\d|3[01])) (\*|([1-9]|1[0-2])) (\*|[0-6])$"
        if not re.match(cron_pattern, v):
            raise ValueError(f"Invalid cron schedule format: {v}")
        return v


@dataclass(slots=True)
class SchedulerConfig:
    cron_jobs: dict[str, CronJob] = Field(
        ..., description="Dictionary of cron jobs with arbitrary keys"
    )
    enabled: bool = True
    job_history: JobHistory | None = None


@dataclass(slots=True)
class Backends:
    https: HttpsBackend | list[HttpsBackend] | None = None
    tcp: TcpBackend | None = None
    command: CommandBackend | None = None
    file: FileBackendConfig | None = None
    redirect: RedirectConfig | None = None
    echo: EchoConfig | None = None
    mock: MockConfig | None = None
    scheduler: SchedulerConfig | None = None


@dataclass(slots=True)
class UpstreamConfig:
    proxy: ProxyConfig | None = None
    virtual: VirtualSourceConfig | None = None
    websocket: WebSocketConfig | None = None
    graphql: GraphQLConfig | None = None
    service_mesh: ServiceMeshConfig | None = None
    function: FunctionConfig | None = None
    # database: DatabaseConfig | None = None
    # cache: CacheMiddleware | None = None
    # queue: CacheMiddleware | None = None
    # load_balancer: LoadBalancer | None = None
    # webhook: Webhook | None = None

    # file: FileBackendConfig | None = None
    # redirect: RedirectConfig | None = None
    # echo: EchoConfig | None = None
    # mock: MockConfig | None = None

    command: CommandBackend | None = None
    # retry: RetryConfig | None = None
    # rewrite_headers: dict[str, str] | None = None
    # add_headers: dict[str, str] | None = None
    # remove_headers: list[str] | None = None


@dataclass(slots=True)
class PerformanceMiddleware:
    resource_filter: ResourceFilterMiddleware | None = None
    compression: CompressionMiddleware | None = None
    cache: CacheMiddleware | None = None
    circuit_breaking: CircuitBreakerMiddleware | None = None


class Bot(BaseModel):
    name: str
    user_agent: str = Field(alias="user-agent")

    class Config:
        populate_by_name = True


@dataclass(slots=True)
class BotFilterMiddleware:
    blacklist: list[Bot]
    enabled: bool = True
    whitelist: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class IpFilterMiddleware:
    blacklist: list[str]
    enabled: bool = True


@dataclass(slots=True)
class SecurityMiddleware:
    ip_filter: IpFilterMiddleware | None = None
    bot_filter: BotFilterMiddleware | None = None


@dataclass(slots=True)
class Middleware:
    performance: PerformanceMiddleware | None = None
    security: SecurityMiddleware | None = None


@dataclass(slots=True)
class TextReplacements:
    oldvalue: str
    newvalue: str


@dataclass(slots=True)
class ResponseTransformer:
    enabled: bool
    textReplacements: list[TextReplacements]


@dataclass(slots=True)
class Transformers:
    response: ResponseTransformer


@dataclass(slots=True)
class Logging:
    level: str
    request_headers: list[str]
    response_headers: list[str]
    exclude_body: bool


@dataclass(slots=True)
class Auth:
    type: str
    header_name: str
    required: bool


@dataclass(slots=True)
class CORS:
    allowed_origins: list[str]
    allowed_methods: list[str]
    allowed_headers: list[str]
    max_age_seconds: int
    enabled: bool


@dataclass(slots=True)
class PrometheusConfig:
    metrics: list[str]
    enabled: bool


@dataclass(slots=True)
class Monitoring:
    health_check_path: str
    metrics_path: str
    backends_status_path: str
    prometheus: PrometheusConfig


@dataclass(slots=True)
class Failover:
    fallback_policy: str
    max_fallbacks: int
    enabled: bool


@dataclass(slots=True)
class Endpoint:
    prefix: str
    match: str
    upstream: UpstreamConfig
    identifier: str | None = None
    weight: int = 100
    backends: Backends | list[Backends] | None = None
    transformers: Transformers | None = None
    logging: Logging | None = None
    auth: Auth | None = None
    cors: CORS | None = None
    monitoring: Monitoring | None = None
    failover: Failover | None = None
    timeout: float = 30


class ServerConfig(BaseModel):
    type: Literal["uvicorn", "gunicorn", "local"] = "gunicorn"
    workers: int = Field(default=2, ge=1)


# Keep Config as BaseModel for easy JSON parsing
class Config(BaseModel):
    name: str
    version: str
    server: ServerConfig = Field(default_factory=ServerConfig)
    endpoints: list[Endpoint]
    timeout: str | None = None
    ssl: bool | None = None
    middlewares: Middleware | None = None
