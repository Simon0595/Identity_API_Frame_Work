"""Build Django CACHES from CACHE_URL / REDIS_URL - LocMem when unset."""

from __future__ import annotations

from urllib.parse import urlparse

_LOC_MEM_BACKEND = "django.core.cache.backends.locmem.LocMemCache"
_REDIS_BACKEND = "django.core.cache.backends.redis.RedisCache"


def build_caches(*, cache_url: str | None) -> dict[str, dict[str, str]]:
    """Return a CACHES dict. Empty URL -> LocMem (hermetic dev/test/CI default)."""
    url = (cache_url or "").strip()
    if not url:
        return {
            "default": {
                "BACKEND": _LOC_MEM_BACKEND,
                "LOCATION": "default-locmem",
            }
        }
    scheme = urlparse(url).scheme
    if scheme not in ("redis", "rediss"):
        msg = f"CACHE_URL scheme must be redis or rediss, got {scheme!r}"
        raise ValueError(msg)
    return {
        "default": {
            "BACKEND": _REDIS_BACKEND,
            "LOCATION": url,
        }
    }


def is_shared_cache(caches: dict[str, dict[str, str]]) -> bool:
    """True when the default backend is not LocMem - required for multi-worker prod."""
    return caches["default"]["BACKEND"] != _LOC_MEM_BACKEND
