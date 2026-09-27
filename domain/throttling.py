"""Rate limits keyed on caller sub or client IP.

TokenPrincipal has no Django User.pk, so we key authenticated limits on sub.
Anon traffic is keyed on IP.
"""

from core.auth.authentication import TokenPrincipal
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class GlobalAnonRateThrottle(AnonRateThrottle):
    """IP-keyed limit for unauthenticated traffic - health, webhooks, auth misses."""

    scope = "anon"


class IdentityReadThrottle(SimpleRateThrottle):
    """Per-caller throttle for authenticated reads - limits scraping, not writes."""

    scope = "identity_read"

    def get_cache_key(self, request: object, view: object) -> str | None:
        principal = getattr(request, "user", None)
        if not isinstance(principal, TokenPrincipal):
            return None
        return self.cache_format % {"scope": self.scope, "ident": principal.sub}


class IdentityWriteThrottle(SimpleRateThrottle):
    """Per-caller throttle for identity PUT - limits write abuse, not reads."""

    scope = "identity_write"

    def get_cache_key(self, request: object, view: object) -> str | None:
        principal = getattr(request, "user", None)
        if not isinstance(principal, TokenPrincipal):
            return None
        return self.cache_format % {"scope": self.scope, "ident": principal.sub}
