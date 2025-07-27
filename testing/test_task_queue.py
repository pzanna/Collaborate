#!/usr/bin/env python3
"""
Task Queue Test Suite for Eunice Research Platform

Tests the Redis Queue (RQ) task processing system including:
- Queue submission and monitoring
- Worker processing
- API Gateway integration
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiohttp
import redis
from old_src.queue.manager import queue_manager
from old_src.queue.config import redis_conn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskQueueTester:
    """Test harness for task queue system"""

    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.api_base_url = api_base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    def test_redis_connection(self) -> bool:
        """Test Redis connection."""
        try:
            response = redis_conn.ping()
            logger.info(f"Redis connection test: {response}")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False

    def test_queue_manager_direct(self) -> bool:
        """Test queue manager directly (without workers)."""
        try:
            # Test literature search submission
            job_id = queue_manager.submit_literature_search(
                query="artificial intelligence neural networks",
                search_type="academic",
                max_results=10
            )
            
            logger.info(f"Submitted literature search job: {job_id}")
            
            # Check job status
            status = queue_manager.get_job_status(job_id)
            logger.info(f"Job status: {json.dumps(status, indent=2)}")
            
            # Test statistics
            stats = queue_manager.get_queue_statistics()
            logger.info(f"Queue statistics: {json.dumps(stats, indent=2)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Queue manager test failed: {e}")
            return False

    async def test_api_gateway_queue_endpoints(self) -> bool:
        """Test API Gateway queue endpoints."""
        try:
            if not self.session:
                logger.error("No active session")
                return False

            # Test literature search via API
            literature_payload = {
                "request_id": "test-queue-lit-001",
                "query": "machine learning research 2024",
                "max_results": 5,
                "include_abstracts": True
            }

            async with self.session.post(
                f"{self.api_base_url}/queue/literature/search",
                json=literature_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Literature search queued: {json.dumps(data, indent=2)}")
                    
                    job_id = data.get('job_id')
                    if job_id:
                        # Check job status via API
                        await asyncio.sleep(2)  # Wait a moment
                        
                        async with self.session.get(f"{self.api_base_url}/queue/jobs/{job_id}") as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                logger.info(f"Job status via API: {json.dumps(status_data, indent=2)}")
                            else:
                                logger.error(f"Failed to get job status: {status_response.status}")
                    
                    return True
                else:
                    logger.error(f"Literature search failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"API Gateway queue test failed: {e}")
            return False

    async def test_queue_statistics_endpoint(self) -> bool:
        """Test queue statistics endpoint."""
        try:
            if not self.session:
                return False

            async with self.session.get(f"{self.api_base_url}/queue/statistics") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Queue statistics: {json.dumps(data, indent=2)}")
                    return True
                else:
                    logger.error(f"Statistics endpoint failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Statistics test failed: {e}")
            return False

    async def test_recent_jobs_endpoint(self) -> bool:
        """Test recent jobs endpoint."""
        try:
            if not self.session:
                return False

            async with self.session.get(f"{self.api_base_url}/queue/jobs?limit=10") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Recent jobs: {json.dumps(data, indent=2)}")
                    return True
                else:
                    logger.error(f"Recent jobs endpoint failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Recent jobs test failed: {e}")
            return False

    def test_queue_cleanup(self) -> bool:
        """Test queue cleanup functionality."""
        try:
            # Clean up old jobs
            cleaned = queue_manager.cleanup_old_jobs(days=0)  # Clean all jobs for testing
            logger.info(f"Cleaned up jobs: {cleaned}")
            return True
            
        except Exception as e:
            logger.error(f"Queue cleanup test failed: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all task queue tests."""
        results = {}
        
        logger.info("Starting Task Queue Test Suite...")
        
        # Test 1: Redis connection
        logger.info("Testing Redis connection...")
        results["redis_connection"] = self.test_redis_connection()
        
        # Test 2: Queue manager direct
        logger.info("Testing queue manager directly...")
        results["queue_manager_direct"] = self.test_queue_manager_direct()
        
        # Test 3: API Gateway queue endpoints
        logger.info("Testing API Gateway queue endpoints...")
        results["api_gateway_queue"] = await self.test_api_gateway_queue_endpoints()
        
        # Test 4: Queue statistics endpoint
        logger.info("Testing queue statistics endpoint...")
        results["queue_statistics"] = await self.test_queue_statistics_endpoint()
        
        # Test 5: Recent jobs endpoint
        logger.info("Testing recent jobs endpoint...")
        results["recent_jobs"] = await self.test_recent_jobs_endpoint()
        
        # Test 6: Queue cleanup
        logger.info("Testing queue cleanup...")
        results["queue_cleanup"] = self.test_queue_cleanup()
        
        return results


async def main():
    """Main test function"""
    logger.info("Task Queue Test Suite Starting...")
    
    async with TaskQueueTester() as tester:
        results = await tester.run_all_tests()
        
        logger.info("\n" + "="*60)
        logger.info("TASK QUEUE TEST RESULTS SUMMARY")
        logger.info("="*60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All task queue tests passed!")
            return 0
        else:
            logger.warning("⚠️  Some tests failed. Check logs above.")
            return 1


if __name__ == "__main__":
    import sys
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        sys.exit(1)
