"""Cognito TokenVerifier tests - mocked JWKS only, no network."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from core.auth.cognito import (
    CognitoTokenVerifier,
    JwksCache,
    map_cognito_groups_to_role,
)
from core.auth.verifier import TokenValidationError
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings
from jwt.algorithms import RSAAlgorithm

TEST_ISSUER = "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_TEST"
TEST_CLIENT_ID = "test-cognito-client-id"
TEST_JWKS_URL = f"{TEST_ISSUER}/.well-known/jwks.json"
TEST_KID = "test-rsa-key-1"

COGNITO_SETTINGS = {
    "AUTH_ISSUER": "cognito",
    "COGNITO_ISSUER": TEST_ISSUER,
    "COGNITO_JWKS_URL": TEST_JWKS_URL,
    "COGNITO_APP_CLIENT_ID": TEST_CLIENT_ID,
}


@pytest.fixture(scope="module")
def rsa_private_key() -> Any:
    """Module-scoped RSA key - deterministic enough for mocked JWKS (no network)."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def jwks_payload(rsa_private_key: Any) -> dict[str, Any]:
    public_key = rsa_private_key.public_key()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": TEST_KID, "use": "sig", "alg": "RS256"})
    return {"keys": [jwk]}


def _mint_cognito_token(
    rsa_private_key: Any,
    *,
    kid: str = TEST_KID,
    sub: str = "cognito-user-123",
    groups: list[str] | None = None,
    iss: str = TEST_ISSUER,
    client_id: str = TEST_CLIENT_ID,
    exp: datetime | None = None,
    extra_claims: dict[str, Any] | None = None,
    signing_key: Any | None = None,
) -> str:
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": iss,
        "client_id": client_id,
        "token_use": "access",
        "cognito:groups": groups if groups is not None else ["colleague"],
        "exp": exp if exp is not None else now + timedelta(hours=1),
        "iat": now,
    }
    if extra_claims:
        payload.update(extra_claims)
    headers = {"kid": kid, "alg": "RS256"}
    key = signing_key if signing_key is not None else rsa_private_key
    return jwt.encode(payload, key, algorithm="RS256", headers=headers)


def _craft_alg_none_token(payload: dict[str, object]) -> str:
    def b64_obj(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    header: dict[str, object] = {"alg": "none", "typ": "JWT", "kid": TEST_KID}
    return f"{b64_obj(header)}.{b64_obj(payload)}."


def _verifier_with_jwks(
    jwks_payload: dict[str, Any],
    *,
    fetch_calls: list[int] | None = None,
) -> CognitoTokenVerifier:
    """Build verifier with injectable JWKS - never hits the network."""

    def fetch_jwks(_url: str) -> dict[str, Any]:
        if fetch_calls is not None:
            fetch_calls.append(1)
        return jwks_payload

    cache = JwksCache(TEST_JWKS_URL, fetch_jwks=fetch_jwks)
    return CognitoTokenVerifier(jwks_cache=cache)


@pytest.mark.parametrize(
    ("groups", "expected_role"),
    [
        (["admin"], "admin"),
        (["colleague"], "colleague"),
        (["subject"], "subject"),
        (["public_caller"], "public_caller"),
        (["colleague", "admin"], "admin"),
    ],
)
def test_valid_cognito_token_groups_mapped_to_role(
    rsa_private_key: Any,
    jwks_payload: dict[str, Any],
    groups: list[str],
    expected_role: str,
) -> None:
    token = _mint_cognito_token(rsa_private_key, groups=groups)
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        claims = verifier.verify(token)
    assert claims["sub"] == "cognito-user-123"
    assert claims["role"] == expected_role


def test_token_iat_slightly_in_future_accepted(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    """Clock skew: host a few dozen seconds behind Cognito must not 401 fresh tokens."""
    now = datetime.now(tz=UTC)
    token = _mint_cognito_token(
        rsa_private_key,
        groups=["admin"],
        extra_claims={"iat": now + timedelta(seconds=30)},
    )
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        claims = verifier.verify(token)
    assert claims["role"] == "admin"


def test_token_alg_none_rejected(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": "cognito-user-123",
        "iss": TEST_ISSUER,
        "client_id": TEST_CLIENT_ID,
        "cognito:groups": ["colleague"],
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = _craft_alg_none_token(payload)
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        with pytest.raises(TokenValidationError, match="Algorithm not allowed"):
            verifier.verify(token)


def test_token_bad_signature_rejected(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _mint_cognito_token(rsa_private_key, signing_key=other_key)
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        with pytest.raises(TokenValidationError):
            verifier.verify(token)


def test_token_expired_rejected(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    expired = datetime.now(tz=UTC) - timedelta(minutes=5)
    token = _mint_cognito_token(rsa_private_key, exp=expired)
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        with pytest.raises(TokenValidationError):
            verifier.verify(token)


def test_token_wrong_aud_rejected(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    token = _mint_cognito_token(rsa_private_key, client_id="wrong-client-id")
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        with pytest.raises(TokenValidationError, match="Invalid audience"):
            verifier.verify(token)


def test_token_wrong_iss_rejected(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    token = _mint_cognito_token(rsa_private_key, iss="https://evil.test/issuer")
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload)
        with pytest.raises(TokenValidationError):
            verifier.verify(token)


def test_unknown_kid_triggers_single_jwks_refresh_then_rejects(
    rsa_private_key: Any, jwks_payload: dict[str, Any]
) -> None:
    """Unknown kid must refresh JWKS once - not per retry - then fail closed."""
    fetch_calls: list[int] = []
    token = _mint_cognito_token(rsa_private_key, kid="missing-kid-not-in-jwks")
    with override_settings(**COGNITO_SETTINGS):
        verifier = _verifier_with_jwks(jwks_payload, fetch_calls=fetch_calls)
        with pytest.raises(TokenValidationError, match="Unknown signing key"):
            verifier.verify(token)
    assert len(fetch_calls) == 1


def test_map_cognito_groups_empty_rejected() -> None:
    with pytest.raises(TokenValidationError, match="missing Cognito groups"):
        map_cognito_groups_to_role([])


def test_map_cognito_groups_unmapped_rejected() -> None:
    with pytest.raises(TokenValidationError, match="No Cognito group maps"):
        map_cognito_groups_to_role(["unrecognised-group"])


def test_jwt_authentication_byte_unchanged_by_cognito_phase() -> None:
    """JWTAuthentication should not mention Cognito. The switch lives in settings."""
    auth_path = Path("core/auth/authentication.py")
    source = auth_path.read_text(encoding="utf-8")
    assert "cognito" not in source.lower()
    assert "AUTH_ISSUER" not in source
    assert "COGNITO" not in source
