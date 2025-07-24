"""
Cache Management System
======================

High - performance caching for systematic review automation.

This module provides:
- Memory - based caching with LRU eviction
- Redis - based distributed caching
- Intelligent cache strategies
- Cache performance monitoring

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import hashlib
import json
import logging
import pickle
import threading
import time
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Redis, fallback gracefully
try:
    import redis
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using memory - only caching")


class CacheStrategy(Enum):
    """Cache strategy options"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"


@dataclass
class CacheConfig:
    """Cache configuration"""

    strategy: CacheStrategy = CacheStrategy.LRU
    max_size: int = 10000
    default_ttl: int = 3600  # seconds
    redis_url: Optional[str] = None
    enable_compression: bool = True
    compression_threshold: int = 1024  # bytes
    enable_metrics: bool = True
    max_memory_mb: int = 512


@dataclass
class CacheEntry:
    """Individual cache entry"""

    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    compressed: bool = False

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False

        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl

    @property
    def age_seconds(self) -> float:
        """Get age in seconds"""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


@dataclass
class CacheMetrics:
    """Cache performance metrics"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    average_access_time_ms: float = 0.0

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class BaseCache(ABC):
    """Abstract base class for cache implementations"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.metrics = CacheMetrics()
        self._lock = threading.RLock()

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    def _generate_key(self, base_key: str, *args, **kwargs) -> str:
        """Generate cache key from base key and parameters"""
        key_components = [base_key]

        if args:
            key_components.extend(str(arg) for arg in args)

        if kwargs:
            # Sort kwargs for consistent key generation
            sorted_kwargs = sorted(kwargs.items())
            key_components.extend(f"{k}={v}" for k, v in sorted_kwargs)

        key_string = "|".join(key_components)

        # Hash long keys to avoid length limits
        if len(key_string) > 200:
            return hashlib.sha256(key_string.encode()).hexdigest()

        return key_string

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        serialized = pickle.dumps(value)

        if self.config.enable_compression and len(serialized) > self.config.compression_threshold:
            try:
                import gzip

                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized):
                    return b"COMPRESSED:" + compressed
            except ImportError:
                pass

        return serialized

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if data.startswith(b"COMPRESSED:"):
            try:
                import gzip

                data = gzip.decompress(data[11:])  # Remove 'COMPRESSED:' prefix
            except ImportError:
                raise ValueError("Gzip not available for decompression")

        return pickle.loads(data)


class MemoryCache(BaseCache):
    """In - memory cache implementation with LRU eviction"""

    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._access_count: Dict[str, int] = {}  # For LFU tracking

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        start_time = time.time()

        with self._lock:
            if key not in self._cache:
                self.metrics.misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired:
                await self._evict_key(key)
                self.metrics.misses += 1
                return None

            # Update access tracking
            entry.accessed_at = datetime.now(timezone.utc)
            entry.access_count += 1

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            # Update LFU count
            self._access_count[key] = self._access_count.get(key, 0) + 1

            self.metrics.hits += 1
            access_time = (time.time() - start_time) * 1000
            self.metrics.average_access_time_ms = (self.metrics.average_access_time_ms + access_time) / 2

            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache"""
        try:
            with self._lock:
                # Calculate size
                serialized = self._serialize_value(value)
                size_bytes = len(serialized)

                # Check if we need to evict entries
                await self._ensure_capacity(size_bytes)

                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(timezone.utc),
                    accessed_at=datetime.now(timezone.utc),
                    ttl=ttl or self.config.default_ttl,
                    size_bytes=size_bytes,
                    compressed=serialized.startswith(b"COMPRESSED:"),
                )

                # Store entry
                self._cache[key] = entry

                # Update tracking
                if key not in self._access_order:
                    self._access_order.append(key)

                # Update metrics
                self.metrics.entry_count = len(self._cache)
                self.metrics.total_size_bytes += size_bytes

                return True

        except Exception as e:
            logger.error(f"Failed to set cache entry {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from memory cache"""
        with self._lock:
            if key in self._cache:
                await self._evict_key(key)
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._access_count.clear()
            self.metrics = CacheMetrics()
            return True

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired:
                await self._evict_key(key)
                return False

            return True

    async def _ensure_capacity(self, new_size: int):
        """Ensure cache has capacity for new entry"""
        # Check memory limit
        current_memory_mb = self.metrics.total_size_bytes / (1024 * 1024)
        new_memory_mb = (self.metrics.total_size_bytes + new_size) / (1024 * 1024)

        if new_memory_mb > self.config.max_memory_mb:
            await self._evict_entries_by_memory(new_size)

        # Check entry count limit
        if len(self._cache) >= self.config.max_size:
            await self._evict_entries_by_count()

    async def _evict_entries_by_memory(self, required_space: int):
        """Evict entries to free memory"""
        target_memory = self.config.max_memory_mb * (1024 * 1024) * 0.8  # 80% of limit

        while self.metrics.total_size_bytes + required_space > target_memory and self._cache:
            await self._evict_single_entry()

    async def _evict_entries_by_count(self):
        """Evict entries to free space"""
        target_count = int(self.config.max_size * 0.8)  # 80% of limit

        while len(self._cache) > target_count:
            await self._evict_single_entry()

    async def _evict_single_entry(self):
        """Evict single entry based on strategy"""
        if not self._cache:
            return

        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used
            key_to_evict = self._access_order[0]
        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            if self._access_count:
                key_to_evict = min(self._access_count.keys(), key=lambda k: self._access_count[k])
            else:
                key_to_evict = next(iter(self._cache)) if self._cache else None
        elif self.config.strategy == CacheStrategy.TTL:
            # Remove oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
            key_to_evict = oldest_key
        else:
            # Default to LRU
            key_to_evict = self._access_order[0] if self._access_order else next(iter(self._cache))

        await self._evict_key(key_to_evict)

    async def _evict_key(self, key: str):
        """Evict specific key"""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]

            if key in self._access_order:
                self._access_order.remove(key)

            if key in self._access_count:
                del self._access_count[key]

            self.metrics.total_size_bytes -= entry.size_bytes
            self.metrics.entry_count = len(self._cache)
            self.metrics.evictions += 1


