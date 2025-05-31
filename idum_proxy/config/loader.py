import json
import logging

from threading import Lock

from idum_proxy.config.models import Config

config_lock = Lock()


def get_file_config(filepath: str) -> Config | None:
    with config_lock:
        try:
            with open(filepath) as f:
                json_loaded = json.load(f)
                config = Config(**json_loaded)
                config.endpoints.sort(key=lambda e: e.weight, reverse=True)
                logging.info(f"Nb endpoints: {len(config.endpoints)}")
                return config
        except FileNotFoundError:
            logging.error(f"File {filepath} not found")
            return None
