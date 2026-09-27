"""JWT verification port - issuer-specific signing behind one method."""

from typing import Any, Protocol, runtime_checkable

import jwt
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class TokenValidationError(Exception):
    """Token failed verification. Messages must never include the raw token."""


@runtime_checkable
class TokenVerifier(Protocol):
    """Verify a bearer JWT and return claims, or raise TokenValidationError."""

    def verify(self, token: str) -> dict[str, Any]:
        """Return verified JWT claims."""
        ...


class LocalTokenVerifier:
    """Prototype mock issuer: HS256 tokens signed with AUTH_LOCAL_SIGNING_KEY."""

    # Explicit allow-list - rejects alg=none and algorithm confusion.
    ALLOWED_ALGORITHMS: tuple[str, ...] = ("HS256",)
    REQUIRED_CLAIMS: tuple[str, ...] = ("sub", "role", "iss", "aud", "exp")

    def verify(self, token: str) -> dict[str, Any]:
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                settings.AUTH_LOCAL_SIGNING_KEY,
                algorithms=list(self.ALLOWED_ALGORITHMS),
                issuer=settings.AUTH_LOCAL_ISSUER,
                audience=settings.AUTH_LOCAL_AUDIENCE,
                options={
                    "require": ["exp", "iss", "aud", "sub"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                },
            )
        except jwt.InvalidTokenError as exc:
            raise TokenValidationError(str(exc)) from exc

        if "role" not in claims:
            raise TokenValidationError("Token missing required claim: role")

        return claims


def get_token_verifier() -> TokenVerifier:
    """Resolve the active verifier from AUTH_ISSUER (single switch point)."""
    issuer = settings.AUTH_ISSUER
    if issuer == "local":
        return LocalTokenVerifier()
    if issuer == "cognito":
        # Lazy import - local dev/tests default to HS256 and need not load JWKS code.
        from core.auth.cognito import CognitoTokenVerifier

        return CognitoTokenVerifier()
    raise ImproperlyConfigured(f"Unsupported AUTH_ISSUER: {issuer!r}")
