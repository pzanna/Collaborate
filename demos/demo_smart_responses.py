#!/usr/bin/env python3
"""
Demonstration of Smart Response Logic Features
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.response_coordinator import ResponseCoordinator
from config.config_manager import ConfigManager
from models.data_models import Message
from datetime import datetime


def demonstrate_smart_responses():
    """Demonstrate the smart response logic features."""
    print("🎯 SMART RESPONSE LOGIC DEMONSTRATION")
    print("=" * 50)
    
    # Initialize coordinator
    config = ConfigManager()
    coordinator = ResponseCoordinator(config)
    available_providers = ["openai", "xai"]
    
    print(f"Available AI providers: {', '.join(available_providers)}")
    print(f"Response threshold: {coordinator.response_threshold}")
    print(f"Max consecutive responses: {coordinator.max_consecutive_responses}")
    print()
    
    # Test scenarios
    scenarios = [
        {
            "title": "1. General Question - Both AIs Should Respond",
            "message": "Can you help me understand machine learning?",
            "context": [],
            "expected": "Both AIs respond to general questions"
        },
        {
            "title": "2. Technical Question - OpenAI Should Be More Relevant",
            "message": "I need help debugging this Python code with algorithms",
            "context": [],
            "expected": "OpenAI has higher relevance for technical content"
        },
        {
            "title": "3. Creative Question - xAI Should Be More Relevant",
            "message": "Let's brainstorm innovative approaches to this problem",
            "context": [],
            "expected": "xAI has higher relevance for creative content"
        },
        {
            "title": "4. Direct Mention - Only Mentioned AI Responds",
            "message": "@openai what do you think about this approach?",
            "context": [],
            "expected": "Only OpenAI responds when directly mentioned"
        },
        {
            "title": "5. Consecutive Response Limiting",
            "message": "What else can you tell me?",
            "context": [
                Message(conversation_id="test", participant="openai", content="Response 1", timestamp=datetime.now()),
                Message(conversation_id="test", participant="openai", content="Response 2", timestamp=datetime.now()),
                Message(conversation_id="test", participant="openai", content="Response 3", timestamp=datetime.now()),
                Message(conversation_id="test", participant="openai", content="Response 4", timestamp=datetime.now())
            ],
            "expected": "OpenAI should be limited due to consecutive responses"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['title']}")
        print("-" * len(scenario['title']))
        
        # Create test message
        message = Message(
            conversation_id="demo",
            participant="user",
            content=scenario["message"],
            timestamp=datetime.now()
        )
        
        print(f"User message: \"{scenario['message']}\"")
        
        # Get responding providers
        responding_providers = coordinator.coordinate_responses(
            message, scenario["context"], available_providers
        )
        
        print(f"Responding providers: {responding_providers}")
        
        # Show relevance scores
        openai_relevance = coordinator._calculate_relevance(message, "openai", scenario["context"])
        xai_relevance = coordinator._calculate_relevance(message, "xai", scenario["context"])
        
        print(f"Relevance scores - OpenAI: {openai_relevance:.2f}, xAI: {xai_relevance:.2f}")
        
        # Check for direct mentions
        openai_mentioned = coordinator._is_ai_mentioned(message, "openai")
        xai_mentioned = coordinator._is_ai_mentioned(message, "xai")
        
        if openai_mentioned or xai_mentioned:
            print(f"Direct mentions - OpenAI: {openai_mentioned}, xAI: {xai_mentioned}")
        
        # Check consecutive responses
        if scenario["context"]:
            openai_consecutive = coordinator._has_too_many_consecutive_responses("openai", scenario["context"])
            print(f"OpenAI consecutive limit reached: {openai_consecutive}")
        
        print(f"Expected: {scenario['expected']}")
        print(f"✓ Test completed")
    
    print(f"\n🎉 Smart Response Logic Demonstration Complete!")
    print("\nKey Features Demonstrated:")
    print("• Relevance-based response selection")
    print("• Provider specialization (technical vs creative)")
    print("• Direct mention handling")
    print("• Consecutive response limiting")
    print("• Context-aware decision making")


if __name__ == "__main__":
    try:
        demonstrate_smart_responses()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
