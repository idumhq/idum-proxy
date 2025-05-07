from pathlib import Path


from idum_proxy.config.models import Backends, Endpoint
from starlette.requests import Request

from idum_proxy.files.reader.io_async_reader import download_text_file


class File:
    def __init__(self, endpoint: Endpoint, backend: Backends):
        self.endpoint = endpoint
        self.backend = backend

    async def handle_request(self, request: Request, headers: dict):
        path = request.url.path.removeprefix(self.endpoint.prefix)

        file_path = self.backend.file.path + path
        return await download_text_file(Path(file_path))
