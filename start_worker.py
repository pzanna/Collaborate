#!/usr/bin/env python3
"""
RQ Worker Script for Eunice Research Platform

This script starts Redis Queue workers to process asynchronous tasks.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rq import Worker
from old_src.queue.config import redis_conn, get_all_queues
from old_src.queue.tasks import (
    literature_search_task,
    research_planning_task,
    data_analysis_task
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main worker function."""
    logger.info("Starting Eunice RQ Worker...")
    
    # Get queue names from command line args or use all queues
    if len(sys.argv) > 1:
        queue_names = sys.argv[1:]
        from old_src.queue.config import get_queue
        queues = [get_queue(name) for name in queue_names if name in ['high_priority', 'literature', 'analysis', 'planning', 'memory', 'default']]
    else:
        queues = get_all_queues()
    
    if not queues:
        logger.error("No valid queues specified")
        sys.exit(1)
    
    logger.info(f"Worker will process queues: {[q.name for q in queues]}")
    
    # Create worker
    worker = Worker(queues, connection=redis_conn)
    
    # Set worker name
    worker_name = f"eunice-worker-{os.getpid()}"
    worker.name = worker_name
    
    logger.info(f"Starting worker: {worker_name}")
    
    try:
        # Start processing jobs
        worker.work()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
