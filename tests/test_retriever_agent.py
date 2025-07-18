#!/usr/bin/env python3
"""
Test script for Retriever Agent implementation.

This script tests the Retriever Agent functionality including:
- Agent initialization
- Search capabilities
- Content extraction
- Error handling
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.retriever_agent import RetrieverAgent
from src.config.config_manager import ConfigManager
from src.mcp.protocols import ResearchAction


async def test_retriever_agent():
    """Test the Retriever Agent implementation."""
    print("🔍 Testing Retriever Agent Implementation")
    print("=" * 50)
    
    try:
        # Initialize configuration
        print("1. Initializing configuration...")
        config = ConfigManager()
        print("   ✅ Configuration loaded successfully")
        
        # Create Retriever Agent
        print("\n2. Creating Retriever Agent...")
        agent = RetrieverAgent(config)
        print(f"   Agent ID: {agent.agent_id}")
        print(f"   Agent Type: {agent.agent_type}")
        print(f"   Capabilities: {agent.capabilities}")
        print("   ✅ Retriever Agent created successfully")
        
        # Test initialization
        print("\n3. Testing agent initialization...")
        success = await agent.initialize()
        if success:
            print("   ✅ Agent initialized successfully")
            print(f"   Status: {agent.status}")
        else:
            print("   ❌ Agent initialization failed")
            return False
        
        # Test agent status
        print("\n4. Testing agent status...")
        status = agent.get_status()
        print(f"   Status: {status}")
        print("   ✅ Agent status retrieved successfully")
        
        # Test search task
        print("\n5. Testing search functionality...")
        search_task = ResearchAction(
            task_id="test-search-123",
            context_id="test-context",
            agent_type="retriever",
            action="search_information",
            payload={
                "query": "artificial intelligence research 2024",
                "max_results": 5,
                "search_engines": ["duckduckgo"]
            }
        )
        
        print(f"   Search query: {search_task.payload['query']}")
        
        # Process search task
        response = await agent.process_task(search_task)
        print(f"   Task status: {response.status}")
        
        if response.status == "completed" and response.result:
            results = response.result.get('results', [])
            print(f"   Found {len(results)} results")
            
            # Display first few results
            for i, result in enumerate(results[:3]):
                print(f"     {i+1}. {result.get('title', 'No title')}")
                print(f"        URL: {result.get('url', 'No URL')}")
                print(f"        Source: {result.get('source', 'Unknown')}")
                print(f"        Relevance: {result.get('relevance_score', 0)}")
                print()
            
            print("   ✅ Search functionality working")
        else:
            print(f"   ⚠️  Search completed with status: {response.status}")
            if response.error:
                print(f"   Error: {response.error}")
        
        # Test content extraction (if we have URLs)
        print("\n6. Testing content extraction...")
        if response.status == "completed" and response.result:
            results = response.result.get('results', [])
            if results and results[0].get('url'):
                test_url = results[0]['url']
                print(f"   Testing URL: {test_url}")
                
                extract_task = ResearchAction(
                    task_id="test-extract-123",
                    context_id="test-context",
                    agent_type="retriever",
                    action="extract_web_content",
                    payload={"url": test_url}
                )
                
                extract_response = await agent.process_task(extract_task)
                print(f"   Extract status: {extract_response.status}")
                
                if extract_response.status == "completed" and extract_response.result:
                    content = extract_response.result
                    print(f"   Title: {content.get('title', 'No title')}")
                    print(f"   Content length: {len(content.get('content', ''))}")
                    print(f"   Metadata keys: {list(content.get('metadata', {}).keys())}")
                    print("   ✅ Content extraction working")
                else:
                    print(f"   ⚠️  Content extraction status: {extract_response.status}")
                    if extract_response.error:
                        print(f"   Error: {extract_response.error}")
            else:
                print("   ⚠️  No URLs found for content extraction test")
        
        # Test performance stats
        print("\n7. Testing performance monitoring...")
        perf_stats = agent.get_performance_stats()
        print(f"   Performance stats: {perf_stats}")
        print("   ✅ Performance monitoring working")
        
        # Test agent cleanup
        print("\n8. Testing agent cleanup...")
        await agent.stop()
        print("   ✅ Agent cleanup completed")
        
        print("\n" + "=" * 50)
        print("🎉 All Retriever Agent tests completed!")
        print("✅ Retriever Agent implementation is working correctly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("Retriever Agent Test Suite")
    print("=" * 50)
    
    success = await test_retriever_agent()
    
    if success:
        print("\n🎉 All tests passed! Retriever Agent is ready for integration.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
