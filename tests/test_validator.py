from __future__ import annotations

import base64
import json
import time
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from amt_auth.core.config import load_config
from amt_auth.core.validator import TokenValidator
from amt_auth.exceptions import InvalidTokenError, TokenExpiredError
from tests.constants import AUDIENCE, ISSUER, KID


def _make_validator(amt_env: dict, fake_jwks_client) -> TokenValidator:
    cfg = load_config(amt_env)
    return TokenValidator(cfg, jwks_client=fake_jwks_client)


def test_valid_jwt(amt_env, make_jwt, fake_jwks_client):
    validator = _make_validator(amt_env, fake_jwks_client)
    claims = validator.validate(make_jwt())
    assert claims.sub == "user-sub-123"
    assert claims.email == "alice@gmail.com"


def test_expired_jwt(amt_env, make_jwt, fake_jwks_client):
    validator = _make_validator(amt_env, fake_jwks_client)
    token = make_jwt({"exp": int(time.time()) - 3600})
    with pytest.raises(TokenExpiredError):
        validator.validate(token)


def test_wrong_issuer(amt_env, make_jwt, fake_jwks_client):
    validator = _make_validator(amt_env, fake_jwks_client)
    token = make_jwt({"iss": "http://evil.example/realms/fake"})
    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_wrong_audience(amt_env, make_jwt, fake_jwks_client):
    validator = _make_validator(amt_env, fake_jwks_client)
    token = make_jwt({"aud": "wrong-client"})
    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_wrong_signing_key(amt_env, fake_jwks_client):
    """Token signed with a different private key; JWKS client returns our public key."""
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    token = pyjwt.encode(
        {
            "sub": "x",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": int(time.time()) + 3600,
        },
        other_pem,
        algorithm="RS256",
        headers={"kid": KID},
    )
    validator = _make_validator(amt_env, fake_jwks_client)
    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_alg_none_rejected(amt_env):
    """alg:none must be rejected before PyJWKClient is ever called."""
    cfg = load_config(amt_env)
    never_called = MagicMock()

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"sub": "x"}).encode())
    token = f"{header}.{payload}."

    validator = TokenValidator(cfg, jwks_client=never_called)
    with pytest.raises(InvalidTokenError, match="Unsupported algorithm"):
        validator.validate(token)
    never_called.get_signing_key_from_jwt.assert_not_called()


def test_hs256_rejected(amt_env):
    """HS256 tokens must be rejected before PyJWKClient is ever called."""
    cfg = load_config(amt_env)
    never_called = MagicMock()

    token = pyjwt.encode(
        {"sub": "x", "iss": ISSUER, "aud": AUDIENCE, "exp": int(time.time()) + 3600},
        "secret",
        algorithm="HS256",
    )
    validator = TokenValidator(cfg, jwks_client=never_called)
    with pytest.raises(InvalidTokenError, match="Unsupported algorithm"):
        validator.validate(token)
    never_called.get_signing_key_from_jwt.assert_not_called()


def test_missing_sub_raises(amt_env, make_jwt, fake_jwks_client):
    validator = _make_validator(amt_env, fake_jwks_client)
    token = make_jwt({"sub": ""})
    with pytest.raises(InvalidTokenError):
        validator.validate(token)
