import time
import hashlib
from typing import Any, Dict, Tuple, Optional
from django.conf import settings

_cache: Dict[str, Tuple[Any, Optional[float]]] = {}

class CacheService:
    """Centralized in-memory cache service with versioning."""

    def __init__(self):
        self.cache = _cache
        self.version = self._get_cache_version()

    def _get_cache_version(self) -> str:
        """Generate cache version based on SECRET_KEY to invalidate on deployments."""
        return hashlib.md5(settings.SECRET_KEY.encode()).hexdigest()[:8]

    def make_key(self, namespace: str, *parts) -> str:
        """Create versioned cache key with namespace."""
        key_parts = [self.version, namespace] + [str(p) for p in parts]
        return ":".join(key_parts)

    def get(self, key: str, default=None) -> Any:
        """Get value from cache, with fallback."""
        entry = self.cache.get(key)
        if not entry:
            return default
        value, expire = entry
        if expire is not None and time.time() > expire:
            del self.cache[key]
            return default
        return value

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache with TTL."""
        expire = time.time() + ttl if ttl else None
        self.cache[key] = (value, expire)

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]

    def invalidate_namespace(self, namespace: str) -> None:
        """Invalidate all keys in a namespace."""
        prefix = f"{self.version}:{namespace}:"
        keys_to_delete = [k for k in list(self.cache) if k.startswith(prefix)]
        for k in keys_to_delete:
            del self.cache[k]

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        entry = self.cache.get(key)
        if not entry:
            return False
        _, expire = entry
        if expire is not None and time.time() > expire:
            del self.cache[key]
            return False
        return True

    def get_ttl(self, key: str) -> int:
        """Get TTL for key."""
        entry = self.cache.get(key)
        if not entry:
            return -1
        _, expire = entry
        if expire is None:
            return -1
        remaining = int(expire - time.time())
        return remaining if remaining > 0 else -1

# Global instance
cache_service = CacheService()