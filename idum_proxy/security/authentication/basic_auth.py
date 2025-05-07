from base64 import b64encode
from idum_proxy.security.authentication.auth import Auth
from pydantic import SecretStr


class BasicAuth(Auth):
    """Authentication handler for HTTP Basic Authentication.

    Implements the HTTP Basic Authentication scheme as defined in RFC 7617.

    Attributes:
        username: The username for authentication
        password: The password stored as a secure SecretStr
    """

    def __init__(self, username: str, password: SecretStr):
        super().__init__()
        self.username = username
        self.password = password

    def get_headers(self) -> dict[str, str]:
        """Generate HTTP headers with Basic Authentication.

        Returns:
            A dictionary containing the Authorization header with properly
            encoded credentials in the format: Basic <base64-encoded-credentials>
        """
        # Properly encode credentials as per RFC 7617
        credentials = f"{self.username}:{self.password.get_secret_value()}"
        encoded_credentials = b64encode(credentials.encode("utf-8")).decode("utf-8")

        return {"Authorization": f"Basic {encoded_credentials}"}
