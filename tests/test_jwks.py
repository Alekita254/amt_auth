"""Tests for the JWKS integration point inside TokenValidator.

We do NOT test PyJWT's PyJWKClient internals (caching, rotation, HTTP fetching).
We test:
  1. That TokenValidator constructs the correct Keycloak JWKS URI.
  2. That PyJWKClientError from the client is wrapped into InvalidTokenError.
"""
from unittest.mock import MagicMock

import pytest
from jwt.exceptions import PyJWKClientError

from amt_auth.core.config import load_config
from amt_auth.core.validator import TokenValidator
from amt_auth.exceptions import InvalidTokenError


def test_jwks_uri_points_to_correct_keycloak_endpoint(amt_env):
    cfg = load_config(amt_env)
    validator = TokenValidator(cfg)
    expected = (
        "http://localhost:8080/realms/amilliontechies"
        "/protocol/openid-connect/certs"
    )
    assert validator._jwks.uri == expected


def test_jwks_client_error_becomes_invalid_token_error(amt_env, make_jwt):
    cfg = load_config(amt_env)
    broken_client = MagicMock()
    broken_client.get_signing_key_from_jwt.side_effect = PyJWKClientError("unreachable")
    validator = TokenValidator(cfg, jwks_client=broken_client)
    with pytest.raises(InvalidTokenError, match="Could not resolve signing key"):
        validator.validate(make_jwt())
