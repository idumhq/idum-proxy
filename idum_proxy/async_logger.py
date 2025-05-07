import sys
import logging
import queue
from logging.handlers import QueueHandler, QueueListener

# Configure the root logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
logger.addHandler(ch)


class AsyncLogger:
    def __init__(self):
        # Create a queue for log messages
        self.log_queue = queue.Queue()

        # Create a QueueHandler that puts log records in the queue
        queue_handler = QueueHandler(self.log_queue)

        # Create a separate logger for the queue handler
        self.queue_logger = logging.getLogger(f"{__name__}.queue")
        self.queue_logger.setLevel(logging.DEBUG)
        self.queue_logger.addHandler(queue_handler)

        # Create a QueueListener that processes records from the queue
        self.queue_listener = QueueListener(
            self.log_queue, ch, respect_handler_level=True
        )

        # Start the listener in a separate thread
        self.queue_listener.start()

    async def log(self, level, message):
        # This is non-blocking since QueueHandler.emit just puts
        # the record in the queue and returns immediately
        self.queue_logger.log(level, message)
        # logger.log(level, message)

    async def info(self, message):
        await self.log(logging.INFO, message)

    async def error(self, message):
        await self.log(logging.ERROR, message)

    async def debug(self, message):
        await self.log(logging.DEBUG, message)

    async def exception(self, ex):
        await self.log(logging.ERROR, ex)

    def close(self):
        # Stop the queue listener thread
        self.queue_listener.stop()


# Create an async logger instance
async_logger = AsyncLogger()
