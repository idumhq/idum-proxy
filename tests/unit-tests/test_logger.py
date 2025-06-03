import pytest

from idum_proxy.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.asyncio
async def test_logger():
    logger.debug("debug message")
    logger.info("info message")
    logger.error("error message")
    logger.exception(Exception("exception message"))
