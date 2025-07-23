#!/usr/bin/env python3
"""
RetrieverAgent Integration Test for Eunice Application

This test verifies that the RetrieverAgent works properly within the Eunice 
application framework, using the real search functionality we implemented.

The test will:
1. Initialize the RetrieverAgent with ConfigManager
2. Test search functionality with various queries
3. Test content extraction from web pages
4. Verify error handling and edge cases
5. Compare performance with the standalone version
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.retriever_agent import RetrieverAgent
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction


class RetrieverAgentTester:
    """Test suite for RetrieverAgent integration within Eunice."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.setup_logging()
        self.config_manager = None
        self.retriever_agent = None
        self.test_results = []
        
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('retriever_integration_test.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def initialize_components(self) -> bool:
        """Initialize ConfigManager and RetrieverAgent."""
        try:
            self.logger.info("Initializing ConfigManager...")
            
            # Initialize config manager
            self.config_manager = ConfigManager()
            
            self.logger.info("Initializing RetrieverAgent...")
            
            # Initialize retriever agent
            self.retriever_agent = RetrieverAgent(self.config_manager)
            await self.retriever_agent.initialize()
            
            self.logger.info("✅ Components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Component initialization failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        if self.retriever_agent:
            await self.retriever_agent.stop()
        self.logger.info("Cleanup completed")
    
    async def run_test(self, test_name: str, test_func, *args, **kwargs) -> Dict[str, Any]:
        """Run a single test and record results."""
        start_time = time.time()
        
        try:
            self.logger.info(f"🧪 Running test: {test_name}")
            result = await test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            test_result = {
                'test_name': test_name,
                'success': True,
                'result': result,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Test '{test_name}' passed ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            
            test_result = {
                'test_name': test_name,
                'success': False,
                'error': str(e),
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.error(f"❌ Test '{test_name}' failed: {e}")
        
        self.test_results.append(test_result)
        return test_result
    
    async def test_search_information(self) -> Dict[str, Any]:
        """Test the search_information functionality."""
        test_queries = [
            "Python machine learning tutorial",
            "artificial intelligence research 2025",
            "web development best practices",
            "database design principles"
        ]
        
        all_results = []
        
        for i, query in enumerate(test_queries):
            action = ResearchAction(
                task_id=f"test_search_{i}",
                context_id="test_context",
                agent_type="Retriever",
                action="search_information",
                payload={
                    "query": query,
                    "max_results": 5,
                    "search_engines": ["google", "bing", "yahoo"]
                }
            )
            
            response = await self.retriever_agent.process_task(action)
            
            # Check if response was successful
            assert response.status == "completed", f"Task failed: {response.error}"
            assert response.result is not None, "No result in response"
            
            result = response.result
            
            # Validate result structure
            assert "query" in result
            assert "results" in result
            assert "total_found" in result
            assert "search_engines_used" in result
            
            # Check that we got some results
            results = result["results"]
            assert len(results) > 0, f"No results found for query: {query}"
            
            # Validate result structure
            for search_result in results:
                assert "title" in search_result
                assert "url" in search_result
                assert "content" in search_result
                assert "source" in search_result
                assert "type" in search_result
            
            all_results.append({
                "query": query,
                "result_count": len(results),
                "sources": list(set(r["source"] for r in results)),
                "types": list(set(r["type"] for r in results))
            })
            
            self.logger.info(f"Query '{query}': {len(results)} results from {result['search_engines_used']}")
        
        return {
            "queries_tested": len(test_queries),
            "results": all_results,
            "total_results": sum(r["result_count"] for r in all_results)
        }
    
    async def test_extract_web_content(self) -> Dict[str, Any]:
        """Test web content extraction."""
        test_urls = [
            "https://www.python.org/",
            "https://github.com/",
            "https://stackoverflow.com/",
            "https://www.wikipedia.org/"
        ]
        
        extraction_results = []
        
        for i, url in enumerate(test_urls):
            try:
                action = ResearchAction(
                    task_id=f"test_extract_{i}",
                    context_id="test_context",
                    agent_type="Retriever",
                    action="extract_web_content",
                    payload={"url": url}
                )
                
                response = await self.retriever_agent.process_task(action)
                
                # Check if response was successful
                assert response.status == "completed", f"Task failed: {response.error}"
                assert response.result is not None, "No result in response"
                
                result = response.result
                
                # Validate result structure
                assert "url" in result
                assert "title" in result
                assert "content" in result
                assert "metadata" in result
                assert "extracted_at" in result
                
                # Check content quality
                assert len(result["content"]) > 100, f"Content too short for {url}"
                assert len(result["title"]) > 0, f"No title extracted for {url}"
                
                extraction_results.append({
                    "url": url,
                    "success": True,
                    "title_length": len(result["title"]),
                    "content_length": len(result["content"]),
                    "metadata_count": len(result["metadata"])
                })
                
                self.logger.info(f"Extracted content from {url}: {len(result['content'])} chars")
                
            except Exception as e:
                extraction_results.append({
                    "url": url,
                    "success": False,
                    "error": str(e)
                })
                self.logger.warning(f"Failed to extract content from {url}: {e}")
        
        successful_extractions = [r for r in extraction_results if r.get("success", False)]
        
        return {
            "urls_tested": len(test_urls),
            "successful_extractions": len(successful_extractions),
            "extraction_results": extraction_results,
            "success_rate": len(successful_extractions) / len(test_urls) * 100
        }
    
    async def test_academic_search(self) -> Dict[str, Any]:
        """Test academic paper search functionality."""
        action = ResearchAction(
            task_id="test_academic",
            context_id="test_context",
            agent_type="Retriever",
            action="search_academic_papers",
            payload={
                "query": "neural networks deep learning",
                "max_results": 5
            }
        )
        
        response = await self.retriever_agent.process_task(action)
        
        # Check if response was successful
        assert response.status == "completed", f"Task failed: {response.error}"
        assert response.result is not None, "No result in response"
        
        result = response.result
        
        # Validate result structure
        assert "query" in result
        assert "results" in result
        assert "total_found" in result
        assert "search_type" in result
        
        academic_results = result["results"]
        
        # Check result quality
        for academic_result in academic_results:
            assert "title" in academic_result
            assert "source" in academic_result
            assert academic_result["source"] == "google_scholar"
            assert academic_result.get("type") == "academic_paper"
        
        return {
            "query": result["query"],
            "academic_results_found": len(academic_results),
            "search_type": result["search_type"]
        }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling for various edge cases."""
        error_tests = []
        
        # Test 1: Invalid URL content extraction
        try:
            action = ResearchAction(
                task_id="test_error_1",
                context_id="test_context",
                agent_type="Retriever",
                action="extract_web_content",
                payload={"url": "invalid://not-a-real-url"}
            )
            response = await self.retriever_agent.process_task(action)
            # If we get here without exception, check if it properly failed
            error_tests.append({"test": "invalid_url", "handled": response.status == "failed"})
        except Exception:
            error_tests.append({"test": "invalid_url", "handled": True})
        
        # Test 2: Empty search query
        try:
            action = ResearchAction(
                task_id="test_error_2",
                context_id="test_context",
                agent_type="Retriever",
                action="search_information",
                payload={"query": "", "max_results": 5}
            )
            response = await self.retriever_agent.process_task(action)
            error_tests.append({"test": "empty_query", "handled": response.status == "failed"})
        except Exception:
            error_tests.append({"test": "empty_query", "handled": True})
        
        # Test 3: Unknown action
        try:
            action = ResearchAction(
                task_id="test_error_3",
                context_id="test_context",
                agent_type="Retriever",
                action="unknown_action",
                payload={"test": "data"}
            )
            response = await self.retriever_agent.process_task(action)
            error_tests.append({"test": "unknown_action", "handled": response.status == "failed"})
        except Exception:
            error_tests.append({"test": "unknown_action", "handled": True})
        
        properly_handled = [t for t in error_tests if t["handled"]]
        
        return {
            "total_error_tests": len(error_tests),
            "properly_handled": len(properly_handled),
            "error_handling_rate": len(properly_handled) / len(error_tests) * 100,
            "test_details": error_tests
        }
    
    async def test_multiple_search_engines(self) -> Dict[str, Any]:
        """Test search with multiple engines and compare results."""
        query = "Python web frameworks comparison"
        
        # Test individual engines
        engine_results = {}
        
        for i, engine in enumerate(["google", "bing", "yahoo"]):
            try:
                action = ResearchAction(
                    task_id=f"test_engine_{i}",
                    context_id="test_context",
                    agent_type="Retriever",
                    action="search_information",
                    payload={
                        "query": query,
                        "max_results": 3,
                        "search_engines": [engine]
                    }
                )
                
                response = await self.retriever_agent.process_task(action)
                
                if response.status == "completed" and response.result:
                    result = response.result
                    engine_results[engine] = {
                        "success": True,
                        "result_count": len(result["results"]),
                        "sources": [r["source"] for r in result["results"]]
                    }
                else:
                    engine_results[engine] = {
                        "success": False,
                        "error": response.error or "Unknown error"
                    }
                
            except Exception as e:
                engine_results[engine] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Test combined engines
        action = ResearchAction(
            task_id="test_combined",
            context_id="test_context",
            agent_type="Retriever",
            action="search_information",
            payload={
                "query": query,
                "max_results": 9,
                "search_engines": ["google", "bing", "yahoo"]
            }
        )
        
        response = await self.retriever_agent.process_task(action)
        
        if response.status == "completed" and response.result:
            combined_result = response.result
            combined_data = {
                "total_results": len(combined_result["results"]),
                "engines_used": combined_result["search_engines_used"],
                "unique_sources": list(set(r["source"] for r in combined_result["results"]))
            }
        else:
            combined_data = {
                "error": response.error or "Unknown error"
            }
        
        return {
            "query": query,
            "individual_engines": engine_results,
            "combined_results": combined_data
        }
    
    async def run_all_tests(self):
        """Run all tests and generate report."""
        self.logger.info("🚀 Starting RetrieverAgent Integration Tests")
        self.logger.info("=" * 60)
        
        # Initialize components
        if not await self.initialize_components():
            self.logger.error("Failed to initialize components. Aborting tests.")
            return
        
        try:
            # Run all tests
            await self.run_test("Search Information", self.test_search_information)
            await self.run_test("Extract Web Content", self.test_extract_web_content)
            await self.run_test("Academic Search", self.test_academic_search)
            await self.run_test("Error Handling", self.test_error_handling)
            await self.run_test("Multiple Search Engines", self.test_multiple_search_engines)
            
        finally:
            await self.cleanup()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report."""
        successful_tests = [t for t in self.test_results if t["success"]]
        failed_tests = [t for t in self.test_results if not t["success"]]
        
        total_duration = sum(t["duration"] for t in self.test_results)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("RETRIEVERAGENT INTEGRATION TEST REPORT")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Tests: {len(self.test_results)}")
        self.logger.info(f"Successful: {len(successful_tests)}")
        self.logger.info(f"Failed: {len(failed_tests)}")
        self.logger.info(f"Success Rate: {len(successful_tests) / len(self.test_results) * 100:.1f}%")
        self.logger.info(f"Total Duration: {total_duration:.2f}s")
        self.logger.info(f"Average Test Duration: {total_duration / len(self.test_results):.2f}s")
        
        self.logger.info("\n" + "-" * 40)
        self.logger.info("DETAILED RESULTS")
        self.logger.info("-" * 40)
        
        for test in self.test_results:
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            self.logger.info(f"{status} {test['test_name']} ({test['duration']:.2f}s)")
            
            if not test["success"]:
                self.logger.info(f"    Error: {test['error']}")
            elif test.get("result"):
                # Show key metrics from test results
                result = test["result"]
                if "queries_tested" in result:
                    self.logger.info(f"    Queries tested: {result['queries_tested']}")
                    self.logger.info(f"    Total results: {result['total_results']}")
                elif "urls_tested" in result:
                    self.logger.info(f"    URLs tested: {result['urls_tested']}")
                    self.logger.info(f"    Success rate: {result['success_rate']:.1f}%")
                elif "total_error_tests" in result:
                    self.logger.info(f"    Error handling rate: {result['error_handling_rate']:.1f}%")
        
        # Save detailed results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"retriever_integration_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        self.logger.info(f"\n📄 Detailed results saved to: {results_file}")
        self.logger.info("=" * 60)


async def main():
    """Main test execution function."""
    tester = RetrieverAgentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("RetrieverAgent Integration Test for Eunice Application")
    print("=" * 60)
    print("Testing RetrieverAgent functionality within the Eunice framework...")
    print("This will test real search engines with actual result extraction.")
    print("")
    
    asyncio.run(main())

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.retriever_agent import RetrieverAgent
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction


class RetrieverAgentTester:
    """Test suite for RetrieverAgent integration within Eunice."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.setup_logging()
        self.config_manager = None
        self.retriever_agent = None
        self.test_results = []
        
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('retriever_integration_test.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def initialize_components(self) -> bool:
        """Initialize ConfigManager and RetrieverAgent."""
        try:
            self.logger.info("Initializing ConfigManager...")
            
            # Initialize config manager
            self.config_manager = ConfigManager()
            
            self.logger.info("Initializing RetrieverAgent...")
            
            # Initialize retriever agent
            self.retriever_agent = RetrieverAgent(self.config_manager)
            await self.retriever_agent.initialize()
            
            self.logger.info("✅ Components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Component initialization failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        if self.retriever_agent:
            await self.retriever_agent.stop()
        self.logger.info("Cleanup completed")
    
    async def run_test(self, test_name: str, test_func, *args, **kwargs) -> Dict[str, Any]:
        """Run a single test and record results."""
        start_time = time.time()
        
        try:
            self.logger.info(f"🧪 Running test: {test_name}")
            result = await test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            test_result = {
                'test_name': test_name,
                'success': True,
                'result': result,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Test '{test_name}' passed ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            
            test_result = {
                'test_name': test_name,
                'success': False,
                'error': str(e),
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.error(f"❌ Test '{test_name}' failed: {e}")
        
        self.test_results.append(test_result)
        return test_result
    
    async def test_search_information(self) -> Dict[str, Any]:
        """Test the search_information functionality."""
        test_queries = [
            "Python machine learning tutorial",
            "artificial intelligence research 2025",
            "web development best practices",
            "database design principles"
        ]
        
        all_results = []
        
        for query in test_queries:
            action = ResearchAction(
                task_id=f"test_search_{len(all_results)}",
                context_id="test_context",
                agent_type="Retriever",
                action="search_information",
                payload={
                    "query": query,
                    "max_results": 5,
                    "search_engines": ["google", "bing", "yahoo"]
                }
            )
            
            response = await self.retriever_agent.process_task(action)
            result = response.result
            
            # Validate result structure
            assert "query" in result
            assert "results" in result
            assert "total_found" in result
            assert "search_engines_used" in result
            
            # Check that we got some results
            results = result["results"]
            assert len(results) > 0, f"No results found for query: {query}"
            
            # Validate result structure
            for search_result in results:
                assert "title" in search_result
                assert "url" in search_result
                assert "content" in search_result
                assert "source" in search_result
                assert "type" in search_result
            
            all_results.append({
                "query": query,
                "result_count": len(results),
                "sources": list(set(r["source"] for r in results)),
                "types": list(set(r["type"] for r in results))
            })
            
            self.logger.info(f"Query '{query}': {len(results)} results from {result['search_engines_used']}")
        
        return {
            "queries_tested": len(test_queries),
            "results": all_results,
            "total_results": sum(r["result_count"] for r in all_results)
        }
    
    async def test_extract_web_content(self) -> Dict[str, Any]:
        """Test web content extraction."""
        test_urls = [
            "https://www.python.org/",
            "https://github.com/",
            "https://stackoverflow.com/",
            "https://www.wikipedia.org/"
        ]
        
        extraction_results = []
        
        for i, url in enumerate(test_urls):
            try:
                action = ResearchAction(
                    task_id=f"test_extract_{i}",
                    context_id="test_context",
                    agent_type="Retriever",
                    action="extract_web_content",
                    payload={"url": url}
                )
                
                response = await self.retriever_agent.process_task(action)
                
                # Check if response was successful
                assert response.status == "completed", f"Task failed: {response.error}"
                assert response.result is not None, "No result in response"
                
                result = response.result
                
                # Validate result structure
                assert "url" in result
                assert "title" in result
                assert "content" in result
                assert "metadata" in result
                assert "extracted_at" in result
                
                # Check content quality
                assert len(result["content"]) > 100, f"Content too short for {url}"
                assert len(result["title"]) > 0, f"No title extracted for {url}"
                
                extraction_results.append({
                    "url": url,
                    "success": True,
                    "title_length": len(result["title"]),
                    "content_length": len(result["content"]),
                    "metadata_count": len(result["metadata"])
                })
                
                self.logger.info(f"Extracted content from {url}: {len(result['content'])} chars")
                
            except Exception as e:
                extraction_results.append({
                    "url": url,
                    "success": False,
                    "error": str(e)
                })
                self.logger.warning(f"Failed to extract content from {url}: {e}")
        
        successful_extractions = [r for r in extraction_results if r.get("success", False)]
        
        return {
            "urls_tested": len(test_urls),
            "successful_extractions": len(successful_extractions),
            "extraction_results": extraction_results,
            "success_rate": len(successful_extractions) / len(test_urls) * 100
        }
    
    async def test_academic_search(self) -> Dict[str, Any]:
        """Test academic paper search functionality."""
        action = ResearchAction(
            task_id="test_academic",
            context_id="test_context",
            agent_type="Retriever",
            action="search_academic_papers",
            payload={
                "query": "neural networks deep learning",
                "max_results": 5
            }
        )
        
        response = await self.retriever_agent.process_task(action)
        
        # Check if response was successful
        assert response.status == "completed", f"Task failed: {response.error}"
        assert response.result is not None, "No result in response"
        
        result = response.result
        
        # Validate result structure
        assert "query" in result
        assert "results" in result
        assert "total_found" in result
        assert "search_type" in result
        
        academic_results = result["results"]
        
        # Check result quality
        for academic_result in academic_results:
            assert "title" in academic_result
            assert "source" in academic_result
            assert academic_result["source"] == "google_scholar"
            assert academic_result.get("type") == "academic_paper"
        
        return {
            "query": result["query"],
            "academic_results_found": len(academic_results),
            "search_type": result["search_type"]
        }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling for various edge cases."""
        error_tests = []
        
        # Test 1: Invalid URL content extraction
        try:
            action = ResearchAction(
                action="extract_web_content",
                payload={"url": "invalid://not-a-real-url"}
            )
            await self.retriever_agent.process_task(action)
            error_tests.append({"test": "invalid_url", "handled": False})
        except Exception:
            error_tests.append({"test": "invalid_url", "handled": True})
        
        # Test 2: Empty search query
        try:
            action = ResearchAction(
                action="search_information",
                payload={"query": "", "max_results": 5}
            )
            await self.retriever_agent.process_task(action)
            error_tests.append({"test": "empty_query", "handled": False})
        except Exception:
            error_tests.append({"test": "empty_query", "handled": True})
        
        # Test 3: Unknown action
        try:
            action = ResearchAction(
                action="unknown_action",
                payload={"test": "data"}
            )
            await self.retriever_agent.process_task(action)
            error_tests.append({"test": "unknown_action", "handled": False})
        except Exception:
            error_tests.append({"test": "unknown_action", "handled": True})
        
        properly_handled = [t for t in error_tests if t["handled"]]
        
        return {
            "total_error_tests": len(error_tests),
            "properly_handled": len(properly_handled),
            "error_handling_rate": len(properly_handled) / len(error_tests) * 100,
            "test_details": error_tests
        }
    
    async def test_multiple_search_engines(self) -> Dict[str, Any]:
        """Test search with multiple engines and compare results."""
        query = "Python web frameworks comparison"
        
        # Test individual engines
        engine_results = {}
        
        for engine in ["google", "bing", "yahoo"]:
            try:
                action = ResearchAction(
                    action="search_information",
                    payload={
                        "query": query,
                        "max_results": 3,
                        "search_engines": [engine]
                    }
                )
                
                result = await self.retriever_agent.process_task(action)
                engine_results[engine] = {
                    "success": True,
                    "result_count": len(result["results"]),
                    "sources": [r["source"] for r in result["results"]]
                }
                
            except Exception as e:
                engine_results[engine] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Test combined engines
        action = ResearchAction(
            action="search_information",
            payload={
                "query": query,
                "max_results": 9,
                "search_engines": ["google", "bing", "yahoo"]
            }
        )
        
        combined_result = await self.retriever_agent.process_task(action)
        
        return {
            "query": query,
            "individual_engines": engine_results,
            "combined_results": {
                "total_results": len(combined_result["results"]),
                "engines_used": combined_result["search_engines_used"],
                "unique_sources": list(set(r["source"] for r in combined_result["results"]))
            }
        }
    
    async def run_all_tests(self):
        """Run all tests and generate report."""
        self.logger.info("🚀 Starting RetrieverAgent Integration Tests")
        self.logger.info("=" * 60)
        
        # Initialize components
        if not await self.initialize_components():
            self.logger.error("Failed to initialize components. Aborting tests.")
            return
        
        try:
            # Run all tests
            await self.run_test("Search Information", self.test_search_information)
            await self.run_test("Extract Web Content", self.test_extract_web_content)
            await self.run_test("Academic Search", self.test_academic_search)
            await self.run_test("Error Handling", self.test_error_handling)
            await self.run_test("Multiple Search Engines", self.test_multiple_search_engines)
            
        finally:
            await self.cleanup()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report."""
        successful_tests = [t for t in self.test_results if t["success"]]
        failed_tests = [t for t in self.test_results if not t["success"]]
        
        total_duration = sum(t["duration"] for t in self.test_results)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("RETRIEVERAGENT INTEGRATION TEST REPORT")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Tests: {len(self.test_results)}")
        self.logger.info(f"Successful: {len(successful_tests)}")
        self.logger.info(f"Failed: {len(failed_tests)}")
        self.logger.info(f"Success Rate: {len(successful_tests) / len(self.test_results) * 100:.1f}%")
        self.logger.info(f"Total Duration: {total_duration:.2f}s")
        self.logger.info(f"Average Test Duration: {total_duration / len(self.test_results):.2f}s")
        
        self.logger.info("\n" + "-" * 40)
        self.logger.info("DETAILED RESULTS")
        self.logger.info("-" * 40)
        
        for test in self.test_results:
            status = "✅ PASS" if test["success"] else "❌ FAIL"
            self.logger.info(f"{status} {test['test_name']} ({test['duration']:.2f}s)")
            
            if not test["success"]:
                self.logger.info(f"    Error: {test['error']}")
            elif test.get("result"):
                # Show key metrics from test results
                result = test["result"]
                if "queries_tested" in result:
                    self.logger.info(f"    Queries tested: {result['queries_tested']}")
                    self.logger.info(f"    Total results: {result['total_results']}")
                elif "urls_tested" in result:
                    self.logger.info(f"    URLs tested: {result['urls_tested']}")
                    self.logger.info(f"    Success rate: {result['success_rate']:.1f}%")
                elif "total_error_tests" in result:
                    self.logger.info(f"    Error handling rate: {result['error_handling_rate']:.1f}%")
        
        # Save detailed results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"retriever_integration_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        self.logger.info(f"\n📄 Detailed results saved to: {results_file}")
        self.logger.info("=" * 60)


async def main():
    """Main test execution function."""
    tester = RetrieverAgentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("RetrieverAgent Integration Test for Eunice Application")
    print("=" * 60)
    print("Testing RetrieverAgent functionality within the Eunice framework...")
    print("This will test real search engines with actual result extraction.")
    print("")
    
    asyncio.run(main())
