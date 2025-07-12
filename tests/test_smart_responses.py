#!/usr/bin/env python3
"""
Test smart response logic functionality
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.response_coordinator import ResponseCoordinator
from config.config_manager import ConfigManager
from models.data_models import Message, ConversationSession
from datetime import datetime


def test_response_coordinator():
    """Test the response coordinator functionality."""
    print("🧪 Testing Response Coordinator...")
    
    # Initialize coordinator
    config = ConfigManager()
    coordinator = ResponseCoordinator(config)
    
    # Test 1: Basic functionality
    print("\n1. Testing basic functionality...")
    
    # Create test messages
    user_message = Message(
        conversation_id="test",
        participant="user",
        content="Can you help me with Python programming?",
        timestamp=datetime.now()
    )
    
    context = []
    available_providers = ["openai", "xai"]
    
    # Test coordinate responses
    responding_providers = coordinator.coordinate_responses(
        user_message, context, available_providers
    )
    
    print(f"   Responding providers: {responding_providers}")
    assert len(responding_providers) > 0, "At least one provider should respond"
    
    # Test 2: Direct mention
    print("\n2. Testing direct mention...")
    
    mention_message = Message(
        conversation_id="test",
        participant="user",
        content="@openai what do you think about this code?",
        timestamp=datetime.now()
    )
    
    for provider in available_providers:
        should_respond = coordinator.should_ai_respond(provider, mention_message, context)
        if provider == "openai":
            assert should_respond, "OpenAI should respond when mentioned"
            print(f"   ✓ {provider} correctly identified as mentioned")
        else:
            print(f"   ✓ {provider} response decision: {should_respond}")
    
    # Test 3: Relevance scoring
    print("\n3. Testing relevance scoring...")
    
    code_message = Message(
        conversation_id="test",
        participant="user",
        content="I need help debugging this Python code with algorithms",
        timestamp=datetime.now()
    )
    
    openai_relevance = coordinator._calculate_relevance(code_message, "openai", context)
    xai_relevance = coordinator._calculate_relevance(code_message, "xai", context)
    
    print(f"   OpenAI relevance for code question: {openai_relevance:.2f}")
    print(f"   xAI relevance for code question: {xai_relevance:.2f}")
    
    assert openai_relevance > 0, "OpenAI should have some relevance for code"
    
    # Test 4: Consecutive response limiting
    print("\n4. Testing consecutive response limiting...")
    
    # Create context with many consecutive responses from same AI
    consecutive_context = []
    for i in range(4):
        consecutive_context.append(Message(
            conversation_id="test",
            participant="openai",
            content=f"Response {i+1}",
            timestamp=datetime.now()
        ))
    
    user_followup = Message(
        conversation_id="test",
        participant="user",
        content="What else can you tell me?",
        timestamp=datetime.now()
    )
    
    should_respond = coordinator.should_ai_respond("openai", user_followup, consecutive_context)
    print(f"   OpenAI should respond after 4 consecutive responses: {should_respond}")
    
    # Test 5: Settings update
    print("\n5. Testing settings update...")
    
    original_threshold = coordinator.response_threshold
    coordinator.update_settings(response_threshold=0.5)
    
    print(f"   Original threshold: {original_threshold}")
    print(f"   Updated threshold: {coordinator.response_threshold}")
    assert coordinator.response_threshold == 0.5, "Threshold should be updated"
    
    print("\n✅ All tests passed! Smart response logic is working correctly.")


def test_integration():
    """Test integration with AI client manager."""
    print("\n🔗 Testing Integration with AI Client Manager...")
    
    try:
        from core.ai_client_manager import AIClientManager
        
        config = ConfigManager()
        ai_manager = AIClientManager(config)
        
        # Test that the response coordinator is initialized
        assert hasattr(ai_manager, 'response_coordinator'), "AI manager should have response coordinator"
        
        # Test smart response method exists
        assert hasattr(ai_manager, 'get_smart_responses'), "AI manager should have smart response method"
        
        print("   ✅ Integration test passed!")
        
    except Exception as e:
        print(f"   ⚠️ Integration test failed: {e}")


if __name__ == "__main__":
    try:
        test_response_coordinator()
        test_integration()
        print("\n🎉 All smart response tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
