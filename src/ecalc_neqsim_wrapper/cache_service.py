"""Centralized cache management for NeqSim-related caches.

All caches registered here will be cleared when the JVM service shuts down,
ensuring no dangling references to JVM objects.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

_logger = logging.getLogger(__name__)

K = TypeVar("K")
V = TypeVar("V")


class CacheName(str, Enum):
    """Registry of all cache names used in ecalc."""

    REFERENCE_FLUID = "reference_fluid"
    FLUID_SERVICE_FLASH = "fluid_service_flash"


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for NeqSimFluidService caches.

    Attributes:
        reference_fluid_max_size: Max entries in reference fluid cache.
            Stores NeqsimFluid instances at standard conditions.
            Using a default max size that covers use cases seen so far.
            Default: 512

        flash_max_size: Max entries in flash results cache.
            Stores FluidProperties for TP/PH flash operations.
            Using a default max size that covers use cases seen so far.
            Default: 100_000
    """

    reference_fluid_max_size: int = 512
    flash_max_size: int = 100_000

    @classmethod
    def default(cls) -> CacheConfig:
        """Return default cache configuration."""
        return cls()


class LRUCache(Generic[K, V]):
    """Thread-safe LRU cache with statistics tracking."""

    def __init__(self, max_size: int = 10000):
        """Initialize LRU cache with specified maximum size.

        Note: For caches that hold JVM objects (like NeqsimFluid), use
        CacheService.create_cache() to ensure proper cleanup on JVM shutdown.
        """
        self._cache: OrderedDict[K, V] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._stats: dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: K) -> V | None:
        """Get value from cache, returns None if not found."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return self._cache[key]
            self._stats["misses"] += 1
            return None

    def put(self, key: K, value: V) -> None:
        """Add value to cache with LRU eviction.

        Note: If max_size is 0, caching is disabled and this is a no-op.
        """
        with self._lock:
            if self._max_size == 0:
                return  # Cache disabled, skip the add-then-evict cycle

            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value

            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1

    def clear(self) -> None:
        """Clear all cached entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self._max_size,
                "hit_rate_percent": round(hit_rate, 1),
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


class CacheService:
    """Central registry for application caches.

    Usage:
        # Create a cache
        my_cache = CacheService.create_cache("my_cache", max_size=1000)

        # Use it
        my_cache.put(key, value)
        value = my_cache.get(key)

        # All caches cleared on JVM shutdown automatically
    """

    _caches: dict[str, LRUCache] = {}
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def create_cache(cls, name: str, max_size: int = 10000) -> LRUCache:
        """Create and register a named cache.

        If a cache with this name already exists, returns the existing cache.
        Note: The existing cache retains its original max_size (logs warning if different).
        """
        with cls._lock:
            if name in cls._caches:
                existing = cls._caches[name]
                if existing._max_size != max_size:
                    _logger.warning(
                        f"Cache '{name}' already exists with max_size={existing._max_size}, "
                        f"ignoring requested max_size={max_size}. "
                        f"Configure cache sizes before first use."
                    )
                else:
                    _logger.debug(f"Returning existing cache '{name}' (max_size={existing._max_size})")
                return existing
            cache: LRUCache = LRUCache(max_size)
            cls._caches[name] = cache
            return cache

    @classmethod
    def get_cache(cls, name: str) -> LRUCache | None:
        """Get a cache by name."""
        with cls._lock:
            return cls._caches.get(name)

    @classmethod
    def clear_all(cls) -> None:
        """Clear all registered caches. Called on JVM shutdown."""
        with cls._lock:
            for cache in cls._caches.values():
                cache.clear()

    @classmethod
    def clear_cache(cls, name: str) -> None:
        """Clear a specific cache by name."""
        with cls._lock:
            if name in cls._caches:
                cls._caches[name].clear()

    @classmethod
    def get_all_stats(cls) -> dict[str, dict]:
        """Get stats from all caches for monitoring."""
        with cls._lock:
            return {name: cache.get_stats() for name, cache in cls._caches.items()}
