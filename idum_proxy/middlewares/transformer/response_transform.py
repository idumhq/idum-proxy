from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from antpathmatcher import AntPathMatcher

from idum_proxy.async_logger import async_logger
from starlette.types import Message

from idum_proxy.networking.routing.routing_selector import RoutingSelector


class ResponseTransformerMiddleware:
    def __init__(self, app: ASGIApp, routing_selector: RoutingSelector) -> None:
        self.app = app
        self.antpathmatcher = AntPathMatcher()
        self.routing_selector = routing_selector

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await async_logger.info("Call ResponseTransformerMiddleware")

        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        async def send_with_transformation(message: Message) -> None:
            message_type = message["type"]

            if message_type == "http.response.start":
                await send(message)
            elif message_type == "http.response.body":
                body = message.get("body", b"")

                try:
                    text_content = body.decode()
                except UnicodeDecodeError:
                    await send(message)
                    return

                request = Request(scope)
                path = request.url.path

                endpoint = self.routing_selector.find_endpoint(request_url_path=path)

                if (
                    hasattr(endpoint, "transformers")
                    and hasattr(endpoint.transformers, "response")
                    and hasattr(endpoint.transformers.response, "textReplacements")
                    and endpoint.transformers.response.textReplacements
                    and endpoint.transformers.response.enabled
                ):
                    to_replace = endpoint.transformers.response.textReplacements
                    for textReplacement in to_replace:
                        new_value = textReplacement.newvalue.replace("${path}", path)
                        message["body"] = text_content.replace(
                            textReplacement.oldvalue, new_value
                        ).encode()

                await send(message)
            elif message_type == "http.response.end":
                await send(message)

        # config = self.idum_proxy.config
        await self.app(scope, receive, send_with_transformation)
