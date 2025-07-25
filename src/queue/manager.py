"""
Queue Manager for Eunice Research Platform

This module provides a high-level interface for managing
asynchronous tasks using Redis Queue (RQ).
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from rq import Queue
from rq.job import Job
from src.queue.config import (
    get_queue, get_all_queues, get_queue_stats, 
    get_job_status, redis_conn
)
from src.queue.tasks import (
    literature_search_task,
    research_planning_task, 
    data_analysis_task
)

logger = logging.getLogger(__name__)

class QueueManager:
    """High-level interface for task queue management."""
    
    def __init__(self):
        """Initialize the queue manager."""
        self.redis_conn = redis_conn
    
    def submit_literature_search(self, query: str, search_type: str = "academic",
                                max_results: int = 20, filters: Optional[Dict[str, Any]] = None,
                                priority: str = "normal") -> str:
        """
        Submit a literature search task to the queue.
        
        Args:
            query: Search query string
            search_type: Type of search (academic, patents, etc.)
            max_results: Maximum number of results
            filters: Additional search filters
            priority: Task priority (high, normal, low)
        
        Returns:
            Job ID for tracking the task
        """
        queue_name = 'high_priority' if priority == 'high' else 'literature'
        queue = get_queue(queue_name)
        
        job = queue.enqueue(
            literature_search_task,
            query=query,
            search_type=search_type,
            max_results=max_results,
            filters=filters,
            job_timeout='30m',
            description=f"Literature search: {query[:50]}..."
        )
        
        logger.info(f"Submitted literature search job {job.id}: {query}")
        return job.id
    
    def submit_research_planning(self, research_question: str, context: str = "",
                               requirements: Optional[Dict[str, Any]] = None,
                               priority: str = "normal") -> str:
        """
        Submit a research planning task to the queue.
        
        Args:
            research_question: The main research question
            context: Additional context information
            requirements: Specific requirements or constraints
            priority: Task priority (high, normal, low)
        
        Returns:
            Job ID for tracking the task
        """
        queue_name = 'high_priority' if priority == 'high' else 'planning'
        queue = get_queue(queue_name)
        
        job = queue.enqueue(
            research_planning_task,
            research_question=research_question,
            context=context,
            requirements=requirements,
            job_timeout='45m',
            description=f"Research planning: {research_question[:50]}..."
        )
        
        logger.info(f"Submitted research planning job {job.id}: {research_question}")
        return job.id
    
    def submit_data_analysis(self, dataset: str, analysis_type: str,
                           parameters: Optional[Dict[str, Any]] = None,
                           priority: str = "normal") -> str:
        """
        Submit a data analysis task to the queue.
        
        Args:
            dataset: Dataset identifier or path
            analysis_type: Type of analysis to perform
            parameters: Analysis parameters
            priority: Task priority (high, normal, low)
        
        Returns:
            Job ID for tracking the task
        """
        queue_name = 'high_priority' if priority == 'high' else 'analysis'
        queue = get_queue(queue_name)
        
        job = queue.enqueue(
            data_analysis_task,
            dataset=dataset,
            analysis_type=analysis_type,
            parameters=parameters,
            job_timeout='60m',
            description=f"Data analysis: {analysis_type} on {dataset}"
        )
        
        logger.info(f"Submitted data analysis job {job.id}: {analysis_type}")
        return job.id
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a specific job."""
        return get_job_status(job_id)
    
    def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get the result of a completed job."""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return job.result if job.is_finished else None
        except Exception as e:
            logger.error(f"Error fetching job result {job_id}: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job if it's still pending."""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            if job.get_status() in ['queued', 'started']:
                job.cancel()
                logger.info(f"Cancelled job {job_id}")
                return True
            else:
                logger.warning(f"Cannot cancel job {job_id} with status {job.get_status()}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        stats = get_queue_stats()
        
        # Add worker information  
        from rq import Worker
        workers = Worker.all(connection=self.redis_conn)
        worker_info = []
        
        for worker in workers:
            worker_info.append({
                'name': worker.name,
                'state': worker.state,
                'queues': [q.name for q in worker.queues],
                'current_job': worker.get_current_job_id(),
                'birth_date': worker.birth_date.isoformat() if worker.birth_date else None,
                'last_heartbeat': worker.last_heartbeat.isoformat() if worker.last_heartbeat else None
            })
        
        return {
            'queues': stats,
            'workers': worker_info,
            'redis_info': {
                'connected': self._check_redis_connection(),
                'memory_usage': self._get_redis_memory_usage()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get information about recent jobs across all queues."""
        recent_jobs = []
        
        for queue in get_all_queues():
            # Get jobs from different registries
            registries = [
                ('finished', queue.finished_job_registry),
                ('failed', queue.failed_job_registry),
                ('started', queue.started_job_registry),
                ('deferred', queue.deferred_job_registry)
            ]
            
            for registry_name, registry in registries:
                job_ids = registry.get_job_ids()[:limit//4]  # Distribute across registries
                
                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self.redis_conn)
                        recent_jobs.append({
                            'id': job.id,
                            'status': job.get_status(),
                            'description': job.description,
                            'queue': job.origin,
                            'created_at': job.created_at.isoformat() if job.created_at else None,
                            'started_at': job.started_at.isoformat() if job.started_at else None,
                            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                            'registry': registry_name
                        })
                    except Exception as e:
                        logger.warning(f"Could not fetch job {job_id}: {e}")
        
        # Sort by creation time, most recent first
        recent_jobs.sort(
            key=lambda x: x['created_at'] or '1970-01-01T00:00:00',
            reverse=True
        )
        
        return recent_jobs[:limit]
    
    def cleanup_old_jobs(self, days: int = 7) -> Dict[str, int]:
        """Clean up jobs older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cleaned = {'finished': 0, 'failed': 0}
        
        for queue in get_all_queues():
            # Clean finished jobs
            finished_jobs = queue.finished_job_registry.get_job_ids()
            for job_id in finished_jobs:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    if job.ended_at and job.ended_at < cutoff_date:
                        job.delete()
                        cleaned['finished'] += 1
                except Exception:
                    pass
            
            # Clean failed jobs
            failed_jobs = queue.failed_job_registry.get_job_ids()
            for job_id in failed_jobs:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    if job.ended_at and job.ended_at < cutoff_date:
                        job.delete()
                        cleaned['failed'] += 1
                except Exception:
                    pass
        
        logger.info(f"Cleaned up {cleaned['finished']} finished and {cleaned['failed']} failed jobs")
        return cleaned
    
    def _check_redis_connection(self) -> bool:
        """Check if Redis connection is working."""
        try:
            self.redis_conn.ping()
            return True
        except Exception:
            return False
    
    def _get_redis_memory_usage(self) -> Optional[str]:
        """Get Redis memory usage information."""
        try:
            info = self.redis_conn.info('memory')
            if isinstance(info, dict):
                return info.get('used_memory_human', 'Unknown')
            return 'Unknown'
        except Exception:
            return None

# Global queue manager instance
queue_manager = QueueManager()
