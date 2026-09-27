"""Stripe PaymentProvider - checkout + signed webhooks via the official SDK."""

from __future__ import annotations

from typing import Any, cast

import stripe
from config.secrets import get_secret
from stripe import SignatureVerificationError, StripeError

from core.payments.provider import PaymentError, PaymentWebhookError


class StripePaymentProvider:
    """Test-mode Stripe adapter - create_checkout and verify_webhook only."""

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self._secret_key = secret_key or get_secret("STRIPE_SECRET_KEY")
        self._webhook_secret = webhook_secret or get_secret("STRIPE_WEBHOOK_SECRET")

    def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        stripe.api_key = self._secret_key
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "unit_amount": amount_cents,
                            "product_data": {"name": "Checkout"},
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except StripeError as exc:
            # Never echo Stripe error bodies - they may contain request metadata.
            raise PaymentError("Checkout session creation failed") from exc

        if not session.url or not session.id:
            raise PaymentError("Checkout session creation failed")

        return {"id": session.id, "url": session.url}

    def verify_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not signature:
            raise PaymentWebhookError(
                "Webhook verification rejected: missing signature"
            )

        try:
            event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
                payload, signature, self._webhook_secret
            )
        except SignatureVerificationError as exc:
            raise PaymentWebhookError(
                "Webhook verification rejected: invalid signature"
            ) from exc
        except ValueError as exc:
            raise PaymentWebhookError(
                "Webhook verification rejected: invalid payload"
            ) from exc

        return cast(dict[str, Any], event.to_dict())
