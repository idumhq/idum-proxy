import json
import logging
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from unittest.mock import patch, MagicMock

from idum_proxy.config.models import Config
from idum_proxy.config.loader import get_file_config  # Adjust import path as needed

