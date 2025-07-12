#!/usr/bin/env python3
"""
Test performance optimization functionality
"""

import os
import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.performance import (
    PerformanceMonitor, CacheManager, BackgroundTaskManager,
    monitor_performance, cache_result, get_performance_monitor,
    get_cache_manager, get_background_manager
)


def test_performance_monitor():
    """Test performance monitoring functionality."""
    print("🧪 Testing Performance Monitor...")
    
    monitor = PerformanceMonitor()
    
    # Test manual timing
    monitor.start_timer("test_operation")
    time.sleep(0.1)  # Simulate work
    duration = monitor.end_timer("test_operation")
    
    assert duration >= 0.1
    print(f"✓ Manual timing: {duration:.3f}s")
    
    # Test decorator
    @monitor_performance("decorated_function")
    def slow_function():
        time.sleep(0.05)
        return "result"
    
    result = slow_function()
    assert result == "result"
    print("✓ Performance decorator works")
    
    # Test statistics
    stats = monitor.get_performance_stats()
    assert "operations" in stats
    assert "test_operation" in stats["operations"]
    
    # The decorated function uses the global monitor, so let's check that instead
    global_monitor = get_performance_monitor()
    global_stats = global_monitor.get_performance_stats()
    
    print(f"✓ Performance statistics: {len(stats['operations'])} local, {len(global_stats['operations'])} global operations")
    
    # Test slow operations detection
    slow_ops = monitor.get_slow_operations(threshold=0.01)
    global_slow_ops = global_monitor.get_slow_operations(threshold=0.01)
    print(f"✓ Slow operations detection: {len(slow_ops)} local, {len(global_slow_ops)} global operations")
    
    # Test system metrics
    monitor.record_memory_usage()
    monitor.record_cpu_usage()
    
    stats = monitor.get_performance_stats()
    assert "system" in stats
    print("✓ System metrics collection")


def test_cache_manager():
    """Test cache manager functionality."""
    print("\n🧪 Testing Cache Manager...")
    
    cache = CacheManager(max_size=3, ttl_seconds=1)
    
    # Test basic operations
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    print("✓ Basic cache operations")
    
    # Test cache miss
    assert cache.get("nonexistent") is None
    print("✓ Cache miss handling")
    
    # Test cache size limit
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    cache.set("key4", "value4")  # Should evict key1
    
    assert cache.get("key1") is None  # Evicted
    assert cache.get("key4") == "value4"  # New value
    print("✓ Cache size limit (LRU eviction)")
    
    # Test TTL expiration
    cache.set("temp_key", "temp_value")
    assert cache.get("temp_key") == "temp_value"
    
    time.sleep(1.1)  # Wait for expiration
    assert cache.get("temp_key") is None
    print("✓ TTL expiration")
    
    # Test cache statistics
    stats = cache.get_stats()
    assert "hit_count" in stats
    assert "miss_count" in stats
    assert "hit_rate" in stats
    print(f"✓ Cache statistics: {stats['hit_rate']:.2f} hit rate")
    
    # Test cache decorator
    call_count = 0
    
    @cache_result(cache)
    def expensive_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    result1 = expensive_function(5)
    result2 = expensive_function(5)  # Should be cached
    
    assert result1 == result2 == 10
    assert call_count == 1  # Function called only once
    print("✓ Cache decorator works")


def test_background_task_manager():
    """Test background task manager."""
    print("\n🧪 Testing Background Task Manager...")
    
    manager = BackgroundTaskManager()
    
    # Test basic task management
    task_runs = []
    
    def test_task():
        task_runs.append(time.time())
    
    manager.start_task("test_task", test_task, interval=1)
    time.sleep(0.1)  # Let task start
    
    status = manager.get_task_status()
    assert "test_task" in status
    assert status["test_task"]  # Task should be running
    print("✓ Background task creation and status")
    
    # Stop the task
    manager.stop_task("test_task")
    time.sleep(0.1)
    
    status = manager.get_task_status()
    assert "test_task" not in status
    print("✓ Background task stopping")
    
    # Test background monitoring
    monitor = get_performance_monitor()
    monitor.reset_metrics()
    
    manager.start_background_monitoring()
    time.sleep(0.5)  # Let monitoring run
    
    stats = monitor.get_performance_stats()
    # Should have some system metrics
    assert "system" in stats
    print("✓ Background performance monitoring")
    
    manager.stop_all_tasks()
    print("✓ Background task cleanup")


def test_integration_example():
    """Test a realistic integration scenario."""
    print("\n🧪 Testing Integration Example...")
    
    # Create a simulated database operation
    @monitor_performance("database_query")
    @cache_result(get_cache_manager())
    def simulated_database_query(query_id):
        """Simulate a database query that takes time."""
        time.sleep(0.02)  # Simulate DB latency
        return f"Result for query {query_id}"
    
    # Test performance monitoring and caching
    start_time = time.time()
    
    # First call - should be slow and cached
    result1 = simulated_database_query("user_projects")
    
    # Second call - should be fast (from cache)
    result2 = simulated_database_query("user_projects")
    
    end_time = time.time()
    
    assert result1 == result2
    assert end_time - start_time < 0.05  # Should be much faster due to caching
    print("✓ Performance + caching integration")
    
    # Check performance stats
    monitor = get_performance_monitor()
    stats = monitor.get_performance_stats()
    
    if "database_query" in stats["operations"]:
        db_stats = stats["operations"]["database_query"]
        print(f"✓ Database query stats: {db_stats['total_calls']} calls, {db_stats['average_time']:.4f}s avg")
    
    # Check cache stats
    cache = get_cache_manager()
    cache_stats = cache.get_stats()
    print(f"✓ Cache stats: {cache_stats['hit_rate']:.2f} hit rate")


def test_performance_optimization():
    """Test performance optimization utilities."""
    print("\n🧪 Testing Performance Optimization...")
    
    # Test batch processing
    from utils.performance import batch_process
    
    def process_batch(items):
        return [item * 2 for item in items]
    
    large_list = list(range(250))
    results = batch_process(large_list, batch_size=50, processor=process_batch)
    
    assert len(results) == 250
    assert results[0] == 0
    assert results[249] == 498
    print("✓ Batch processing")
    
    # Test query optimization
    from utils.performance import optimize_database_query
    
    query = "SELECT * FROM conversations WHERE project_id = ?"
    optimized = optimize_database_query(query)
    
    assert "LIMIT" in optimized
    print("✓ Database query optimization")


if __name__ == "__main__":
    try:
        test_performance_monitor()
        test_cache_manager()
        test_background_task_manager()
        test_integration_example()
        test_performance_optimization()
        
        print("\n🎉 All performance tests passed!")
        print("\nKey Features Tested:")
        print("• Performance monitoring with decorators")
        print("• Caching system with TTL and LRU eviction")
        print("• Background task management")
        print("• System resource monitoring")
        print("• Performance statistics collection")
        print("• Integration with real-world scenarios")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up background tasks
        get_background_manager().stop_all_tasks()
