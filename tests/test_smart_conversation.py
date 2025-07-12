#!/usr/bin/env python3
"""
Test smart responses in a real conversation scenario
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from models.data_models import Project, Conversation, Message
from datetime import datetime


def test_smart_conversation():
    """Test smart responses in a conversation."""
    print("🧪 Testing Smart Responses in Conversation...")
    
    # Initialize components
    config = ConfigManager()
    db_manager = DatabaseManager(config.config.storage.database_path)
    ai_manager = AIClientManager(config)
    
    # Check if AI providers are available
    if not ai_manager.get_available_providers():
        print("⚠️  No AI providers available for testing. Skipping conversation test.")
        return
    
    # Create test project
    project = Project(
        name="Smart Response Test",
        description="Testing smart response logic"
    )
    db_manager.create_project(project)
    print(f"✓ Created test project: {project.name}")
    
    # Create test conversation
    conversation = Conversation(
        project_id=project.id,
        title="Smart Response Test Chat",
        description="Testing smart responses"
    )
    db_manager.create_conversation(conversation)
    print(f"✓ Created test conversation: {conversation.title}")
    
    # Test different types of messages
    test_messages = [
        {
            "content": "Hello! Can you help me with Python programming?",
            "expected_responses": ["openai", "xai"],  # Both should respond initially
            "description": "General programming question"
        },
        {
            "content": "I need help with a specific algorithm optimization",
            "expected_responses": ["openai"],  # OpenAI should be more relevant
            "description": "Technical algorithm question"
        },
        {
            "content": "Let's brainstorm some creative solutions for this problem",
            "expected_responses": ["xai"],  # xAI should be more relevant for creativity
            "description": "Creative brainstorming request"
        },
        {
            "content": "@openai what do you think about the previous solution?",
            "expected_responses": ["openai"],  # Direct mention
            "description": "Direct mention of OpenAI"
        }
    ]
    
    for i, test_case in enumerate(test_messages, 1):
        print(f"\n🔍 Test {i}: {test_case['description']}")
        
        # Create user message
        user_message = Message(
            conversation_id=conversation.id,
            participant="user",
            content=test_case["content"]
        )
        db_manager.create_message(user_message)
        
        # Get conversation session
        session = db_manager.get_conversation_session(conversation.id)
        context_messages = session.get_context_messages(4000)  # Get recent context
        
        # Test smart responses
        responses = ai_manager.get_smart_responses(context_messages)
        
        print(f"   Message: {test_case['content']}")
        print(f"   Expected responses from: {test_case['expected_responses']}")
        print(f"   Actual responses from: {list(responses.keys())}")
        
        # Save AI responses
        for provider, response in responses.items():
            if not response.startswith("Error:"):
                ai_message = Message(
                    conversation_id=conversation.id,
                    participant=provider,
                    content=response[:100] + "..." if len(response) > 100 else response
                )
                db_manager.create_message(ai_message)
        
        print(f"   ✓ {len(responses)} AI(s) responded")
    
    # Test response statistics
    print(f"\n📊 Conversation Statistics:")
    session = db_manager.get_conversation_session(conversation.id)
    stats = ai_manager.get_response_stats(session)
    
    print(f"   Total messages: {stats['total_messages']}")
    print(f"   User messages: {stats['user_messages']}")
    print(f"   AI responses: {sum(stats['ai_responses'].values())}")
    
    for provider, count in stats['ai_responses'].items():
        rate = stats['response_rate'][provider] * 100
        print(f"   {provider.upper()}: {count} responses ({rate:.1f}%)")
    
    print("\n✅ Smart conversation test completed successfully!")


if __name__ == "__main__":
    try:
        test_smart_conversation()
        print("\n🎉 All conversation tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
