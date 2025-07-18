#!/usr/bin/env python3
"""
Test script to trigger AI API logging
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.config_manager import ConfigManager
from models.data_models import Message, AIConfig
from ai_clients.openai_client import OpenAIClient
from ai_clients.xai_client import XAIClient
from core.ai_client_manager import AIClientManager
from datetime import datetime


async def test_ai_logging():
    """Test AI client logging functionality"""
    print("🧪 Testing AI API logging...")
    
    # Initialize config manager and setup logging
    config_manager = ConfigManager()
    config_manager.setup_logging()
    
    # Create test messages
    test_messages = [
        Message(
            conversation_id="test-logging",
            participant="user",
            content="Hello! Can you explain what artificial intelligence is in simple terms?",
            timestamp=datetime.now()
        )
    ]
    
    print(f"📝 Created test message: {test_messages[0].content}")
    
    # Test AI client manager
    ai_manager = AIClientManager(config_manager)
    
    print(f"🤖 Available AI providers: {ai_manager.get_available_providers()}")
    
    # Test getting smart responses (should trigger AI API calls)
    print("📞 Making AI API calls...")
    
    try:
        responses = ai_manager.get_smart_responses(test_messages)
        print(f"✅ Got responses from {len(responses)} providers")
        
        for provider, response in responses.items():
            print(f"🤖 {provider}: {response[:100]}...")
            
    except Exception as e:
        print(f"❌ Error during AI API calls: {e}")
        import traceback
        traceback.print_exc()
    
    print("🔍 Check logs/ai_api.log for detailed API logging")


if __name__ == "__main__":
    asyncio.run(test_ai_logging())
