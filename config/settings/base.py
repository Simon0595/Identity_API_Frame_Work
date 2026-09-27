"""
Shared Django settings. Secrets and environment-specific flags live in env vars
so PostgreSQL can replace SQLite without code changes (engine/name/host via env).
"""

import os
from pathlib import Path

from csp.constants import NONE

from config.settings.cache_config import build_caches

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Fail fast if unset - never ship a default secret in code.
SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS: list[str] = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "csp",
    "rest_framework",
    "domain",
    "domain2",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "config.middleware.PermissionsPolicyMiddleware",
    # Above CommonMiddleware so preflight/Origin checks run before URL normalization.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Default SQLite for the prototype; swap engine/credentials via env for PostgreSQL.
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Dev/test expose /admin/ for inspection; prod overlay sets False.
ENABLE_DJANGO_ADMIN = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Global throttles - anon IP limit + per-sub read limit on all views.
    # Views with their own throttle_classes (e.g. write) replace this list entirely.
    "DEFAULT_THROTTLE_CLASSES": [
        "domain.throttling.GlobalAnonRateThrottle",
        "domain.throttling.IdentityReadThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON_RATE", "30/min"),
        "identity_read": os.getenv("THROTTLE_USER_READ_RATE", "120/min"),
        "identity_write": os.getenv("THROTTLE_IDENTITY_WRITE_RATE", "60/min"),
    },
}

# CORS - explicit allowlist only; empty default keeps dev/test/CI hermetic.
# Bearer-token auth: never enable credentials (wildcard + credentials is unsafe).
CORS_ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = False

# Security response headers - JSON API only; the SPA host sets its own CSP.
SECURE_REFERRER_POLICY = "same-origin"
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [NONE],
    },
}

# Cache. LocMem by default. Set CACHE_URL or REDIS_URL for a shared backend.
# Prod needs Redis so throttle counters and webhook de-dupe work across workers.
CACHES = build_caches(cache_url=os.getenv("CACHE_URL") or os.getenv("REDIS_URL"))

# local = offline HS256. cognito = real pool.
AUTH_ISSUER = os.getenv("AUTH_ISSUER", "local")
AUTH_LOCAL_SIGNING_KEY = os.getenv(
    "AUTH_LOCAL_SIGNING_KEY",
    "test-only-local-signing-key-not-for-production",
)
AUTH_LOCAL_ISSUER = os.getenv("AUTH_LOCAL_ISSUER", "https://local.test/issuer")
AUTH_LOCAL_AUDIENCE = os.getenv("AUTH_LOCAL_AUDIENCE", "api-web-framework")

# Cognito - placeholders only; do not commit real COGNITO_* / AWS_* values.
COGNITO_REGION = os.getenv("COGNITO_REGION", "")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "")
_default_cognito_issuer = (
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
    if COGNITO_REGION and COGNITO_USER_POOL_ID
    else ""
)
COGNITO_ISSUER = os.getenv("COGNITO_ISSUER", _default_cognito_issuer)
COGNITO_JWKS_URL = os.getenv(
    "COGNITO_JWKS_URL",
    f"{COGNITO_ISSUER}/.well-known/jwks.json" if COGNITO_ISSUER else "",
)

# Default disabled - no Stripe account for dev/CI.
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "disabled")
