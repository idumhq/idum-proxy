import sys
import logging
import structlog
from structlog.stdlib import LoggerFactory


def configure_structlog():
    """Configure structlog with proper processors and formatting."""

    # Configure stdlib logging first
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            # Add context from structlog
            structlog.contextvars.merge_contextvars,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="ISO"),
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Format for console output
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class AsyncLogger:
    """Async-friendly structured logger using structlog."""

    def __init__(self, name: str | None = None):
        # Configure structlog if not already done
        if not structlog.is_configured():
            configure_structlog()

        # Create the logger
        self.logger = structlog.get_logger(name or __name__)

    async def log(self, level: str, message: str, **kwargs):
        """Log a message at the specified level with optional context."""
        log_method = getattr(self.logger, level.lower())
        log_method(message, **kwargs)

    async def info(self, message: str, **kwargs):
        """Log an info message."""
        self.logger.info(message, **kwargs)

    async def error(self, message: str, **kwargs):
        """Log an error message."""
        self.logger.error(message, **kwargs)

    async def debug(self, message: str, **kwargs):
        """Log a debug message."""
        self.logger.debug(message, **kwargs)

    async def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self.logger.warning(message, **kwargs)

    async def exception(self, message: str, exc_info: bool = True, **kwargs):
        """Log an exception with traceback."""
        self.logger.exception(message, exc_info=exc_info, **kwargs)

    def bind(self, **kwargs):
        """Bind context to the logger that will be included in all subsequent logs."""
        bound_logger = self.logger.bind(**kwargs)
        new_instance = AsyncLogger()
        new_instance.logger = bound_logger
        return new_instance

    def close(self):
        """Close method for compatibility - structlog doesn't require explicit cleanup."""
        pass


# Initialize structlog configuration
configure_structlog()

# Create an async logger instance
async_logger = AsyncLogger()
