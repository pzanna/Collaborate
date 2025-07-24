"""
Performance & Scalability Package
=================================

Enterprise - grade performance optimization and scalability enhancements
for systematic review automation.

This package provides:
- Parallel processing optimization
- Memory management and caching
- Database query optimization
- Resource monitoring and profiling
- Scalable architecture patterns

Author: Eunice AI System
Date: July 2025
"""

from .cache_manager import (
    CacheConfig,
    CacheManager,
    CacheStrategy,
    MemoryCache,
    RedisCache,
)
from .db_optimizer import (
    ConnectionPool,
    DatabaseOptimizer,
    IndexManager,
    QueryOptimizer,
)
from .parallel_processor import (
    ParallelConfig,
    ParallelProcessor,
    ProcessingStrategy,
    TaskBatch,
)
from .resource_monitor import (
    PerformanceProfiler,
    PerformanceReport,
    ResourceMonitor,
    SystemMetrics,
)

__all__ = [
    # Parallel processing
    "ParallelProcessor",
    "TaskBatch",
    "ProcessingStrategy",
    "ParallelConfig",
    # Cache management
    "CacheManager",
    "CacheStrategy",
    "CacheConfig",
    "MemoryCache",
    "RedisCache",
    # Database optimization
    "DatabaseOptimizer",
    "QueryOptimizer",
    "IndexManager",
    "ConnectionPool",
    # Resource monitoring
    "ResourceMonitor",
    "PerformanceProfiler",
    "SystemMetrics",
    "PerformanceReport",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Eunice AI System"
__description__ = "Performance & Scalability for Systematic Review Automation"
