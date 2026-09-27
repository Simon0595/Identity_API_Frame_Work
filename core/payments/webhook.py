"""Payment webhook handling - verify via port, idempotent on event id."""

from typing import Any

from django.core.cache import cache

from core.payments.provider import PaymentWebhookError, get_payment_provider

_EVENT_CACHE_PREFIX = "payment_webhook:"
# Stripe retries for up to 3 days; retain ids a bit longer for safety.
_EVENT_CACHE_TTL_SECONDS = 4 * 24 * 60 * 60


def process_payment_webhook(payload: bytes, signature: str | None) -> dict[str, Any]:
    """Verify signature via the active provider; process each event id at most once."""
    provider = get_payment_provider()
    event = provider.verify_webhook(payload, signature)

    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise PaymentWebhookError("Webhook verification rejected: missing event id")

    cache_key = f"{_EVENT_CACHE_PREFIX}{event_id}"
    if cache.add(cache_key, True, _EVENT_CACHE_TTL_SECONDS):
        return {"status": "processed", "event_id": event_id}
    return {"status": "already_processed", "event_id": event_id}
