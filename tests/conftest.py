import pytest
import logging


class RetryException(Exception): ...


# config
MAX_ATTEMPTS = 5
MIN_TIME = 0.1  # in seconds
MAX_TIME = 0.2  # in seconds

SHOW_EXCEPTIONS = True

pytest_plugins = ["pytester"]

# For console output
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)


@pytest.fixture
def disable_logging_exception(mocker):
    if not SHOW_EXCEPTIONS:
        mocker.patch("logging.exception", lambda *args, **kwargs: None)
