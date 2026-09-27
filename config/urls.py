"""Root URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import path
from domain.views import (
    IdentityAuditView,
    IdentityReadView,
    IdentityWriteView,
    PaymentWebhookView,
)
from domain2.views import AssetReadView

from config.views import DevLoginView, MeView, health

_admin_patterns = (
    [path("admin/", admin.site.urls)]
    if getattr(settings, "ENABLE_DJANGO_ADMIN", True)
    else []
)

urlpatterns = [
    path("health/", health, name="health"),
    path("api/v1/me", MeView.as_view(), name="me"),
    path("api/v1/dev/login", DevLoginView.as_view(), name="dev-login"),
    *_admin_patterns,
    path(
        "api/v1/identities/<uuid:person_id>",
        IdentityReadView.as_view(),
        name="identity-read",
    ),
    path(
        "api/v1/identities/<uuid:person_id>/contexts/<str:context>",
        IdentityWriteView.as_view(),
        name="identity-write",
    ),
    path(
        "api/v1/identities/<uuid:person_id>/audit",
        IdentityAuditView.as_view(),
        name="identity-audit",
    ),
    path(
        "api/v1/assets/<uuid:asset_id>",
        AssetReadView.as_view(),
        name="asset-read",
    ),
    path(
        "api/v1/payments/webhook",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
]
