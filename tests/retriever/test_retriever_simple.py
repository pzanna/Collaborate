#!/usr/bin/env python3
"""
Simple RetrieverAgent Integration Test for Eunice Application

This is a simplified test that focuses on verifying the core functionality works.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.retriever_agent import RetrieverAgent
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction


async def test_search_functionality():
    """Test basic search functionality."""
    print("🚀 Testing RetrieverAgent Search Functionality")
    print("=" * 60)
    
    try:
        # Initialize components
        config_manager = ConfigManager()
        retriever_agent = RetrieverAgent(config_manager)
        await retriever_agent.initialize()
        print("✅ RetrieverAgent initialized successfully")
        
        # Test search
        action = ResearchAction(
            task_id="test_search",
            context_id="test_context", 
            agent_type="Retriever",
            action="search_information",
            payload={
                "query": "Python programming tutorial",
                "max_results": 3,
                "search_engines": ["google", "bing"]
            }
        )
        
        print("🔍 Testing search...")
        start_time = time.time()
        response = await retriever_agent.process_task(action)
        duration = time.time() - start_time
        
        if response.status == "completed" and response.result:
            results = response.result["results"]
            print(f"✅ Search completed in {duration:.2f}s")
            print(f"   Found {len(results)} results")
            print(f"   Engines used: {response.result['search_engines_used']}")
            
            # Show first result
            if results:
                first_result = results[0]
                print(f"   Sample result: {first_result['title']}")
                print(f"   URL: {first_result['url']}")
                print(f"   Source: {first_result['source']}")
        else:
            print(f"❌ Search failed: {response.error}")
            
        # Test content extraction
        print("\n🌐 Testing content extraction...")
        action = ResearchAction(
            task_id="test_extract",
            context_id="test_context",
            agent_type="Retriever", 
            action="extract_web_content",
            payload={"url": "https://www.python.org/"}
        )
        
        start_time = time.time()
        response = await retriever_agent.process_task(action)
        duration = time.time() - start_time
        
        if response.status == "completed" and response.result:
            result = response.result
            print(f"✅ Content extraction completed in {duration:.2f}s")
            print(f"   Title: {result['title']}")
            print(f"   Content length: {len(result['content'])} characters")
        else:
            print(f"❌ Content extraction failed: {response.error}")
            
        # Test academic search
        print("\n🎓 Testing academic search...")
        action = ResearchAction(
            task_id="test_academic",
            context_id="test_context",
            agent_type="Retriever",
            action="search_academic_papers",
            payload={
                "query": "machine learning algorithms",
                "max_results": 3
            }
        )
        
        start_time = time.time()
        response = await retriever_agent.process_task(action)
        duration = time.time() - start_time
        
        if response.status == "completed" and response.result:
            results = response.result["results"]
            print(f"✅ Academic search completed in {duration:.2f}s")
            print(f"   Found {len(results)} academic papers")
            if results:
                print(f"   Sample paper: {results[0]['title']}")
        else:
            print(f"❌ Academic search failed: {response.error}")
        
        # Test error handling
        print("\n⚠️ Testing error handling...")
        action = ResearchAction(
            task_id="test_error",
            context_id="test_context",
            agent_type="Retriever",
            action="extract_web_content",
            payload={"url": "invalid://not-a-real-url"}
        )
        
        response = await retriever_agent.process_task(action)
        
        if response.status == "failed":
            print("✅ Error handling working correctly")
            print(f"   Error properly caught: {response.error}")
        else:
            print("❌ Error handling not working properly")
            
        # Cleanup
        await retriever_agent.stop()
        print("\n✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("RetrieverAgent Simple Integration Test")
    print("Testing updated search functionality within Eunice framework")
    print("")
    
    asyncio.run(test_search_functionality())
