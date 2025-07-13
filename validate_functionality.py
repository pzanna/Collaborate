#!/usr/bin/env python3
"""
Quick validation of AI Client Manager and Response Coordinator functionality
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.ai_client_manager import AIClientManager
from core.response_coordinator import ResponseCoordinator
from config.config_manager import ConfigManager
from models.data_models import Message


def test_basic_functionality():
    """Test basic functionality without API calls."""
    print("🧪 Testing Basic Functionality...")
    
    # Initialize components
    config_manager = ConfigManager()
    coordinator = ResponseCoordinator(config_manager)
    ai_manager = AIClientManager(config_manager)
    
    print("✅ Components initialized successfully")
    
    # Test message creation
    test_message = Message(
        conversation_id="test_conv",
        participant="user",
        content="Test message for validation"
    )
    
    print("✅ Message creation works")
    
    # Test response coordination
    available_providers = ["openai", "xai"]
    context = []
    
    responding_providers = coordinator.coordinate_responses(
        test_message, context, available_providers
    )
    
    print(f"✅ Response coordination works: {responding_providers}")
    
    # Test relevance calculation
    relevance_openai = coordinator._calculate_relevance(test_message, "openai", context)
    relevance_xai = coordinator._calculate_relevance(test_message, "xai", context)
    
    print(f"✅ Relevance calculation: OpenAI={relevance_openai:.2f}, xAI={relevance_xai:.2f}")
    
    # Test system prompt adaptation
    adapted_prompt = ai_manager.adapt_system_prompt("openai", "code help", context)
    
    print(f"✅ System prompt adaptation works: {len(adapted_prompt)} chars")
    
    # Test provider health
    health = ai_manager.get_provider_health()
    
    print(f"✅ Provider health check: {health}")
    
    # Test mentions
    mention_message = Message(
        conversation_id="test_conv",
        participant="user", 
        content="@openai can you help with this code?"
    )
    
    mentioned_providers = coordinator.coordinate_responses(
        mention_message, context, available_providers
    )
    
    print(f"✅ Mention detection: {mentioned_providers}")
    
    print("\n🎉 All basic functionality tests passed!")


if __name__ == "__main__":
    test_basic_functionality()
