"""Pull the bearer token off the request and turn it into sub + role."""

from dataclasses import dataclass

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from core.auth.verifier import TokenValidationError, get_token_verifier


@dataclass(frozen=True, slots=True)
class TokenPrincipal:
    """Who called: sub and role from the token."""

    sub: str
    role: str

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class JWTAuthentication(BaseAuthentication):
    """Authenticate requests via Authorization: Bearer <jwt>."""

    keyword = b"bearer"

    def authenticate_header(self, request: Request) -> str:
        """WWW-Authenticate value - required so DRF returns 401, not coerced 403."""
        return 'Bearer realm="api"'

    def authenticate(self, request: Request) -> tuple[TokenPrincipal, None] | None:
        token = self._extract_bearer_token(request)
        if token is None:
            return None

        try:
            claims = get_token_verifier().verify(token)
        except TokenValidationError:
            # Generic message - never include the raw token.
            raise AuthenticationFailed("Invalid or expired token.") from None

        return TokenPrincipal(sub=claims["sub"], role=claims["role"]), None

    def _extract_bearer_token(self, request: Request) -> str | None:
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if parts[0].lower() != self.keyword:
            return None
        if len(parts) == 1:
            raise AuthenticationFailed(
                "Invalid token header. No credentials provided."
            )
        if len(parts) > 2:
            raise AuthenticationFailed(
                "Invalid token header. Token string should not contain spaces."
            )
        try:
            return parts[1].decode()
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Invalid token header.") from exc
