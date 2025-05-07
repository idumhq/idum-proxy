import pytest

from idum_proxy.async_logger import AsyncLogger


@pytest.mark.asyncio
async def test_async_logger():
    async_logger = AsyncLogger()

    await async_logger.debug("debug message")
    await async_logger.info("info message")
    await async_logger.error("error message")
    await async_logger.exception(Exception("exception message"))
