"""Cache settings - LocMem default; Redis when CACHE_URL is set."""

import os
import subprocess
import sys
import textwrap

import pytest
from config.settings.cache_config import build_caches, is_shared_cache
from django.test import override_settings

_LOC_MEM = "django.core.cache.backends.locmem.LocMemCache"
_REDIS = "django.core.cache.backends.redis.RedisCache"


def test_build_caches_defaults_to_locmem_when_url_unset() -> None:
    """Dev/test/CI with no env var must stay on per-process LocMem."""
    caches = build_caches(cache_url=None)
    assert caches["default"]["BACKEND"] == _LOC_MEM
    assert not is_shared_cache(caches)


def test_build_caches_uses_redis_when_cache_url_set() -> None:
    """CACHE_URL selects Django's built-in Redis backend - shared across workers."""
    url = "redis://cache.example.com:6379/0"
    caches = build_caches(cache_url=url)
    assert caches["default"]["BACKEND"] == _REDIS
    assert caches["default"]["LOCATION"] == url
    assert is_shared_cache(caches)


def test_build_caches_accepts_rediss_scheme() -> None:
    """TLS Redis URLs (rediss://) are valid for production cache endpoints."""
    url = "rediss://cache.example.com:6380/1"
    caches = build_caches(cache_url=url)
    assert caches["default"]["BACKEND"] == _REDIS
    assert caches["default"]["LOCATION"] == url


def test_build_caches_rejects_non_redis_scheme() -> None:
    """Fail closed on misconfigured cache URLs - no silent fallback."""
    with pytest.raises(ValueError, match="redis"):
        build_caches(cache_url="memcached://127.0.0.1:11211")


def test_base_settings_use_locmem_without_cache_url() -> None:
    """Imported test settings must not require Redis for hermetic pytest runs."""
    from django.conf import settings

    assert settings.CACHES["default"]["BACKEND"] == _LOC_MEM


def test_prod_import_requires_shared_cache_url() -> None:
    """Prod overlay must refuse LocMem - throttle/dedup would be per-worker only."""
    env = os.environ.copy()
    env.update(
        {
            "SECRET_KEY": "test-only-not-for-production",
            "ALLOWED_HOSTS": "example.com",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/mydb",
        }
    )
    script = textwrap.dedent(
        """
        try:
            import config.settings.prod # noqa: F401
        except Exception as exc:
            assert "CACHE_URL" in str(exc) or "REDIS_URL" in str(exc)
        else:
            raise AssertionError("expected ImproperlyConfigured without CACHE_URL")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@override_settings(
    CACHES=build_caches(cache_url="redis://127.0.0.1:6379/2"),
)
def test_override_settings_can_swap_to_redis_backend() -> None:
    """Tests can opt into Redis config without touching process env."""
    from django.conf import settings

    assert settings.CACHES["default"]["BACKEND"] == _REDIS
