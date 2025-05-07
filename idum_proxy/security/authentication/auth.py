from typing import Protocol


class Auth(Protocol):
    def get_headers(self) -> dict[str, str]: ...
