#!/usr/bin/env python3
"""
Demonstration of Multi-Round Iterations and Streaming Responses
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.ai_client_manager import AIClientManager
from config.config_manager import ConfigManager
from models.data_models import Message


def demonstrate_multi_round_collaboration():
    """Demonstrate multi-round collaborative AI responses."""
    print("🔄 MULTI-ROUND COLLABORATION DEMONSTRATION")
    print("=" * 60)
    
    # Initialize manager
    config_manager = ConfigManager()
    ai_manager = AIClientManager(config_manager)
    
    # Create test conversation
    messages = [
        Message(
            conversation_id="multi_round_test",
            participant="user",
            content="I want to build a machine learning model for predicting customer churn. Can you help me plan this project?"
        )
    ]
    
    print("User Query:", messages[0].content)
    print("\n" + "─" * 60)
    
    # Get collaborative responses with multiple rounds
    collaborative_responses = ai_manager.get_collaborative_responses(
        messages, 
        max_rounds=3
    )
    
    print("\n📊 COLLABORATIVE RESULTS:")
    print("=" * 60)
    
    for provider, data in collaborative_responses.items():
        print(f"\n🤖 {provider.upper()}:")
        print(f"Total rounds: {data['round_count']}")
        
        for round_data in data['responses']:
            print(f"\n  Round {round_data['round']}:")
            print(f"  {round_data['content'][:200]}...")
    
    print("\n✅ Multi-round collaboration completed!")


async def demonstrate_streaming_responses():
    """Demonstrate streaming AI responses."""
    print("\n\n🌊 STREAMING RESPONSES DEMONSTRATION")
    print("=" * 60)
    
    # Initialize manager
    config_manager = ConfigManager()
    ai_manager = AIClientManager(config_manager)
    
    # Create test conversation
    messages = [
        Message(
            conversation_id="streaming_test",
            participant="user", 
            content="Explain the benefits and challenges of microservices architecture"
        )
    ]
    
    print("User Query:", messages[0].content)
    print("\n" + "─" * 60)
    print("Streaming responses...\n")
    
    # Stream responses
    provider_responses = {}
    
    async for update in ai_manager.get_streaming_responses(messages):
        if update['type'] == 'providers_selected':
            print(f"🎯 Selected providers: {', '.join(update['providers'])}")
            
        elif update['type'] == 'provider_started':
            print(f"\n🤖 {update['provider'].upper()} starting...")
            provider_responses[update['provider']] = []
            
        elif update['type'] == 'response_chunk':
            provider_responses[update['provider']].append(update['chunk'])
            print(f"[{update['provider']}] {update['chunk']}", end='', flush=True)
            
        elif update['type'] == 'provider_completed':
            print(f"\n✅ {update['provider'].upper()} completed")
            
        elif update['type'] == 'provider_error':
            print(f"\n❌ {update['provider']} error: {update['error']}")
            
        elif update['type'] == 'conversation_completed':
            print(f"\n🎉 All {update['total_providers']} providers completed!")
    
    print("\n✅ Streaming demonstration completed!")


def demonstrate_sync_streaming():
    """Demonstrate synchronous streaming for CLI contexts."""
    print("\n\n🔄 SYNCHRONOUS STREAMING DEMONSTRATION")
    print("=" * 60)
    
    # Initialize manager
    config_manager = ConfigManager()
    ai_manager = AIClientManager(config_manager)
    
    # Create test conversation
    messages = [
        Message(
            conversation_id="sync_streaming_test",
            participant="user",
            content="What are the key considerations for database design?"
        )
    ]
    
    print("User Query:", messages[0].content)
    print("\n" + "─" * 60)
    print("Synchronous streaming...\n")
    
    # Use synchronous streaming
    for update in ai_manager.get_streaming_responses_sync(messages):
        if update['type'] == 'providers_selected':
            print(f"🎯 Selected providers: {', '.join(update['providers'])}")
            
        elif update['type'] == 'provider_started':
            print(f"\n🤖 {update['provider'].upper()} starting...")
            
        elif update['type'] == 'response_chunk':
            print(update['chunk'], end='', flush=True)
            
        elif update['type'] == 'provider_completed':
            print(f"\n✅ {update['provider'].upper()} completed")
            
        elif update['type'] == 'conversation_completed':
            print(f"\n🎉 All {update['total_providers']} providers completed!")
    
    print("\n✅ Synchronous streaming demonstration completed!")


async def main():
    """Run all demonstrations."""
    print("🚀 ADVANCED AI COLLABORATION FEATURES DEMO")
    print("=" * 70)
    
    # Run multi-round demonstration
    demonstrate_multi_round_collaboration()
    
    # Run async streaming demonstration
    await demonstrate_streaming_responses()
    
    # Run sync streaming demonstration
    demonstrate_sync_streaming()
    
    print("\n🎉 ALL DEMONSTRATIONS COMPLETED!")
    print("Key Features Demonstrated:")
    print("• Multi-round collaborative iterations")
    print("• Real-time streaming responses")
    print("• Synchronous streaming for CLI")
    print("• Advanced collaboration logic")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
