from starlette.types import ASGIApp


class ContentLengthMiddleware:
    """
    Middleware that sets the Content-Length header for responses.

    This middleware intercepts responses and calculates their content length,
    then adds the appropriate Content-Length header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Collect response data
        response_data = []
        response_headers = []
        response_status = None

        async def send_wrapper(message: dict) -> None:
            nonlocal response_status, response_headers, response_data

            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = list(message.get("headers", []))

                # Remove any existing Content-Length header to replace it
                response_headers = [
                    header
                    for header in response_headers
                    if header[0].lower() != b"content-length"
                ]

                # Always wait for body to calculate correct Content-Length

            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_data.append(body)

                # If this is the last chunk (more_body is False or not present)
                if not message.get("more_body", False):
                    # Calculate total content length
                    total_body = b"".join(response_data)
                    content_length = len(total_body)

                    # Add the correct Content-Length header
                    response_headers.append(
                        (b"content-length", str(content_length).encode())
                    )

                    # Send the start message with corrected headers
                    await send(
                        {
                            "type": "http.response.start",
                            "status": response_status,
                            "headers": response_headers,
                        }
                    )

                    # Send the complete body
                    await send(
                        {
                            "type": "http.response.body",
                            "body": total_body,
                            "more_body": False,
                        }
                    )
                # If more_body=True, continue collecting chunks

            else:
                await send(message)

        await self.app(scope, receive, send_wrapper)
