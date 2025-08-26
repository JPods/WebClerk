# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/utils/global_storage.py
import time
import threading
from typing import Any, Optional


class GlobalStorage:
    """A thread-safe in-memory key-value store with expiration for caching database queries."""

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, expiry_seconds: int = 3600) -> None:
        """
        Store a key-value pair with an expiration time.

        Args:
            key: The key to store the value under.
            value: The value to store.
            expiry_seconds: Expiration time in seconds (default: 3600 seconds).
        """
        with self._lock:
            self._store[key] = {"value": value, "timestamp": time.time(), "expiry_seconds": expiry_seconds}

    def get(self, key: str, force_refresh: bool = False) -> Optional[Any]:
        """
        Retrieve a value by key, checking for existence and expiration.

        Args:
            key: The key to retrieve the value for.
            force_refresh: If True, bypasses the cache (default: False).

        Returns:
            The stored value if it exists and is not expired, else None.
        """
        with self._lock:
            if force_refresh or key not in self._store:
                return None

            entry = self._store[key]
            current_time = time.time()
            if current_time > entry["timestamp"] + entry["expiry_seconds"]:
                # Entry has expired, remove it
                self._store.pop(key, None)
                return None

            return entry["value"]

    def clear(self, key: str) -> None:
        """
        Remove a specific key from the store.

        Args:
            key: The key to remove.
        """
        with self._lock:
            self._store.pop(key, None)
