from antpathmatcher import AntPathMatcher
from starlette.responses import JSONResponse, Response

from idum_proxy.config.models import Backends, Endpoint, MockResponseTemplate
from starlette.requests import Request


class Mock:
    def __init__(self, connection_pooling, endpoint: Endpoint, backend: Backends):
        self.connection_pooling = connection_pooling
        self.endpoint = endpoint
        self.backend = backend
        self.ant_matcher = AntPathMatcher()

    def _find_mock_response_template(
        self, request_url_path: str
    ) -> MockResponseTemplate:
        if not request_url_path.startswith("/"):
            request_url_path = "/" + request_url_path

        def match(path: str):
            is_match = self.ant_matcher.match(path, request_url_path)
            return is_match

        mock_path = next(
            (e for e in self.backend.mock.path_templates if match(e)), None
        )
        if not mock_path:
            return self.backend.mock.default_response

        return self.backend.mock.path_templates[mock_path]

    async def handle_request(self, request: Request, headers: dict):
        mock_response_template: MockResponseTemplate = (
            self._find_mock_response_template(
                request_url_path=request.url.path.removeprefix(self.endpoint.prefix),
            )
        )

        headers = (
            mock_response_template.headers.copy()
            if mock_response_template.headers
            else {}
        )

        if "application/json" in mock_response_template.content_type:
            return JSONResponse(
                content=mock_response_template.body,
                status_code=mock_response_template.status_code,
                media_type=mock_response_template.content_type,
                headers=headers,
            )

        return Response(
            content=mock_response_template.body,
            status_code=mock_response_template.status_code,
            media_type=mock_response_template.content_type,
            headers=headers,
        )
