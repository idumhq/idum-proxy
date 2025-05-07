from typing import Dict, Optional
from datetime import datetime, timedelta
from jose import jwt
from pydantic import SecretStr
from idum_proxy.security.authentication.auth import Auth


class JWTAuth(Auth):
    """Authentication handler for JWT (JSON Web Token) Authentication.

    Implements JWT authentication for API requests by generating and
    including a signed token in the Authorization header.

    Attributes:
        secret_key: The secret key used to sign the JWT
        algorithm: The algorithm used for JWT signing (default: HS256)
        token_expire_minutes: Token expiration time in minutes (default: 30)
        additional_claims: Optional additional claims to include in the token
    """

    def __init__(
        self,
        secret_key: SecretStr,
        algorithm: str = "HS256",
        token_expire_minutes: int = 30,
        additional_claims: Optional[Dict] = None,
    ):
        super().__init__()
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_minutes = token_expire_minutes
        self.additional_claims = additional_claims or {}
        self._cached_token = None
        self._token_expiry = None

    def _generate_token(self) -> str:
        """Generate a new JWT token.

        Creates a new JWT with expiration time and any additional claims.

        Returns:
            A signed JWT string
        """
        expiry = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        self._token_expiry = expiry

        payload = {"exp": expiry, "iat": datetime.utcnow(), **self.additional_claims}

        return jwt.encode(
            payload, self.secret_key.get_secret_value(), algorithm=self.algorithm
        )

    def _is_token_valid(self) -> bool:
        """Check if the cached token is still valid.

        Returns:
            Boolean indicating if token is still valid
        """
        if not self._cached_token or not self._token_expiry:
            return False

        # Add buffer time to ensure token doesn't expire during request
        buffer_time = timedelta(seconds=30)
        return datetime.utcnow() < (self._token_expiry - buffer_time)

    def get_headers(self) -> dict[str, str]:
        """Generate HTTP headers with JWT Authentication.

        Generates or reuses a valid JWT token and returns it in the
        Authorization header with the Bearer scheme.

        Returns:
            A dictionary containing the Authorization header with
            the JWT token in the format: Bearer <token>
        """
        if not self._is_token_valid():
            self._cached_token = self._generate_token()

        return {"Authorization": f"Bearer {self._cached_token}"}
