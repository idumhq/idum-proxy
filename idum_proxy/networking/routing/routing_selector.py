from antpathmatcher import AntPathMatcher

from idum_proxy.config.models import (
    Config,
    Endpoint,
)


class RoutingSelector:
    def __init__(self, config: Config):
        self.ant_matcher = AntPathMatcher()
        self.config = config

    def find_endpoint(self, request_url_path: str) -> Endpoint:
        """find the upstream"""

        if not request_url_path.endswith("/"):
            request_url_path = request_url_path + "/"

        def match(e):
            is_match = self.ant_matcher.match(
                e.match if e.match else e.endpoint, request_url_path
            )
            return is_match

        # for each routes, find the route that match the input path
        endpoint = next((e for e in self.config.endpoints if match(e)), None)
        if not endpoint:
            raise Exception(f"no endpoint found for {request_url_path}")
            # return Response(content="Endpoint not found", status_code=HTTPStatus.NOT_FOUND)

        """
        # extract the variables of the path
        variables = self.ant_matcher.extract_uri_template_variables(
            route.endpoint, request_url_path
        )

        
        result = (
            route.backend.url_pattern
            if route.backend.url_pattern
            else f"{request_url_path.replace(route.prefix, '').strip('/')}"
        )
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", value)
        """

        return endpoint
