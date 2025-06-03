"""
Structured logging setup with structlog
"""

from typing import Any

from idum_proxy.logger import setup_structlog, get_logger

# Example usage
if __name__ == "__main__":
    # Setup logging
    setup_structlog(log_level="DEBUG", json_logs=False)

    # Get logger
    logger = get_logger(__name__)

    # Basic logging
    logger.info("Application started")
    logger.debug("Debug information", user_id=123)

    # Structured context
    logger = logger.bind(request_id="abc-123", user_id=456)
    logger.info("Processing request", action="create_user")
    logger.warning("Rate limit approaching", current_rate=95, limit=100)

    # Error logging with exception
    try:
        result = 1 / 0
    except ZeroDivisionError:
        logger.error(
            "Division by zero occurred",
            operation="divide",
            dividend=1,
            divisor=0,
            exc_info=True,
        )

    # Proper way to use bound context
    batch_logger = logger.bind(operation="batch_process")
    batch_logger.info("Starting batch", batch_size=1000)
    for i in range(3):
        batch_logger.debug("Processing item", item_id=i)
    batch_logger.info("Batch completed", items_processed=3)


# Alternative: Custom logger class for more advanced usage
class StructuredLogger:
    """Wrapper class for structured logging with common patterns."""

    def __init__(self, name: str, context: dict[str, Any] | None = None):
        self.logger = get_logger(name)
        if context:
            self.logger = self.logger.bind(**context)

    def with_context(self, **kwargs) -> "StructuredLogger":
        """Return a new logger with additional context."""
        new_logger = StructuredLogger.__new__(StructuredLogger)
        new_logger.logger = self.logger.bind(**kwargs)
        return new_logger

    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self.logger.critical(message, **kwargs)


# Usage example with custom logger class
def example_with_custom_logger():
    setup_structlog(json_logs=True)

    # Application logger with base context
    app_logger = StructuredLogger(
        "myapp", {"service": "user-service", "version": "1.0.0"}
    )

    # Request-specific logger
    request_logger = app_logger.with_context(
        request_id="req-789", endpoint="/api/users", method="POST"
    )

    request_logger.info(
        "Request received", client_ip="192.168.1.1", user_agent="MyApp/1.0"
    )

    # Business logic logging
    user_logger = request_logger.with_context(user_id=123)
    user_logger.debug("Validating user data", fields=["email", "username"])
    user_logger.info("User created successfully", username="john_doe")

    request_logger.info("Request completed", status_code=201, response_time_ms=245)


# Configuration for different environments
def setup_production_logging():
    """Production-ready logging configuration."""
    setup_structlog(log_level="INFO", json_logs=True, include_timestamp=True)


def setup_development_logging():
    """Development logging with pretty console output."""
    setup_structlog(log_level="DEBUG", json_logs=False, include_timestamp=False)


# Context management patterns
def context_examples():
    """Examples of proper context management with structlog."""
    setup_structlog(json_logs=False)
    logger = get_logger(__name__)

    # Pattern 1: Bound logger for temporary context
    request_logger = logger.bind(request_id="req-123")
    request_logger.info("Request started")
    request_logger.info("Request completed")

    # Pattern 2: Function-scoped context
    def process_user(user_id: int):
        user_logger = logger.bind(user_id=user_id)
        user_logger.info("Processing user")
        user_logger.debug("Validating user data")
        return user_logger

    # Pattern 3: Using contextvars for automatic context propagation
    import contextvars
    import structlog.contextvars

    # Configure structlog with contextvars support
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # This merges contextvars
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Now you can use context variables
    request_id_var = contextvars.ContextVar("request_id")

    def handle_request():
        request_id_var.set("req-456")
        ctx_logger = get_logger(__name__)
        ctx_logger.info("This log will include request_id automatically")

        # Clear context
        structlog.contextvars.clear_contextvars()
        ctx_logger.info("This log won't include request_id")

    handle_request()
