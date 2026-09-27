"""Payment provider port - Stripe specifics stay in adapters."""

from typing import Any, Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class PaymentError(Exception):
    """Payment operation failed. Messages must never include secrets or card data."""


class PaymentDisabledError(PaymentError):
    """Payments are not configured - checkout is unavailable."""


class PaymentWebhookError(PaymentError):
    """Webhook payload failed verification - deny by default."""


@runtime_checkable
class PaymentProvider(Protocol):
    """Create checkout sessions and verify signed webhook payloads."""

    def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Return a provider-neutral checkout session (must include url)."""
        ...

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        """Verify signature and return the parsed event dict."""
        ...


class DisabledPaymentProvider:
    """No-op default - dev/tests/CI need no payment account."""

    def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        raise PaymentDisabledError("Payments are disabled (PAYMENT_PROVIDER=disabled)")

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        # Deny by default - same posture as a bad signature on a live provider.
        raise PaymentWebhookError("Webhook verification rejected: payments disabled")


def get_payment_provider() -> PaymentProvider:
    """Resolve the active provider from PAYMENT_PROVIDER (single switch point)."""
    name = settings.PAYMENT_PROVIDER
    if name == "disabled":
        return DisabledPaymentProvider()
    if name == "stripe":
        # Lazy import - default disabled avoids loading Stripe unless selected.
        from core.payments.stripe import StripePaymentProvider

        return StripePaymentProvider()
    raise ImproperlyConfigured(f"Unsupported PAYMENT_PROVIDER: {name!r}")
