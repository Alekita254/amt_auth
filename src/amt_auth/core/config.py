from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from amt_auth.exceptions import ConfigError

_REQUIRED = ("AMT_KEYCLOAK_URL", "AMT_REALM", "AMT_CLIENT_ID", "AMT_CLIENT_SECRET")
_config_cache: AMTConfig | None = None


@dataclass(frozen=True)
class AMTConfig:
    keycloak_url: str   # e.g. "http://localhost:8080"
    realm: str          # e.g. "amilliontechies"
    client_id: str
    client_secret: str


def load_config(env: dict[str, str] | None = None) -> AMTConfig:
    """Read and validate config from environment variables.

    Raises ConfigError immediately on any missing or malformed value.
    """
    if env is None:
        env = dict(os.environ)

    missing = [k for k in _REQUIRED if not env.get(k)]
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    keycloak_url = env["AMT_KEYCLOAK_URL"].rstrip("/")
    parsed = urlparse(keycloak_url)
    if not parsed.scheme or not parsed.netloc:
        raise ConfigError(
            f"AMT_KEYCLOAK_URL must be a full URL with scheme (got {keycloak_url!r})"
        )

    return AMTConfig(
        keycloak_url=keycloak_url,
        realm=env["AMT_REALM"],
        client_id=env["AMT_CLIENT_ID"],
        client_secret=env["AMT_CLIENT_SECRET"],
    )


def get_config() -> AMTConfig:
    """Return cached config singleton. Calls load_config() on first access."""
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache
