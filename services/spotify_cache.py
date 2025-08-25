"""Cache system for Spotify search results with lazy loading."""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with data and metadata."""

    data: Any
    timestamp: float
    ttl: float = 300.0  # 5 minutes default TTL

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl


class SpotifySearchCache:
    """Cache for Spotify search results with pagination support."""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_cache_size = 1000

    def _cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired]
        for key in expired_keys:
            del self._cache[key]

    def _enforce_cache_limit(self):
        """Enforce cache size limit by removing oldest entries."""
        if len(self._cache) > self._max_cache_size:
            # Sort by timestamp and remove oldest entries
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1].timestamp)
            to_remove = len(self._cache) - self._max_cache_size
            for key, _ in sorted_items[:to_remove]:
                del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """Get cached data if exists and not expired."""
        self._cleanup_expired()

        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry.data
        elif entry:
            # Remove expired entry
            del self._cache[key]

        return None

    def set(self, key: str, data: Any, ttl: float = 300.0):
        """Set cache data with TTL."""
        self._cache[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)

        self._enforce_cache_limit()

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern or all if no pattern."""
        if pattern is None:
            self._cache.clear()
        else:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {"total_entries": len(self._cache), "max_size": self._max_cache_size}


# Global cache instance
spotify_cache = SpotifySearchCache()
