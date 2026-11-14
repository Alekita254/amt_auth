from __future__ import annotations

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from amt_auth.core.claims import TokenClaims
from amt_auth.core.config import AMTConfig
from amt_auth.exceptions import InvalidTokenError, TokenExpiredError

_ALLOWED_ALGORITHMS = {"RS256"}


class TokenValidator:
    """Validates a raw JWT string against the Keycloak realm's JWKS.

    Uses PyJWT's PyJWKClient for key fetching and caching — no custom
    caching logic. Rejects any algorithm other than RS256 before making
    any network call.
    """

    def __init__(
        self,
        config: AMTConfig,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self._config = config
        jwks_uri = (
            f"{config.keycloak_url}/realms/{config.realm}"
            "/protocol/openid-connect/certs"
        )
        self._jwks = jwks_client or PyJWKClient(jwks_uri)

    def validate(self, raw_jwt: str) -> TokenClaims:
        try:
            header = jwt.get_unverified_header(raw_jwt)
        except jwt.exceptions.DecodeError as exc:
            raise InvalidTokenError(f"Cannot decode token header: {exc}") from exc

        alg = header.get("alg", "")
        if alg not in _ALLOWED_ALGORITHMS:
            raise InvalidTokenError(
                f"Unsupported algorithm {alg!r}. Only RS256 is accepted."
            )

        try:
            signing_key = self._jwks.get_signing_key_from_jwt(raw_jwt)
        except PyJWKClientError as exc:
            raise InvalidTokenError(f"Could not resolve signing key: {exc}") from exc

        issuer = f"{self._config.keycloak_url}/realms/{self._config.realm}"

        try:
            payload = jwt.decode(
                raw_jwt,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._config.client_id,
                issuer=issuer,
            )
        except jwt.exceptions.ExpiredSignatureError as exc:
            raise TokenExpiredError("Token has expired") from exc
        except jwt.exceptions.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        return TokenClaims.from_decoded(payload, self._config.client_id)
