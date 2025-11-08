import time
import threading
from typing import Any, Optional
from apps.core.services.cache_service import cache_service


class GlobalStorage:
    """A thread-safe key-value store that uses Redis for cross-process consistency."""

    def __init__(self):
        self._local_store = {}  # Fallback local storage
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, expiry_seconds: int = 3600) -> None:
        """
        Store a key-value pair with an expiration time.

        Args:
            key: The key to store the value under.
            value: The value to store.
            expiry_seconds: Expiration time in seconds (default: 3600 seconds).
        """
        cache_key = cache_service.make_key('global', key)
        cache_service.set(cache_key, value, ttl=expiry_seconds)

        # Also store locally as fallback
        with self._lock:
            self._local_store[key] = {"value": value, "timestamp": time.time(), "expiry_seconds": expiry_seconds}

    def get(self, key: str, force_refresh: bool = False) -> Optional[Any]:
        """
        Retrieve a value by key, checking for existence and expiration.

        Args:
            key: The key to retrieve the value for.
            force_refresh: If True, bypasses the cache (default: False).

        Returns:
            The stored value if it exists and is not expired, else None.
        """
        if force_refresh:
            return None

        # Try Redis first
        cache_key = cache_service.make_key('global', key)
        cached_value = cache_service.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Fallback to local storage
        with self._lock:
            if key not in self._local_store:
                return None

            entry = self._local_store[key]
            current_time = time.time()
            if current_time > entry["timestamp"] + entry["expiry_seconds"]:
                # Entry has expired, remove it
                self._local_store.pop(key, None)
                return None

            return entry["value"]

    def clear(self, key: str) -> None:
        """
        Remove a specific key from the store.

        Args:
            key: The key to remove.
        """
        cache_key = cache_service.make_key('global', key)
        cache_service.delete(cache_key)

        with self._lock:
            self._local_store.pop(key, None)
