"""
Task Queue Configuration for Eunice Research Platform

This module configures the Redis Queue (RQ) system for handling
asynchronous research tasks.
"""

import os
from typing import Dict, List, Any
import redis
from rq import Queue
from rq.job import Job

# Redis connection configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Redis connection
redis_conn = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Queue definitions
QUEUE_NAMES = {
    'high_priority': 'high',
    'literature': 'literature',
    'analysis': 'analysis', 
    'planning': 'planning',
    'memory': 'memory',
    'default': 'default'
}

# Queue instances
queues: Dict[str, Queue] = {}

def initialize_queues():
    """Initialize all RQ queues."""
    global queues
    
    for queue_name, queue_key in QUEUE_NAMES.items():
        queues[queue_name] = Queue(
            name=queue_key,
            connection=redis_conn,
            default_timeout=1800  # 30 minutes in seconds
        )

def get_queue(queue_name: str = 'default') -> Queue:
    """Get a specific queue instance."""
    if queue_name not in queues:
        queue_name = 'default'
    return queues[queue_name]

def get_all_queues() -> List[Queue]:
    """Get all queue instances."""
    return list(queues.values())

def clear_all_queues():
    """Clear all jobs from all queues (for testing/development)."""
    for queue in queues.values():
        queue.empty()

def get_queue_stats() -> Dict[str, Dict[str, int]]:
    """Get statistics for all queues."""
    stats = {}
    
    for queue_name, queue in queues.items():
        stats[queue_name] = {
            'pending': len(queue),
            'started': queue.started_job_registry.count,
            'finished': queue.finished_job_registry.count,
            'failed': queue.failed_job_registry.count,
            'deferred': queue.deferred_job_registry.count
        }
    
    return stats

def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status of a specific job."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        return {
            'id': job.id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'progress': job.meta.get('progress', 0) if job.meta else 0,
            'result': job.result if job.is_finished else None,
            'error': str(job.exc_info) if job.is_failed else None,
            'queue': job.origin,
            'timeout': job.timeout,
            'description': job.description
        }
    
    except Exception as e:
        return {
            'id': job_id,
            'status': 'not_found',
            'error': f'Job not found: {str(e)}'
        }

# Initialize queues on import
initialize_queues()
