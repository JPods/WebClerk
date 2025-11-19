import redis
import json
import hashlib
from typing import Any
from django.conf import settings


class CacheService:
    """Centralized Redis-based cache service with versioning and async updates."""

    def __init__(self):
        try:
            self.redis = redis.Redis.from_url(settings.CELERY_RESULT_BACKEND)
            self.version = self._get_cache_version()
        except Exception:
            # Graceful degradation if Redis unavailable
            self.redis = None
            self.version = "fallback"

    def _get_cache_version(self) -> str:
        """Generate cache version based on SECRET_KEY to invalidate on deployments."""
        return hashlib.md5(settings.SECRET_KEY.encode()).hexdigest()[:8]

    def make_key(self, namespace: str, *parts) -> str:
        """Create versioned cache key with namespace."""
        key_parts = [self.version, namespace] + [str(p) for p in parts]
        return ":".join(key_parts)

    def get(self, key: str, default=None) -> Any:
        """Get value from cache, with fallback."""
        if not self.redis:
            return default
        try:
            data = self.redis.get(key)
            if data is None:
                return default
            # Handle both bytes and str
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return json.loads(data)
        except Exception:
            return default

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in cache with TTL."""
        if not self.redis:
            return
        try:
            self.redis.setex(key, ttl, json.dumps(value))
        except Exception:
            pass  # Silent failure for graceful degradation

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if not self.redis:
            return
        try:
            self.redis.delete(key)
        except Exception:
            pass

    def invalidate_namespace(self, namespace: str) -> None:
        """Invalidate all keys in a namespace."""
        if not self.redis:
            return
        try:
            pattern = f"{self.version}:{namespace}:*"
            keys = self.redis.keys(pattern)
            if keys:
                # Handle both single key and list of keys
                if isinstance(keys, list):
                    self.redis.delete(*keys)
                else:
                    self.redis.delete(keys)
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.redis:
            return False
        try:
            result = self.redis.exists(key)
            return bool(result)
        except Exception:
            return False

    def get_ttl(self, key: str) -> int:
        """Get TTL for key."""
        if not self.redis:
            return -1
        try:
            result = self.redis.ttl(key)
            # Redis.ttl returns -1 if key doesn't exist, -2 if expired
            # or the remaining TTL in seconds
            if isinstance(result, (int, float)):
                return int(result)
            return -1
        except Exception:
            return -1


# Global instance
cache_service = CacheService()