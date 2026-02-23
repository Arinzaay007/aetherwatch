"""
AetherWatch — Thread-safe TTL Cache
Wraps cachetools.TTLCache with a threading.Lock for safe concurrent access.
"""

import threading
import time
from typing import Any, Callable
from cachetools import TTLCache


class SafeTTLCache:
    """Thread-safe TTL cache with optional fallback value on miss."""

    def __init__(self, maxsize: int = 128, ttl: int = 30):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Return cached value or call fetch_fn, cache the result, and return it."""
        cached = self.get(key)
        if cached is not None:
            return cached
        result = fetch_fn(*args, **kwargs)
        if result is not None:
            self.set(key, result)
        return result

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# Module-level shared caches
aviation_cache = SafeTTLCache(maxsize=10, ttl=15)
satellite_cache = SafeTTLCache(maxsize=20, ttl=300)
camera_cache = SafeTTLCache(maxsize=30, ttl=10)


def cached(ttl: int = 60):
    import functools, time
    def decorator(fn):
        _store = {}
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in _store:
                result, ts = _store[key]
                if time.time() - ts < ttl:
                    return result
            result = fn(*args, **kwargs)
            _store[key] = (result, time.time())
            return result
        return wrapper
    return decorator
def cache_stats() -> dict:
    return {
        "aviation": {"size": len(aviation_cache._cache)},
        "satellite": {"size": len(satellite_cache._cache)},
        "camera": {"size": len(camera_cache._cache)},
    }
def cache_stats() -> dict:
    total = len(aviation_cache._cache) + len(satellite_cache._cache) + len(camera_cache._cache)
    return {
        "valid_entries": total,
        "total_entries": total,
        "aviation": len(aviation_cache._cache),
        "satellite": len(satellite_cache._cache),
        "camera": len(camera_cache._cache),
    }
