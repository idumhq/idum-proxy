__version__ = "1.0.0"
__all__ = (
    "__version__",
    "IdumProxy",
)

import logging

from idum_proxy.idum_proxy import IdumProxy

logger = logging.getLogger("idum-proxy")
logger.addHandler(logging.NullHandler())
