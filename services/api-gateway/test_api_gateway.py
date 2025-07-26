#!/usr/bin/env python3
"""
Test Client for Containerized API Gateway

Validates that the containerized API Gateway is working correctly
and can communicate with the MCP server.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIGatewayTester:
    """Test harness for the containerized API Gateway"""

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
            logger.info("🏥 Testing health check endpoint...")
            
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Health check passed: {data.get('status', 'unknown')}")
                    
                    # Check dependencies
                    dependencies = data.get('dependencies', {})
                    for dep, status in dependencies.items():
                        icon = "✅" if status in ["connected", "healthy"] else "❌"
                        logger.info(f"   {icon} {dep}: {status}")
                    
                    return data.get('status') in ['healthy', 'degraded']
                else:
                    logger.error(f"❌ Health check failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return False

    async def test_status_endpoint(self) -> bool:
        """Test the status endpoint"""
        try:
            logger.info("📊 Testing status endpoint...")
            
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Status endpoint working")
                    logger.info(f"   Service: {data.get('service', 'unknown')}")
                    logger.info(f"   Version: {data.get('version', 'unknown')}")
                    logger.info(f"   Active requests: {data.get('active_requests', 0)}")
                    return True
                else:
                    logger.error(f"❌ Status endpoint failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Status endpoint error: {e}")
            return False

    async def test_literature_search(self) -> bool:
        """Test literature search endpoint"""
        try:
            logger.info("📚 Testing literature search endpoint...")
            
            search_request = {
                "query": "neural networks attention mechanisms",
                "max_results": 10,
                "include_abstracts": True,
                "date_range": {
                    "start": "2020-01-01",
                    "end": "2024-12-31"
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/literature/search",
                json=search_request
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Literature search request accepted")
                    logger.info(f"   Request ID: {data.get('request_id', 'unknown')}")
                    logger.info(f"   Success: {data.get('success', False)}")
                    
                    if data.get('success'):
                        task_data = data.get('data', {})
                        logger.info(f"   Task ID: {task_data.get('task_id', 'unknown')}")
                        logger.info(f"   Status: {task_data.get('status', 'unknown')}")
                    
                    return data.get('success', False)
                else:
                    logger.error(f"❌ Literature search failed with status {response.status}")
                    text = await response.text()
                    logger.error(f"   Response: {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Literature search error: {e}")
            return False

    async def test_research_task_submission(self) -> bool:
        """Test research task submission endpoint"""
        try:
            logger.info("🔬 Testing research task submission...")
            
            task_request = {
                "agent_type": "planning",
                "action": "create_research_plan",
                "payload": {
                    "research_question": "How do attention mechanisms improve neural network performance?",
                    "domain": "machine learning",
                    "requirements": ["literature review", "methodology", "evaluation metrics"]
                },
                "priority": "normal",
                "timeout": 300
            }
            
            async with self.session.post(
                f"{self.base_url}/research/tasks",
                json=task_request
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Research task request accepted")
                    logger.info(f"   Request ID: {data.get('request_id', 'unknown')}")
                    logger.info(f"   Success: {data.get('success', False)}")
                    
                    if data.get('success'):
                        task_data = data.get('data', {})
                        logger.info(f"   Task ID: {task_data.get('task_id', 'unknown')}")
                        logger.info(f"   Status: {task_data.get('status', 'unknown')}")
                    
                    return data.get('success', False)
                else:
                    logger.error(f"❌ Research task submission failed with status {response.status}")
                    text = await response.text()
                    logger.error(f"   Response: {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Research task submission error: {e}")
            return False

    async def test_task_status_query(self, task_id: str = "test-task-123") -> bool:
        """Test task status query endpoint"""
        try:
            logger.info(f"📋 Testing task status query for task: {task_id}")
            
            async with self.session.get(f"{self.base_url}/tasks/{task_id}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Task status query successful")
                    logger.info(f"   Task ID: {data.get('request_id', 'unknown')}")
                    logger.info(f"   Success: {data.get('success', False)}")
                    
                    if data.get('success'):
                        task_data = data.get('data', {})
                        logger.info(f"   Status: {task_data.get('status', 'unknown')}")
                    else:
                        logger.info(f"   Error: {data.get('error', 'unknown')}")
                    
                    return True  # Even if task not found, the endpoint works
                elif response.status == 404:
                    logger.info(f"✅ Task status query working (task not found is expected)")
                    return True
                else:
                    logger.error(f"❌ Task status query failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Task status query error: {e}")
            return False

    async def test_metrics_endpoint(self) -> bool:
        """Test metrics endpoint"""
        try:
            logger.info("📈 Testing metrics endpoint...")
            
            async with self.session.get(f"{self.base_url}/metrics") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Metrics endpoint working")
                    logger.info(f"   Active requests: {data.get('active_requests', 0)}")
                    logger.info(f"   MCP connected: {data.get('mcp_connected', False)}")
                    logger.info(f"   Service: {data.get('service', 'unknown')}")
                    logger.info(f"   Version: {data.get('version', 'unknown')}")
                    return True
                else:
                    logger.error(f"❌ Metrics endpoint failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Metrics endpoint error: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all API Gateway tests"""
        logger.info("🚀 Starting API Gateway test suite...")
        
        test_results = {}
        
        # Basic connectivity tests
        test_results["health_check"] = await self.test_health_check()
        test_results["status_endpoint"] = await self.test_status_endpoint()
        test_results["metrics_endpoint"] = await self.test_metrics_endpoint()
        
        # API functionality tests
        test_results["literature_search"] = await self.test_literature_search()
        test_results["research_task_submission"] = await self.test_research_task_submission()
        test_results["task_status_query"] = await self.test_task_status_query()
        
        # Summary
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        logger.info(f"\n📊 Test Results Summary:")
        logger.info(f"   Passed: {passed_tests}/{total_tests}")
        
        for test_name, result in test_results.items():
            icon = "✅" if result else "❌"
            logger.info(f"   {icon} {test_name}")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! API Gateway is working correctly.")
        else:
            logger.warning(f"⚠️  {total_tests - passed_tests} test(s) failed.")
        
        return test_results


async def main():
    """Main test function"""
    try:
        async with APIGatewayTester() as tester:
            results = await tester.run_all_tests()
            
            # Return appropriate exit code
            if all(results.values()):
                return 0
            else:
                return 1
                
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        sys.exit(1)
