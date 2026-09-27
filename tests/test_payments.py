"""Payment provider tests - disabled default, no network."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from core.payments.provider import (
    DisabledPaymentProvider,
    PaymentDisabledError,
    PaymentWebhookError,
    get_payment_provider,
)
from core.payments.stripe import StripePaymentProvider
from django.core.cache import cache
from django.test import Client, override_settings
from stripe import SignatureVerificationError

_FAKE_SECRET_KEY = "sk_test_fake_key_for_unit_tests_only"
_FAKE_WEBHOOK_SECRET = "whsec_fake_webhook_secret_for_tests"


def _stripe_provider() -> StripePaymentProvider:
    """Build adapter with injected fakes - no env secrets or network."""
    return StripePaymentProvider(
        secret_key=_FAKE_SECRET_KEY,
        webhook_secret=_FAKE_WEBHOOK_SECRET,
    )


def test_get_payment_provider_defaults_to_disabled() -> None:
    """Default settings resolve to DisabledPaymentProvider - no Stripe in CI."""
    with override_settings(PAYMENT_PROVIDER="disabled"):
        assert isinstance(get_payment_provider(), DisabledPaymentProvider)


def test_get_payment_provider_stripe() -> None:
    """Settings switch returns StripePaymentProvider - same switch as disabled."""
    with override_settings(PAYMENT_PROVIDER="stripe"):
        with patch(
            "core.payments.stripe.get_secret",
            side_effect=[_FAKE_SECRET_KEY, _FAKE_WEBHOOK_SECRET],
        ):
            assert isinstance(get_payment_provider(), StripePaymentProvider)


def test_disabled_create_checkout_raises() -> None:
    """Checkout is unavailable when payments are disabled."""
    provider = DisabledPaymentProvider()
    with pytest.raises(PaymentDisabledError, match="disabled"):
        provider.create_checkout(
            amount_cents=1000,
            currency="eur",
            success_url="https://example.test/success",
            cancel_url="https://example.test/cancel",
        )


def test_disabled_verify_webhook_rejects() -> None:
    """Deny by default - disabled provider rejects all webhook payloads."""
    provider = DisabledPaymentProvider()
    with pytest.raises(PaymentWebhookError, match="rejected"):
        provider.verify_webhook(b"{}", signature=None)


def test_get_payment_provider_unknown_raises() -> None:
    with override_settings(PAYMENT_PROVIDER="unknown-provider"):
        with pytest.raises(Exception, match="Unsupported PAYMENT_PROVIDER"):
            get_payment_provider()


@patch("core.payments.stripe.stripe")
def test_stripe_create_checkout_delegates_to_session_create(
    mock_stripe: MagicMock,
) -> None:
    """Checkout creation delegates to Stripe Session.create (mocked - no network)."""
    mock_stripe.checkout.Session.create.return_value = MagicMock(
        id="cs_test_123",
        url="https://checkout.stripe.test/cs_test_123",
    )
    provider = _stripe_provider()

    result = provider.create_checkout(
        amount_cents=1500,
        currency="eur",
        success_url="https://example.test/success",
        cancel_url="https://example.test/cancel",
    )

    mock_stripe.checkout.Session.create.assert_called_once()
    assert result == {
        "id": "cs_test_123",
        "url": "https://checkout.stripe.test/cs_test_123",
    }
    assert mock_stripe.api_key == _FAKE_SECRET_KEY


@patch("core.payments.stripe.stripe")
def test_stripe_verify_webhook_accepts_valid_signature(
    mock_stripe: MagicMock,
) -> None:
    """Valid signature is accepted - construct_event is the trust boundary."""
    event_payload: dict[str, Any] = {
        "id": "evt_test_1",
        "type": "checkout.session.completed",
    }
    mock_event = MagicMock()
    mock_event.to_dict.return_value = event_payload
    mock_stripe.Webhook.construct_event.return_value = mock_event
    provider = _stripe_provider()

    result = provider.verify_webhook(b'{"id":"evt_test_1"}', signature="sig_valid")

    mock_stripe.Webhook.construct_event.assert_called_once_with(
        b'{"id":"evt_test_1"}',
        "sig_valid",
        _FAKE_WEBHOOK_SECRET,
    )
    assert result == event_payload


def test_stripe_verify_webhook_rejects_missing_signature() -> None:
    provider = _stripe_provider()
    with pytest.raises(PaymentWebhookError, match="missing signature"):
        provider.verify_webhook(b"{}", signature=None)


@patch("core.payments.stripe.stripe")
def test_stripe_verify_webhook_rejects_invalid_signature(
    mock_stripe: MagicMock,
) -> None:
    mock_stripe.Webhook.construct_event.side_effect = SignatureVerificationError(  # type: ignore[no-untyped-call]
        "bad sig", sig_header="sig_bad"
    )
    provider = _stripe_provider()
    with pytest.raises(PaymentWebhookError, match="invalid signature"):
        provider.verify_webhook(b"{}", signature="sig_bad")


_WEBHOOK_URL = "/api/v1/payments/webhook"
_EVENT_BODY = b'{"id":"evt_test_webhook_1","type":"checkout.session.completed"}'


@pytest.fixture(autouse=True)
def _clear_webhook_event_cache() -> None:
    """Each test starts with an empty dedup cache."""
    cache.clear()


@patch("core.payments.stripe.stripe")
def test_webhook_valid_signature_processed_once(
    mock_stripe: MagicMock,
) -> None:
    """Valid signature is accepted via the HTTP endpoint and processed once."""
    mock_event = MagicMock()
    mock_event.to_dict.return_value = {
        "id": "evt_test_webhook_1",
        "type": "checkout.session.completed",
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    client = Client()
    with override_settings(PAYMENT_PROVIDER="stripe"):
        with patch(
            "core.payments.stripe.get_secret",
            side_effect=[_FAKE_SECRET_KEY, _FAKE_WEBHOOK_SECRET],
        ):
            response = client.post(
                _WEBHOOK_URL,
                data=_EVENT_BODY,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_valid",
            )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processed",
        "event_id": "evt_test_webhook_1",
    }


@patch("core.payments.stripe.stripe")
def test_webhook_replay_is_idempotent(mock_stripe: MagicMock) -> None:
    """Same event id twice: first processed, replay already_processed."""
    mock_event = MagicMock()
    mock_event.to_dict.return_value = {
        "id": "evt_test_webhook_1",
        "type": "checkout.session.completed",
    }
    mock_stripe.Webhook.construct_event.return_value = mock_event

    client = Client()
    with override_settings(PAYMENT_PROVIDER="stripe"):
        with patch(
            "core.payments.stripe.get_secret",
            side_effect=[_FAKE_SECRET_KEY, _FAKE_WEBHOOK_SECRET] * 2,
        ):
            first = client.post(
                _WEBHOOK_URL,
                data=_EVENT_BODY,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_valid",
            )
            second = client.post(
                _WEBHOOK_URL,
                data=_EVENT_BODY,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_valid",
            )

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json() == {
        "status": "already_processed",
        "event_id": "evt_test_webhook_1",
    }


def test_webhook_missing_signature_rejected() -> None:
    """Missing Stripe-Signature header is rejected - deny by default."""
    with override_settings(PAYMENT_PROVIDER="stripe"):
        with patch(
            "core.payments.stripe.get_secret",
            side_effect=[_FAKE_SECRET_KEY, _FAKE_WEBHOOK_SECRET],
        ):
            response = Client().post(
                _WEBHOOK_URL,
                data=_EVENT_BODY,
                content_type="application/json",
            )

    assert response.status_code == 400
    assert response.json() == {"detail": "Webhook verification failed."}


@patch("core.payments.stripe.stripe")
def test_webhook_invalid_signature_rejected(mock_stripe: MagicMock) -> None:
    mock_stripe.Webhook.construct_event.side_effect = SignatureVerificationError(  # type: ignore[no-untyped-call]
        "bad sig", sig_header="sig_bad"
    )
    with override_settings(PAYMENT_PROVIDER="stripe"):
        with patch(
            "core.payments.stripe.get_secret",
            side_effect=[_FAKE_SECRET_KEY, _FAKE_WEBHOOK_SECRET],
        ):
            response = Client().post(
                _WEBHOOK_URL,
                data=_EVENT_BODY,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_bad",
            )

    assert response.status_code == 400
    assert response.json() == {"detail": "Webhook verification failed."}


def test_domain_webhook_delegates_to_port_not_stripe() -> None:
    """Seam proof: domain view calls the port, not Stripe SDK imports."""
    mock_provider = MagicMock()
    mock_provider.verify_webhook.return_value = {
        "id": "evt_seam_proof",
        "type": "checkout.session.completed",
    }

    with patch(
        "core.payments.webhook.get_payment_provider",
        return_value=mock_provider,
    ):
        response = Client().post(
            _WEBHOOK_URL,
            data=b'{"id":"evt_seam_proof"}',
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_any",
        )

    assert response.status_code == 200
    mock_provider.verify_webhook.assert_called_once()
    assert mock_provider.verify_webhook.call_args.args[0] == b'{"id":"evt_seam_proof"}'
    assert isinstance(get_payment_provider(), DisabledPaymentProvider)

