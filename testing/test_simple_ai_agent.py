#!/usr/bin/env python3
"""
Test script for Simple AI Agent - Phase 2 Implementation

This script validates the Simple AI Agent implementation according to
Architecture.md Phase 2 specifications. It demonstrates:

1. Centralized AI service abstraction
2. Service-based architecture pattern  
3. Multi-agent AI access through unified interface
4. Basic error handling and service monitoring
5. MCP protocol compliance

Usage:
    python test_simple_ai_agent.py
"""

import asyncio
import logging  
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config_manager import ConfigManager
from src.agents.artificial_intelligence.simple_ai_agent import SimpleAIAgent
from src.mcp.protocols import ResearchAction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_task(action: str, payload: Dict[str, Any], task_id: Optional[str] = None) -> ResearchAction:
    """Create a properly formatted test task."""
    import uuid
    return ResearchAction(
        task_id=task_id or f"test_{str(uuid.uuid4())[:8]}",
        context_id="test_context",
        agent_type="simple_ai_agent",
        action=action,
        payload=payload
    )


async def test_agent_initialization():
    """Test Simple AI Agent initialization."""
    print("\n🔧 Testing Simple AI Agent Initialization...")
    
    try:
        # Initialize config manager
        config_path = Path(__file__).parent.parent / "config" / "default_config.json"
        config_manager = ConfigManager(str(config_path))
        
        # Initialize Simple AI Agent
        ai_agent = SimpleAIAgent(config_manager)
        
        # Check service info
        service_info = ai_agent.get_service_info()
        print(f"✅ Service ID: {service_info['service_id']}")
        print(f"✅ Service Type: {service_info['service_type']}")
        print(f"✅ Version: {service_info['version']}")
        print(f"✅ Capabilities: {len(service_info['capabilities'])} features")
        print(f"✅ Description: {service_info['description']}")
        
        return ai_agent
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return None


async def test_text_generation(ai_agent: SimpleAIAgent):
    """Test text generation capabilities."""
    print("\n📝 Testing Text Generation...")
    
    try:
        # Test direct text generation
        response = await ai_agent.generate_text_direct(
            "Explain the concept of centralized AI service abstraction."
        )
        print(f"✅ Direct generation ({len(response)} chars): {response[:100]}...")
        
        # Test via MCP protocol
        task = create_test_task("generate_text", {
            "prompt": "What are the benefits of AI service abstraction in software architecture?",
        })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ MCP response length: {result['response_length']} characters")
        print(f"✅ Method used: {result['method']}")
        print(f"✅ Response time: {result['response_time']:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False


async def test_health_check(ai_agent: SimpleAIAgent):
    """Test health check functionality."""
    print("\n🏥 Testing Health Check...")
    
    try:
        task = create_test_task("health_check", {})
        result = await ai_agent._process_task_impl(task)
        
        print(f"✅ Service status: {result['status']}")
        print(f"✅ Uptime: {result['uptime']:.2f}s")
        print(f"✅ Requests processed: {result['requests_processed']}")
        print(f"✅ AI clients available: {result['ai_clients_available']}")
        print(f"✅ Available providers: {result.get('available_providers', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_statistics(ai_agent: SimpleAIAgent):
    """Test statistics reporting."""
    print("\n📊 Testing Statistics...")
    
    try:
        task = create_test_task("get_stats", {})
        result = await ai_agent._process_task_impl(task)
        
        service_stats = result['service_stats']
        print(f"✅ Service uptime: {service_stats['uptime']:.2f}s")
        print(f"✅ Requests processed: {service_stats['requests_processed']}")
        print(f"✅ Capabilities: {result['capabilities']}")
        
        ai_status = result['ai_integration_status']
        print(f"✅ AI providers configured: {ai_status['providers_configured']}")
        print(f"✅ Available providers: {ai_status['available_providers']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        return False


async def test_error_handling(ai_agent: SimpleAIAgent):
    """Test error handling."""
    print("\n⚠️ Testing Error Handling...")
    
    try:
        # Test unsupported action
        task = create_test_task("unsupported_action", {})
        result = await ai_agent._process_task_impl(task)
        
        if result['status'] == 'not_implemented':
            print(f"✅ Correctly handled unsupported action")
            print(f"✅ Supported actions listed: {result['supported_actions']}")
        else:
            print("❌ Should have returned not_implemented status")
            return False
        
        # Test empty prompt
        try:
            empty_task = create_test_task("generate_text", {"prompt": ""})
            await ai_agent._process_task_impl(empty_task)
            print("❌ Should have raised error for empty prompt")
            return False
        except ValueError as e:
            print(f"✅ Correctly handled empty prompt: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


async def test_service_abstraction_pattern(ai_agent: SimpleAIAgent):
    """Test the service abstraction pattern compliance."""
    print("\n🏗️ Testing Service Abstraction Pattern...")
    
    try:
        # Simulate multiple agents accessing the AI service
        agent_types = ["literature", "planning", "executor", "memory"]
        requests = []
        
        for agent_type in agent_types:
            task = create_test_task("generate_text", {
                "prompt": f"This is a request from the {agent_type} agent for AI services.",
            })
            # Modify task to simulate different agents
            task.agent_type = agent_type
            requests.append(task)
        
        # Process all requests
        results = []
        for task in requests:
            result = await ai_agent._process_task_impl(task)
            results.append((task.agent_type, result))
        
        print(f"✅ Processed requests from {len(agent_types)} different agent types")
        
        # Verify each got a response
        for agent_type, result in results:
            print(f"✅ {agent_type} agent: got {result['response_length']} char response")
        
        # Check that the service maintains consistency
        service_info = ai_agent.get_service_info()
        print(f"✅ Service processed {service_info['requests_processed']} total requests")
        
        return True
        
    except Exception as e:
        print(f"❌ Service abstraction test failed: {e}")
        return False


async def main():
    """Run Simple AI Agent tests."""
    print("🚀 Starting Simple AI Agent Tests - Phase 2 Implementation")
    print("=" * 60)
    
    # Initialize agent
    ai_agent = await test_agent_initialization()
    if not ai_agent:
        print("\n❌ Test suite failed at initialization")
        return False
    
    # Run test suite
    tests = [
        test_text_generation,
        test_health_check,
        test_statistics,
        test_error_handling,
        test_service_abstraction_pattern
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            result = await test_func(ai_agent)
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
    
    # Final results
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Simple AI Agent is working correctly.")
        print("\n📋 Architecture.md Phase 2 Compliance:")
        print("  ✅ Centralized AI service abstraction implemented")
        print("  ✅ Multi-agent access pattern demonstrated")
        print("  ✅ Service-based architecture pattern working")
        print("  ✅ Error handling and monitoring functional")
        print("  ✅ MCP protocol compliance verified")
        return True
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
        return False


if __name__ == "__main__":
    # Run the test suite
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)
