class AMTAuthError(Exception):
    """Base for all amt-auth errors."""


class ConfigError(AMTAuthError):
    """Missing or malformed configuration."""


class TokenExpiredError(AMTAuthError):
    """JWT has expired."""


class InvalidTokenError(AMTAuthError):
    """JWT is invalid (bad signature, wrong iss/aud, bad alg, missing sub, etc.)."""


class AdminAPIError(AMTAuthError):
    """Non-2xx response from the Keycloak Admin API."""

    def __init__(self, status_code: int, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Admin API error {status_code}: {body}")


class SyncError(AMTAuthError):
    """Malformed event payload received by the sync consumer."""