class RedisCache(BaseCache):
    """Redis - based distributed cache implementation"""

    def __init__(self, config: CacheConfig):
        super().__init__(config)

        if not REDIS_AVAILABLE:
            raise ImportError("Redis is required for RedisCache")

        if not config.redis_url:
            raise ValueError("Redis URL is required for RedisCache")

        self._redis_pool = None
        self._client = None

    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if self._client is None:
            self._client = aioredis.from_url(self.config.redis_url, encoding="utf - 8", decode_responses=False)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            await self._ensure_connection()

            data = await self._client.get(key)
            if data is None:
                self.metrics.misses += 1
                return None

            value = self._deserialize_value(data)
            self.metrics.hits += 1
            return value

        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self.metrics.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        try:
            await self._ensure_connection()

            serialized = self._serialize_value(value)
            ttl_seconds = ttl or self.config.default_ttl

            await self._client.setex(key, ttl_seconds, serialized)
            return True

        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        try:
            await self._ensure_connection()

            result = await self._client.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            await self._ensure_connection()

            await self._client.flushdb()
            return True

        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache"""
        try:
            await self._ensure_connection()

            result = await self._client.exists(key)
            return result > 0

        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False


class CacheManager:
    """
    High - level cache manager with multiple backends and intelligent routing
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache manager

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self.primary_cache = self._create_primary_cache()
        self.secondary_cache = self._create_secondary_cache()
        self.decorators = CacheDecorators(self)

        logger.info(f"Cache manager initialized with {type(self.primary_cache).__name__}")

    def _create_primary_cache(self) -> BaseCache:
        """Create primary cache instance"""
        return MemoryCache(self.config)

    def _create_secondary_cache(self) -> Optional[BaseCache]:
        """Create secondary cache instance (Redis if available)"""
        if REDIS_AVAILABLE and self.config.redis_url:
            try:
                return RedisCache(self.config)
            except Exception as e:
                logger.warning(f"Failed to create Redis cache: {e}")
        return None

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with fallback strategy

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        # Try primary cache first
        value = await self.primary_cache.get(key)
        if value is not None:
            return value

        # Try secondary cache
        if self.secondary_cache:
            value = await self.secondary_cache.get(key)
            if value is not None:
                # Write back to primary cache
                await self.primary_cache.set(key, value)
                return value

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with write - through strategy

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        success = True

        # Write to primary cache
        primary_success = await self.primary_cache.set(key, value, ttl)
        if not primary_success:
            success = False

        # Write to secondary cache
        if self.secondary_cache:
            secondary_success = await self.secondary_cache.set(key, value, ttl)
            if not secondary_success:
                logger.warning(f"Failed to write to secondary cache: {key}")

        return success

    async def delete(self, key: str) -> bool:
        """
        Delete value from all cache levels

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        success = True

        # Delete from primary cache
        if not await self.primary_cache.delete(key):
            success = False

        # Delete from secondary cache
        if self.secondary_cache:
            if not await self.secondary_cache.delete(key):
                success = False

        return success

    async def clear(self) -> bool:
        """Clear all cache levels"""
        success = True

        if not await self.primary_cache.clear():
            success = False

        if self.secondary_cache:
            if not await self.secondary_cache.clear():
                success = False

        return success

    async def exists(self, key: str) -> bool:
        """Check if key exists in any cache level"""
        if await self.primary_cache.exists(key):
            return True

        if self.secondary_cache:
            return await self.secondary_cache.exists(key)

        return False

    def get_metrics(self) -> Dict[str, CacheMetrics]:
        """Get metrics from all cache levels"""
        metrics = {"primary": self.primary_cache.metrics}

        if self.secondary_cache:
            metrics["secondary"] = self.secondary_cache.metrics

        return metrics

    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key with consistent format"""
        return self.primary_cache._generate_key(prefix, *args, **kwargs)


