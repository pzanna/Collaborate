#!/usr/bin/env python3
"""Test script to verify _add_collaboration_context integration with AIClientManager."""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.ai_client_manager import AIClientManager
from src.config.config_manager import ConfigManager
from src.models.data_models import Message


def test_collaboration_context_integration():
    """Test that AIClientManager can call _add_collaboration_context without errors."""
    print("🔧 Testing Collaboration Context Integration...")
    
    # Initialize components
    config_manager = ConfigManager()
    ai_manager = AIClientManager(config_manager)
    
    # Create test messages
    history = [
        Message(
            id="test-1",
            conversation_id="test-conv",
            participant="user",
            content="Can you help me with this Python code?",
            timestamp=datetime.now()
        ),
        Message(
            id="test-2", 
            conversation_id="test-conv",
            participant="openai",
            content="I can help! Let me analyze the code. What do you think, xai?",
            timestamp=datetime.now()
        )
    ]
    
    try:
        # Test adapt_system_prompt which calls _add_collaboration_context
        prompt = ai_manager.adapt_system_prompt("xai", "creative brainstorming", history)
        print("✅ adapt_system_prompt executed successfully")
        print(f"📝 Generated prompt contains collaboration context: {'COLLABORATION CONTEXT' in prompt}")
        
        if "COLLABORATION CONTEXT" in prompt:
            context_start = prompt.find("COLLABORATION CONTEXT")
            context_part = prompt[context_start:context_start+150]
            print(f"🔍 Context preview: {context_part}...")
        
    except AttributeError as e:
        if "_add_collaboration_context" in str(e):
            print("❌ Error: _add_collaboration_context method still missing")
            return False
        else:
            print(f"❌ Other AttributeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    print("✅ Integration test passed - no more '_add_collaboration_context' error!")
    return True


if __name__ == "__main__":
    success = test_collaboration_context_integration()
    if success:
        print("\n🎉 The XAI error has been resolved!")
    else:
        print("\n💥 The error still exists - need more fixes")
