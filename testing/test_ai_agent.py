#!/usr/bin/env python3
"""
Test script for AI Agent service implementation

This script validates the AI Agent service implementation according to
Architecture.md Phase 2 specifications. It tests:

1. Service initialization
2. Multi-provider support
3. Text generation capabilities
4. Streaming responses
5. Error handling and fallback
6. Cost tracking
7. Performance monitoring
8. Health checks

Usage:
    python test_ai_agent.py
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config_manager import ConfigManager
from src.agents.artificial_intelligence.ai_agent import AIAgent
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
        agent_type="ai_agent",
        action=action,
        payload=payload
    )


async def test_ai_agent_initialization():
    """Test AI Agent service initialization."""
    print("\n🔧 Testing AI Agent Initialization...")
    
    try:
        # Initialize config manager
        config_path = Path(__file__).parent.parent / "config" / "default_config.json"
        config_manager = ConfigManager(str(config_path))
        
        # Initialize AI Agent
        ai_agent = AIAgent(config_manager)
        
        # Check service info
        service_info = ai_agent.get_service_info()
        print(f"✅ Service ID: {service_info['service_id']}")
        print(f"✅ Service Type: {service_info['service_type']}")
        print(f"✅ Version: {service_info['version']}")
        print(f"✅ Available providers: {service_info['providers']}")
        print(f"✅ Capabilities: {len(service_info['capabilities'])} features")
        
        return ai_agent
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return None


async def test_text_generation(ai_agent: AIAgent):
    """Test text generation capabilities."""
    print("\n📝 Testing Text Generation...")
    
    try:
        # Test direct text generation
        response = await ai_agent.generate_text_direct(
            prompt="Explain the concept of artificial intelligence in one paragraph.",
            temperature=0.7,
            max_tokens=150
        )
        print(f"✅ Generated text ({len(response)} chars): {response[:100]}...")
        
        # Test via MCP protocol
        task = create_test_task("generate_text", {
            "prompt": "What is machine learning?",
            "temperature": 0.5,
            "max_tokens": 100
        })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ MCP response length: {result['response_length']} characters")
        print(f"✅ Provider used: {result['provider']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False


async def test_streaming_generation(ai_agent: AIAgent):
    """Test streaming text generation."""
    print("\n🌊 Testing Streaming Generation...")
    
    try:
        task = create_test_task("generate_stream", {
                "prompt": "Write a short story about AI helping researchers.",
                "temperature": 0.8,
                "max_tokens": 200
            })
        
        result = await ai_agent._process_task_impl(task)
        stream = result["stream"]
        
        chunks_received = 0
        total_text = ""
        
        async for chunk in stream:
            if "text" in chunk:
                total_text += chunk["text"]
                chunks_received += 1
            if chunks_received >= 5:  # Limit for testing
                break
        
        print(f"✅ Streaming works: {chunks_received} chunks, {len(total_text)} chars")
        return True
        
    except Exception as e:
        print(f"❌ Streaming generation failed: {e}")
        return False


async def test_embeddings(ai_agent: AIAgent):
    """Test embedding generation."""
    print("\n🔗 Testing Embeddings...")
    
    try:
        # Test direct embedding
        embedding = await ai_agent.get_embedding_direct(
            "This is a test sentence for embedding generation."
        )
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        
        # Test via MCP protocol
        task = create_test_task("get_embedding", {
                "text": "Machine learning is a subset of artificial intelligence."
            })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ MCP embedding: {result['dimensions']} dimensions")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return False


async def test_text_analysis(ai_agent: AIAgent):
    """Test text analysis capabilities."""
    print("\n🔍 Testing Text Analysis...")
    
    try:
        test_text = """
        Artificial intelligence represents a significant breakthrough in computer science.
        It has applications in healthcare, finance, transportation, and education.
        The technology continues to evolve rapidly with new developments every year.
        """
        
        task = create_test_task("analyze_text", {
                "text": test_text,
                "analysis_type": "comprehensive"
            })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ Analysis completed: {len(result['analysis'])} chars")
        print(f"✅ Analysis type: {result['analysis_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Text analysis failed: {e}")
        return False


async def test_translation(ai_agent: AIAgent):
    """Test translation capabilities."""
    print("\n🌐 Testing Translation...")
    
    try:
        task = create_test_task("translate_text", {
                "text": "Hello, how are you today?",
                "source_lang": "en",
                "target_lang": "es"
            })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ Translation: {result['translation']}")
        print(f"✅ Language pair: {result['source_lang']} -> {result['target_lang']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        return False


async def test_summarization(ai_agent: AIAgent):
    """Test text summarization."""
    print("\n📄 Testing Summarization...")
    
    try:
        long_text = """
        Artificial Intelligence (AI) is a broad field of computer science focused on creating 
        systems that can perform tasks that typically require human intelligence. These tasks 
        include learning, reasoning, problem-solving, perception, and language understanding. 
        AI systems can be categorized into narrow AI, which is designed for specific tasks, 
        and general AI, which would have human-like cognitive abilities across various domains. 
        Machine learning, a subset of AI, involves training algorithms on data to make predictions 
        or decisions without being explicitly programmed for every scenario. Deep learning, 
        a further subset of machine learning, uses neural networks with multiple layers to 
        model and understand complex patterns in data. AI has applications in numerous fields 
        including healthcare, finance, transportation, education, and entertainment.
        """
        
        task = create_test_task("summarize_text", {
                "text": long_text,
                "summary_type": "concise",
                "max_length": 50
            })
        
        result = await ai_agent._process_task_impl(task)
        print(f"✅ Summary: {result['summary']}")
        print(f"✅ Compression ratio: {result['compression_ratio']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return False


async def test_health_and_stats(ai_agent: AIAgent):
    """Test health check and statistics."""
    print("\n🏥 Testing Health Check and Statistics...")
    
    try:
        # Health check
        health_task = create_test_task("health_check", {})
        
        health_result = await ai_agent._process_task_impl(health_task)
        print(f"✅ Service status: {health_result['status']}")
        print(f"✅ Success rate: {health_result['success_rate']:.2%}")
        print(f"✅ Requests processed: {health_result['requests_processed']}")
        
        # Statistics
        stats_task = create_test_task("get_stats", {})
        
        stats_result = await ai_agent._process_task_impl(stats_task)
        print(f"✅ Service uptime: {stats_result['service_stats']['uptime']:.2f}s")
        print(f"✅ Total cost: ${stats_result['cost_stats']['total_cost']:.6f}")
        print(f"✅ Available providers: {stats_result['provider_stats']['available_providers']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health/stats check failed: {e}")
        return False


async def test_error_handling(ai_agent: AIAgent):
    """Test error handling and fallback mechanisms."""
    print("\n⚠️ Testing Error Handling...")
    
    try:
        # Test invalid action
        try:
            invalid_task = create_test_task("invalid_action", {})
            await ai_agent._process_task_impl(invalid_task)
            print("❌ Should have raised error for invalid action")
            return False
        except ValueError as e:
            print(f"✅ Correctly handled invalid action: {e}")
        
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


async def main():
    """Run comprehensive AI Agent tests."""
    print("🚀 Starting AI Agent Service Tests")
    print("=" * 50)
    
    # Initialize AI Agent
    ai_agent = await test_ai_agent_initialization()
    if not ai_agent:
        print("\n❌ Test suite failed at initialization")
        return False
    
    # Run test suite
    tests = [
        test_text_generation,
        test_streaming_generation,
        test_embeddings,
        test_text_analysis,
        test_translation,
        test_summarization,
        test_health_and_stats,
        test_error_handling
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
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AI Agent service is working correctly.")
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
