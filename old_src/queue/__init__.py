"""
Task Queue Package for Eunice Research Platform

This package provides asynchronous task processing capabilities
using Redis Queue (RQ) for handling long-running research operations.
"""

from .config import redis_conn, get_queue, get_all_queues, get_queue_stats
from .manager import queue_manager
from .tasks import literature_search_task, research_planning_task, data_analysis_task

__all__ = [
    'redis_conn',
    'get_queue', 
    'get_all_queues',
    'get_queue_stats',
    'queue_manager',
    'literature_search_task',
    'research_planning_task', 
    'data_analysis_task'
]
