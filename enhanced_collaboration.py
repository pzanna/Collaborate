"""Enhanced Collaboration Manager with Real-Time Streaming Support

This extends the main collaboration script to support real-time streaming
responses, making conversations feel more natural and Slack-like.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.streaming_coordinator import StreamingResponseCoordinator
from src.core.response_coordinator import ResponseCoordinator
from src.core.ai_client_manager import AIClientManager
from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.models.data_models import Message
from typing import List


class EnhancedCollaborationManager:
    """Enhanced collaboration manager with real-time streaming support."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager("data/collaborate.db")
        self.ai_manager = AIClientManager(self.config_manager)
        self.response_coordinator = ResponseCoordinator(self.config_manager)
        self.streaming_coordinator = StreamingResponseCoordinator(
            self.config_manager, self.response_coordinator
        )
        
    async def stream_conversation_response(
        self, 
        user_message: Message, 
        context: List[Message],
        conversation_id: str
    ):
        """Stream AI responses in real-time for a more natural conversation flow."""
        
        available_providers = self.ai_manager.get_available_providers()
        if not available_providers:
            print("❌ No AI providers available")
            return
        
        print(f"\n💭 Processing: '{user_message.content[:50]}{'...' if len(user_message.content) > 50 else ''}'")
        
        # Track responses for database storage
        completed_responses = {}
        
        try:
            async for update in self.streaming_coordinator.stream_with_interruption_support(
                user_message, context, available_providers, self.ai_manager
            ):
                update_type = update['type']
                
                if update_type == 'queue_determined':
                    providers = update['queue']
                    print(f"🎯 Response queue: {' → '.join(providers)}")
                    
                elif update_type == 'interruption_detected':
                    providers = update['providers']
                    print(f"🚨 Interruption! Prioritizing: {', '.join(providers)}")
                    
                elif update_type == 'repair_needed':
                    provider = update['provider']
                    print(f"🔧 Routing clarification to {provider.upper()}")
                    
                elif update_type == 'provider_starting':
                    provider = update['provider']
                    position = update['position']
                    total = update['total']
                    print(f"\n🤖 {provider.upper()} ({position}/{total}): ", end='', flush=True)
                    
                elif update_type == 'response_chunk':
                    chunk = update['chunk']
                    print(chunk, end='', flush=True)
                    
                elif update_type == 'provider_completed':
                    provider = update['provider']
                    response = update['response']
                    completed_responses[provider] = response
                    
                    # Save to database
                    ai_message = Message(
                        conversation_id=conversation_id,
                        participant=provider,
                        content=response
                    )
                    self.db_manager.create_message(ai_message)
                    print(f"\n✅ {provider.upper()} completed and saved")
                    
                elif update_type == 'chain_detected':
                    from_provider = update['from_provider']
                    to_provider = update['to_provider']
                    print(f"\n🔗 {from_provider.upper()} is calling on {to_provider.upper()}")
                    
                elif update_type == 'queue_updated':
                    added_provider = update['added_provider']
                    print(f"📝 Added {added_provider.upper()} to speaking queue")
                    
                elif update_type == 'provider_error':
                    provider = update['provider']
                    error = update['error']
                    print(f"\n❌ Error from {provider.upper()}: {error}")
                    
                elif update_type == 'conversation_completed':
                    total_providers = update['total_providers']
                    print(f"\n🎉 Conversation chain completed ({total_providers} responses)")
                    
                # Small delay for readability
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"\n❌ Streaming error: {e}")
            
        return completed_responses
    
    def get_streaming_vs_batch_comparison(self):
        """Return comparison data for streaming vs batch processing."""
        return {
            'batch_processing': {
                'flow': 'User → Wait → All responses at once',
                'user_experience': 'Long wait, then information dump',
                'conversation_feel': 'Robotic, disconnected',
                'chaining': 'No real-time chaining',
                'interruptions': 'Cannot handle mid-conversation interruptions',
                'typical_wait_time': '10-30 seconds'
            },
            'streaming_processing': {
                'flow': 'User → Immediate response stream → Chain continues',
                'user_experience': 'Immediate feedback, natural progression',
                'conversation_feel': 'Slack-like, engaging',
                'chaining': 'Real-time AI-to-AI handoffs',
                'interruptions': 'Can detect and respond to interruptions',
                'typical_wait_time': '1-3 seconds to first response'
            },
            'benefits': [
                'More engaging conversation experience',
                'Natural AI-to-AI collaboration in real-time',
                'Better handling of conversational interruptions',
                'Immediate visual feedback on progress',
                'Feels like chatting with real people on Slack',
                'Enables true conversation repair mechanics'
            ]
        }


def demonstrate_realtime_improvements():
    """Demonstrate the real-time streaming improvements."""
    print("🚀 REAL-TIME CONVERSATION STREAMING")
    print("=" * 50)
    
    manager = EnhancedCollaborationManager()
    comparison = manager.get_streaming_vs_batch_comparison()
    
    print("\n📊 BATCH vs STREAMING COMPARISON")
    print("-" * 30)
    
    print("\n🐌 OLD BATCH PROCESSING:")
    batch = comparison['batch_processing']
    for key, value in batch.items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
    
    print("\n⚡ NEW STREAMING PROCESSING:")
    streaming = comparison['streaming_processing']
    for key, value in streaming.items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
    
    print("\n🎯 KEY BENEFITS:")
    for benefit in comparison['benefits']:
        print(f"  ✓ {benefit}")
    
    print("\n💡 HOW TO USE:")
    print("  1. Run: python demos/demo_realtime_streaming.py")
    print("  2. Choose option 1 for interactive demo")
    print("  3. Type messages and watch responses stream in real-time")
    print("  4. Try interrupting with 'wait' or 'actually' to see interruption handling")
    print("  5. Ask for clarification to see conversation repair in action")


if __name__ == "__main__":
    demonstrate_realtime_improvements()
