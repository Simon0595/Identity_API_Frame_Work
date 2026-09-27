"""Smoke tests - prove pytest-django and DRF routing work before domain code exists."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_returns_ok() -> None:
    """GET /health/ must return 200 so markers can verify the harness quickly."""
    response = Client().get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
