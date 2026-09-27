"""JWT auth tests. Bad tokens and the issuer switch."""

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from core.auth.authentication import JWTAuthentication, TokenPrincipal
from core.auth.testing import mint_test_token
from core.auth.verifier import (
    LocalTokenVerifier,
    TokenValidationError,
    get_token_verifier,
)
from django.conf import settings
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()
auth_backend = JWTAuthentication()


@pytest.fixture
def verifier() -> LocalTokenVerifier:
    return LocalTokenVerifier()


def _craft_alg_none_token(payload: dict[str, object]) -> str:
    """Build a JWT with alg=none - must be rejected."""

    def b64_obj(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    header: dict[str, object] = {"alg": "none", "typ": "JWT"}
    return f"{b64_obj(header)}.{b64_obj(payload)}."


def test_valid_token_accepted(verifier: LocalTokenVerifier) -> None:
    """Happy path: verified claims include sub and role for downstream use."""
    token = mint_test_token(sub="user-123", role="admin")
    claims = verifier.verify(token)
    assert claims["sub"] == "user-123"
    assert claims["role"] == "admin"


def test_token_alg_none_rejected(verifier: LocalTokenVerifier) -> None:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": "user-123",
        "role": "colleague",
        "iss": settings.AUTH_LOCAL_ISSUER,
        "aud": settings.AUTH_LOCAL_AUDIENCE,
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    token = _craft_alg_none_token(payload)
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_token_bad_signature_rejected(verifier: LocalTokenVerifier) -> None:
    token = mint_test_token(signing_key="wrong-key-not-the-local-signing-key")
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_token_expired_rejected(verifier: LocalTokenVerifier) -> None:
    expired = datetime.now(tz=UTC) - timedelta(minutes=5)
    token = mint_test_token(exp=expired)
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_token_wrong_aud_rejected(verifier: LocalTokenVerifier) -> None:
    token = mint_test_token(aud="wrong-audience")
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_token_wrong_iss_rejected(verifier: LocalTokenVerifier) -> None:
    token = mint_test_token(iss="https://evil.test/issuer")
    with pytest.raises(TokenValidationError):
        verifier.verify(token)


def test_token_missing_required_claim_rejected(verifier: LocalTokenVerifier) -> None:
    token = mint_test_token(omit_claims=frozenset({"role"}))
    with pytest.raises(TokenValidationError, match="role"):
        verifier.verify(token)


def test_get_token_verifier_resolves_local() -> None:
    """Settings switch returns LocalTokenVerifier - Cognito drops in."""
    with override_settings(AUTH_ISSUER="local"):
        assert isinstance(get_token_verifier(), LocalTokenVerifier)


def test_get_token_verifier_resolves_cognito() -> None:
    """Settings switch returns CognitoTokenVerifier - same switch as local."""
    from core.auth.cognito import CognitoTokenVerifier

    with override_settings(
        AUTH_ISSUER="cognito",
        COGNITO_ISSUER="https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_TEST",
        COGNITO_JWKS_URL=(
            "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_TEST/.well-known/jwks.json"
        ),
        COGNITO_APP_CLIENT_ID="test-cognito-client-id",
    ):
        assert isinstance(get_token_verifier(), CognitoTokenVerifier)


def test_get_token_verifier_unknown_issuer_raises() -> None:
    with override_settings(AUTH_ISSUER="unknown-issuer"):
        with pytest.raises(Exception, match="Unsupported AUTH_ISSUER"):
            get_token_verifier()


def test_jwt_authentication_valid_token_exposes_sub_and_role() -> None:
    """Happy path through DRF: verified sub/role on request.user for downstream code."""
    token = mint_test_token(sub="user-456", role="colleague")
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    result = auth_backend.authenticate(request)
    assert result is not None
    user, auth = result
    assert isinstance(user, TokenPrincipal)
    assert user.sub == "user-456"
    assert user.role == "colleague"
    assert user.is_authenticated is True
    assert auth is None


def test_jwt_authentication_missing_header_returns_none() -> None:
    request = factory.get("/")
    assert auth_backend.authenticate(request) is None


def test_jwt_authentication_invalid_token_rejected() -> None:
    request = factory.get("/", HTTP_AUTHORIZATION="Bearer not-a-valid-jwt")
    with pytest.raises(AuthenticationFailed, match="Invalid or expired token"):
        auth_backend.authenticate(request)


def test_jwt_authentication_uses_verifier_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap verifier via hook - JWTAuthentication unchanged."""

    class StubVerifier:
        def verify(self, token: str) -> dict[str, Any]:
            return {"sub": "stub-subject", "role": "admin"}

    monkeypatch.setattr(
        "core.auth.authentication.get_token_verifier",
        lambda: StubVerifier(),
    )
    request = factory.get("/", HTTP_AUTHORIZATION="Bearer any-token")
    result = auth_backend.authenticate(request)
    assert result is not None
    user, _ = result
    assert isinstance(user, TokenPrincipal)
    assert user.sub == "stub-subject"
    assert user.role == "admin"
