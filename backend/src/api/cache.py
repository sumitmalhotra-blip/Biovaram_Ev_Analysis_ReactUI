"""
In-memory TTL cache for expensive computations.

Caches FCS parsing, scatter-data, distribution analysis,
and other heavy endpoints to avoid re-computing on every request.

No external dependencies (no Redis needed) — simple dict-based cache
with TTL expiration and max-size eviction.
"""

import time
import hashlib
import json
from typing import Any, Optional
from dataclasses import dataclass, field
from threading import Lock
from loguru import logger


@dataclass
class CacheEntry:
    """Single cache entry with value and expiration."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    hits: int = 0
    size_bytes: int = 0


class TTLCache:
    """
    Thread-safe in-memory cache with TTL expiration.
    
    Features:
    - Per-key TTL
    - Max size with LRU-like eviction (oldest first)
    - Automatic cleanup of expired entries
    - Cache statistics for monitoring
    """
    
    def __init__(self, max_entries: int = 500, name: str = "default"):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._max_entries = max_entries
        self._name = name
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returns None if expired or missing."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if time.time() > entry.expires_at:
                # Expired
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            entry.hits += 1
            self._stats["hits"] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: float = 60.0) -> None:
        """Store value with TTL."""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_entries and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl_seconds,
            )
            self._stats["sets"] += 1
    
    def invalidate(self, prefix: str) -> int:
        """Remove all entries matching a key prefix. Returns count removed."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def _evict_oldest(self) -> None:
        """Evict the oldest entry (by creation time)."""
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self._stats["evictions"] += 1
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if now > v.expires_at]
            for k in expired:
                del self._cache[k]
            return len(expired)
    
    @property
    def stats(self) -> dict:
        """Cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
        return {
            "name": self._name,
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_pct": round(hit_rate, 1),
            "evictions": self._stats["evictions"],
            "sets": self._stats["sets"],
        }


def make_cache_key(*args: Any) -> str:
    """Create a deterministic cache key from args."""
    raw = json.dumps(args, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


# ============================================================================
# Global cache instances (shared across all requests)
# ============================================================================

# FCS file parsing cache — stores parsed DataFrames
# TTL: 5min (FCS files don't change, but memory is finite)
fcs_parse_cache = TTLCache(max_entries=50, name="fcs_parse")

# Scatter data cache — stores computed scatter plot points
# TTL: 2min (depends on Mie params which user may change)
scatter_cache = TTLCache(max_entries=100, name="scatter_data")

# Distribution analysis cache — stores normality tests + fitting
# TTL: 2min (depends on Mie params)
distribution_cache = TTLCache(max_entries=100, name="distribution")

# Size bins cache — stores size categorization
# TTL: 2min
size_bins_cache = TTLCache(max_entries=100, name="size_bins")

# Sample list cache — stores list query results
# TTL: 10s (changes on upload/delete)
sample_list_cache = TTLCache(max_entries=20, name="sample_list")

# Misc cache — for lighter endpoints
misc_cache = TTLCache(max_entries=200, name="misc")


def get_all_cache_stats() -> list[dict]:
    """Get stats for all cache instances."""
    return [
        fcs_parse_cache.stats,
        scatter_cache.stats,
        distribution_cache.stats,
        size_bins_cache.stats,
        sample_list_cache.stats,
        misc_cache.stats,
    ]


def invalidate_sample_caches(sample_id: str) -> int:
    """Invalidate all cached data for a specific sample."""
    total = 0
    total += scatter_cache.invalidate(f"scatter:{sample_id}:")
    total += distribution_cache.invalidate(f"dist:{sample_id}:")
    total += size_bins_cache.invalidate(f"bins:{sample_id}:")
    total += fcs_parse_cache.invalidate(f"fcs:{sample_id}:")
    total += misc_cache.invalidate(f"anomaly:{sample_id}:")
    total += sample_list_cache.clear() or 0
    if total > 0:
        logger.debug(f"Invalidated {total} cache entries for sample {sample_id}")
    return total


def invalidate_all_caches() -> None:
    """Clear all caches (e.g., after calibration change)."""
    fcs_parse_cache.clear()
    scatter_cache.clear()
    distribution_cache.clear()
    size_bins_cache.clear()
    sample_list_cache.clear()
    misc_cache.clear()
    logger.info("All caches cleared")
