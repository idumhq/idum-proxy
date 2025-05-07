from http import HTTPStatus

from starlette.responses import RedirectResponse

from idum_proxy.config.models import Backends, Endpoint
from starlette.requests import Request


class Redirect:
    def __init__(self, connection_pooling, endpoint: Endpoint, backend: Backends):
        self.connection_pooling = connection_pooling
        self.endpoint = endpoint
        self.backend = backend

    async def handle_request(self, request: Request, headers: dict):
        redirect_url = self.backend.redirect.location

        if self.backend.redirect.preserve_path:
            path = request.url.path.removeprefix(self.endpoint.prefix)

            if request.url.query:
                path = f"{path}?{request.url.query}"

            redirect_url = f"{redirect_url}{path}"
        return RedirectResponse(
            url=redirect_url, status_code=HTTPStatus.FOUND, headers=headers
        )
