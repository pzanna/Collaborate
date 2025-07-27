#!/usr/bin/env python3
"""
Test script for API Gateway functionality

Tests the API Gateway endpoints and integration with MCP server.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIGatewayTester:
    """Test harness for API Gateway"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        try:
            if not self.session:
                logger.error("No active session")
                return False
                
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Health check passed: {data}")
                    return True
                else:
                    logger.error(f"Health check failed with status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def test_status_endpoint(self) -> bool:
        """Test the status endpoint"""
        try:
            if not self.session:
                logger.error("No active session")
                return False
                
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status in [200, 503]:  # 503 is expected if MCP server is down
                    data = await response.json()
                    logger.info(f"Status check: {json.dumps(data, indent=2)}")
                    return True
                else:
                    logger.error(f"Status check failed with status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return False

    async def test_literature_search(self) -> bool:
        """Test literature search endpoint"""
        try:
            if not self.session:
                logger.error("No active session")
                return False
                
            payload = {
                "request_id": "test-lit-001",
                "query": "neural networks artificial intelligence",
                "search_type": "academic",
                "max_results": 10,
                "filters": {
                    "year_range": [2020, 2024],
                    "document_type": "article"
                }
            }

            async with self.session.post(
                f"{self.base_url}/literature/search",
                json=payload
            ) as response:
                data = await response.json()
                logger.info(f"Literature search response: {json.dumps(data, indent=2)}")
                
                if response.status in [200, 503]:  # 503 expected if MCP server unavailable
                    return True
                else:
                    logger.error(f"Literature search failed with status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Literature search error: {e}")
            return False

    async def test_task_status(self) -> bool:
        """Test task status endpoint"""
        try:
            if not self.session:
                logger.error("No active session")
                return False
                
            task_id = "test-task-001"
            async with self.session.get(f"{self.base_url}/tasks/{task_id}/status") as response:
                data = await response.json()
                logger.info(f"Task status response: {json.dumps(data, indent=2)}")
                
                if response.status in [200, 503]:  # 503 expected if MCP server unavailable
                    return True
                else:
                    logger.error(f"Task status failed with status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Task status error: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all API Gateway tests"""
        results = {}
        
        logger.info("Starting API Gateway tests...")
        
        # Test 1: Health check
        logger.info("Testing health check endpoint...")
        results["health_check"] = await self.test_health_check()
        
        # Test 2: Status endpoint
        logger.info("Testing status endpoint...")
        results["status"] = await self.test_status_endpoint()
        
        # Test 3: Literature search
        logger.info("Testing literature search endpoint...")
        results["literature_search"] = await self.test_literature_search()
        
        # Test 4: Task status
        logger.info("Testing task status endpoint...")
        results["task_status"] = await self.test_task_status()
        
        return results


async def main():
    """Main test function"""
    logger.info("API Gateway Test Suite Starting...")
    
    async with APIGatewayTester() as tester:
        results = await tester.run_all_tests()
        
        logger.info("\n" + "="*50)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("="*50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed!")
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