class CacheDecorators:
    """Cache decorators for easy function caching"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    def cached(self, key_prefix: str, ttl: Optional[int] = None):
        """
        Decorator to cache function results

        Args:
            key_prefix: Prefix for cache key
            ttl: Time to live in seconds
        """

        def decorator(func):
            """TODO: Add docstring for decorator."""

            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.cache_manager.cache_key(key_prefix, *args, **kwargs)

                # Try to get from cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Cache result
                await self.cache_manager.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator

    def cache_invalidate(self, key_prefix: str):
        """
        Decorator to invalidate cache entries

        Args:
            key_prefix: Prefix for cache key
        """

        def decorator(func):
            """TODO: Add docstring for decorator."""

            async def wrapper(*args, **kwargs):
                # Execute function first
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Invalidate cache
                cache_key = self.cache_manager.cache_key(key_prefix, *args, **kwargs)
                await self.cache_manager.delete(cache_key)

                return result

            return wrapper

        return decorator


# Example usage and testing functions
async def demo_cache_manager():
    """Demonstrate cache manager capabilities"""
    print("💾 Cache Manager Demo")
    print("=" * 30)

    # Initialize cache manager
    config = CacheConfig(strategy=CacheStrategy.LRU, max_size=1000, default_ttl=300, enable_compression=True)
    cache_manager = CacheManager(config)

    # Test basic operations
    print("📝 Testing basic cache operations...")

    # Set values
    await cache_manager.set("user:123", {"name": "John", "age": 30})
    await cache_manager.set("study:456", {"title": "AI Research", "year": 2023})

    # Get values
    user = await cache_manager.get("user:123")
    study = await cache_manager.get("study:456")

    print(f"   Retrieved user: {user}")
    print(f"   Retrieved study: {study}")

    # Test cache miss
    missing = await cache_manager.get("nonexistent")
    print(f"   Missing key result: {missing}")

    # Test decorators
    print("\n🎯 Testing cache decorators...")

    @cache_manager.decorators.cached("expensive_calc", ttl=60)
    async def expensive_calculation(n: int) -> int:
        # Simulate expensive operation
        await asyncio.sleep(0.1)
        return n * n * n

    # First call (cache miss)
    start_time = time.time()
    result1 = await expensive_calculation(10)
    time1 = time.time() - start_time

    # Second call (cache hit)
    start_time = time.time()
    result2 = await expensive_calculation(10)
    time2 = time.time() - start_time

    print(f"   First call (miss): {result1} in {time1:.3f}s")
    print(f"   Second call (hit): {result2} in {time2:.3f}s")
    print(f"   Speed improvement: {time1 / time2:.1f}x")

    # Get metrics
    metrics = cache_manager.get_metrics()
    primary_metrics = metrics["primary"]

    print(f"\n📊 Cache Metrics:")
    print(f"   Hit ratio: {primary_metrics.hit_ratio:.1%}")
    print(f"   Entries: {primary_metrics.entry_count}")
    print(f"   Total size: {primary_metrics.total_size_bytes} bytes")
    print(f"   Evictions: {primary_metrics.evictions}")

    return cache_manager


if __name__ == "__main__":
    asyncio.run(demo_cache_manager())
