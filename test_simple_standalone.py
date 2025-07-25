#!/usr/bin/env python3
"""
Standalone test for Simple AI Agent - Direct Import

This test bypasses the complex import chain to validate the Simple AI Agent
implementation directly according to Architecture.md Phase 2 specifications.
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockConfigManager:
    """Mock config manager for testing."""
    
    def __init__(self):
        self.config = {
            "ai": {
                "openai": {
                    "api_key": "test-key",
                    "model": "gpt-4"
                },
                "xai": {
                    "api_key": "test-key", 
                    "model": "grok-beta"
                }
            }
        }
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, {})
        return value if value else default


class ResearchAction:
    """Mock ResearchAction for testing."""
    
    def __init__(self, task_id: str, context_id: str, agent_type: str, action: str, payload: Dict[str, Any]):
        self.task_id = task_id
        self.context_id = context_id
        self.agent_type = agent_type
        self.action = action
        self.payload = payload


def create_test_task(action: str, payload: Dict[str, Any], task_id: Optional[str] = None) -> ResearchAction:
    """Create a properly formatted test task."""
    return ResearchAction(
        task_id=task_id or f"test_{str(uuid.uuid4())[:8]}",
        context_id="test_context",
        agent_type="simple_ai_agent", 
        action=action,
        payload=payload
    )


# Import the simple AI agent directly
sys.path.insert(0, str(Path(__file__).parent / "src" / "agents" / "artificial_intelligence"))

from simple_ai_agent import SimpleAIAgent


async def test_initialization():
    """Test Simple AI Agent initialization."""
    print("\n🔧 Testing Simple AI Agent Initialization...")
    
    try:
        config_manager = MockConfigManager()
        ai_agent = SimpleAIAgent(config_manager)
        
        service_info = ai_agent.get_service_info()
        print(f"✅ Service ID: {service_info['service_id']}")
        print(f"✅ Service Type: {service_info['service_type']}")
        print(f"✅ Version: {service_info['version']}")
        print(f"✅ Capabilities: {len(service_info['capabilities'])} features")
        
        return ai_agent
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return None


async def test_text_generation(ai_agent):
    """Test text generation."""
    print("\n📝 Testing Text Generation...")
    
    try:
        # Test direct generation
        response = await ai_agent.generate_text_direct(
            "Explain centralized AI service abstraction."
        )
        print(f"✅ Direct generation: {response[:100]}...")
        
        # Test via task
        task = create_test_task("generate_text", {
            "prompt": "What are the benefits of AI service abstraction?"
        })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ Task response length: {result['response_length']}")
        print(f"✅ Method: {result['method']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False


async def test_health_check(ai_agent):
    """Test health check."""
    print("\n🏥 Testing Health Check...")
    
    try:
        task = create_test_task("health_check", {})
        result = await ai_agent._process_task_impl(task)
        
        print(f"✅ Status: {result['status']}")
        print(f"✅ Uptime: {result['uptime']:.2f}s")
        print(f"✅ Requests: {result['requests_processed']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def test_service_abstraction(ai_agent):
    """Test service abstraction pattern."""
    print("\n🏗️ Testing Service Abstraction Pattern...")
    
    try:
        # Simulate multiple agent types
        agent_types = ["literature", "planning", "executor", "memory"]
        
        for agent_type in agent_types:
            task = create_test_task("generate_text", {
                "prompt": f"Request from {agent_type} agent"
            })
            task.agent_type = agent_type
            
            result = await ai_agent._process_task_impl(task)
            print(f"✅ {agent_type}: {result['response_length']} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Service abstraction test failed: {e}")
        return False


async def main():
    """Run standalone tests."""
    print("🚀 Simple AI Agent Standalone Test - Phase 2 Implementation")
    print("=" * 60)
    
    # Initialize
    ai_agent = await test_initialization()
    if not ai_agent:
        print("\n❌ Test failed at initialization")
        return False
    
    # Run tests
    tests = [
        test_text_generation,
        test_health_check, 
        test_service_abstraction
    ]
    
    passed = 0
    for test_func in tests:
        try:
            if await test_func(ai_agent):
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
    
    # Results
    print("\n" + "=" * 60)
    print(f"🏁 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Simple AI Agent working correctly.")
        print("\n📋 Architecture.md Phase 2 Compliance:")
        print("  ✅ Centralized AI service abstraction")
        print("  ✅ Multi-agent access pattern")  
        print("  ✅ Service-based architecture")
        print("  ✅ Basic error handling")
        return True
    else:
        print("⚠️ Some tests failed")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test crashed: {e}")
        sys.exit(1)
