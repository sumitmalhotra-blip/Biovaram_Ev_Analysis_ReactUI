"""
In-memory LRU cache for parsed FCS data.

Avoids re-parsing large FCS files (900k+ events) on every API request.
Cache is keyed by absolute file path and invalidated by file mtime.
Limited to 5 entries (~500MB peak for typical EV datasets).
"""

import os
import time
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd
from loguru import logger


class _FCSDataCache:
    """Thread-safe LRU cache for parsed FCS DataFrames."""

    def __init__(self, max_entries: int = 5):
        self._cache: OrderedDict[str, Tuple[float, pd.DataFrame, List[str]]] = OrderedDict()
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, file_path: str) -> Optional[Tuple[pd.DataFrame, List[str]]]:
        """Return (parsed_data, channel_names) if cached and file unchanged, else None."""
        key = os.path.normpath(os.path.abspath(file_path))

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            cached_mtime, data, channels = entry

            # Invalidate if file was modified since caching
            try:
                current_mtime = os.path.getmtime(file_path)
            except OSError:
                # File removed — evict
                self._cache.pop(key, None)
                self._misses += 1
                return None

            if current_mtime != cached_mtime:
                self._cache.pop(key, None)
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"FCS cache HIT for {Path(file_path).name} (hits={self._hits})")
            return data, channels

    def put(self, file_path: str, data: pd.DataFrame, channels: List[str]) -> None:
        """Store parsed FCS data. Evicts LRU entry if cache is full."""
        key = os.path.normpath(os.path.abspath(file_path))

        try:
            mtime = os.path.getmtime(file_path)
        except OSError:
            return  # Don't cache if file doesn't exist

        with self._lock:
            # Remove existing entry to refresh position
            self._cache.pop(key, None)

            # Evict oldest if at capacity
            while len(self._cache) >= self._max_entries:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug(f"FCS cache evicted: {Path(evicted_key).name}")

            self._cache[key] = (mtime, data, channels)
            logger.debug(f"FCS cache stored: {Path(file_path).name} ({len(data)} events, {len(self._cache)}/{self._max_entries} entries)")

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._cache),
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
            }


# Module-level singleton
_fcs_cache = _FCSDataCache(max_entries=5)


def get_cached_fcs_data(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Parse an FCS file, using cache when possible.
    
    Returns:
        (parsed_data_df, channel_names_list)
    """
    cached = _fcs_cache.get(file_path)
    if cached is not None:
        return cached

    # Cache miss — parse the file
    from src.parsers.fcs_parser import FCSParser

    parser = FCSParser(file_path)
    parsed_data = parser.parse()
    channels = parser.channel_names

    _fcs_cache.put(file_path, parsed_data, channels)
    return parsed_data, channels


def clear_fcs_cache() -> None:
    """Clear the FCS parsing cache (e.g., on file deletion)."""
    _fcs_cache.clear()


def fcs_cache_stats() -> dict:
    """Return cache statistics."""
    return _fcs_cache.stats
