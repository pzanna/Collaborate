"""Performance monitoring and optimization utilities."""

import functools
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable, Dict, Optional


class PerformanceMonitor:
    """Monitor performance metrics for the application."""

    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.start_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        with self._lock:
            self.start_times[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """End timing an operation and record the duration."""
        with self._lock:
            if operation in self.start_times:
                duration = time.time() - self.start_times[operation]
                self.metrics[operation].append(duration)
                del self.start_times[operation]
                return duration
            return 0.0

    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation."""
        with self._lock:
            times = list(self.metrics[operation])
            if not times:
                return {"count": 0, "avg": 0, "min": 0, "max": 0}

            return {
                "count": len(times),
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "recent": times[-10:],  # Last 10 operations
            }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        with self._lock:
            operations = {}
            for operation, times in self.metrics.items():
                if times:
                    operations[operation] = self.get_stats(operation)

            return {"operations": operations, "total_operations": sum(len(times) for times in self.metrics.values())}

    def get_slow_operations(self, threshold: float = 1.0) -> Dict[str, Any]:
        """Get operations that exceed the threshold."""
        with self._lock:
            slow_ops = {}
            for operation, times in self.metrics.items():
                slow_times = [t for t in times if t > threshold]
                if slow_times:
                    slow_ops[operation] = {
                        "count": len(slow_times),
                        "avg": sum(slow_times) / len(slow_times),
                        "max": max(slow_times),
                        "recent": slow_times[-5:],
                    }
            return slow_ops

    def clear_stats(self, operation: Optional[str] = None) -> None:
        """Clear statistics for an operation or all operations."""
        with self._lock:
            if operation:
                self.metrics[operation].clear()
            else:
                self.metrics.clear()
                self.start_times.clear()


class CacheManager:
    """Simple in - memory cache manager with TTL support."""

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[float] = None):
        self.cache: Dict[str, Any] = {}
        self.access_times: Dict[str, float] = {}
        self.expiry_times: Dict[str, float] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        """Get value from cache."""
        with self._lock:
            # Check if expired
            if key in self.expiry_times and time.time() > self.expiry_times[key]:
                self._remove_key(key)
                return None

            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()

            self.cache[key] = value
            self.access_times[key] = time.time()

            # Set expiry time if TTL is configured
            if self.ttl_seconds:
                self.expiry_times[key] = time.time() + self.ttl_seconds

    def _remove_key(self, key: str) -> None:
        """Remove a key from all tracking dictionaries."""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
        self.expiry_times.pop(key, None)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.access_times:
            return

        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.expiry_times.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)


class BackgroundTaskManager:
    """Manage background tasks."""

    def __init__(self):
        self.tasks: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start_task(self, name: str, target: Callable, *args, **kwargs) -> None:
        """Start a background task."""
        with self._lock:
            if name in self.tasks and self.tasks[name].is_alive():
                return  # Task already running

            # Remove interval from kwargs if present (not supported in this basic implementation)
            kwargs.pop("interval", None)

            thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
            thread.start()
            self.tasks[name] = thread

    def is_running(self, name: str) -> bool:
        """Check if a task is running."""
        with self._lock:
            return name in self.tasks and self.tasks[name].is_alive()

    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all tasks."""
        with self._lock:
            status = {}
            for name, thread in self.tasks.items():
                status[name] = {"running": thread.is_alive(), "daemon": thread.daemon}
            return status

    def stop_all(self) -> None:
        """Stop all tasks (note: this doesn't force stop, just removes references)."""
        with self._lock:
            self.tasks.clear()


# Global instances
_performance_monitor = PerformanceMonitor()
_cache_manager = CacheManager()
_background_manager = BackgroundTaskManager()


def monitor_performance(operation: str) -> Callable:
    """Decorator to monitor performance of functions."""

    def decorator(func: Callable) -> Callable:
        """TODO: Add docstring for decorator."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """TODO: Add docstring for wrapper."""
            _performance_monitor.start_timer(operation)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                _performance_monitor.end_timer(operation)

        return wrapper

    return decorator


def cache_result(cache_manager_or_key_func=None, ttl: Optional[float] = None) -> Callable:
    """Decorator to cache function results."""

    def decorator(func: Callable) -> Callable:
        """TODO: Add docstring for decorator."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """TODO: Add docstring for wrapper."""
            # Handle the case where cache_manager is passed
            if hasattr(cache_manager_or_key_func, "get") and hasattr(cache_manager_or_key_func, "set"):
                cache_manager = cache_manager_or_key_func
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            else:
                cache_manager = _cache_manager
                # Use custom key function if provided
                if callable(cache_manager_or_key_func):
                    cache_key = str(cache_manager_or_key_func(*args, **kwargs))
                else:
                    cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Calculate and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            return result

        return wrapper

    return decorator


def batch_process(items: list, batch_size: int = 100, delay: float = 0.0) -> list:
    """Process items in batches to avoid overwhelming resources."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        # For this simple implementation, just yield batches
        # In real use, you'd process each batch
        results.extend(batch)
        if delay > 0 and i + batch_size < len(items):
            time.sleep(delay)
    return results


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    return _performance_monitor


def get_cache_manager() -> CacheManager:
    """Get the global cache manager."""
    return _cache_manager


def get_background_manager() -> BackgroundTaskManager:
    """Get the global background task manager."""
    return _background_manager
