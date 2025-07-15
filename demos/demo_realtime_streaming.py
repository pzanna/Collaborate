#!/usr/bin/env python3
"""
Real-Time Streaming Conversation Demo

Demonstrates real-time chain responses where AI responses appear as they're 
generated, creating a more natural Slack-like conversation experience.
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.ai_client_manager import AIClientManager
from src.core.streaming_coordinator import StreamingResponseCoordinator
from src.core.response_coordinator import ResponseCoordinator
from src.config.config_manager import ConfigManager
from src.storage.database import DatabaseManager
from src.models.data_models import Message, Conversation


class RealTimeConversationInterface:
    """Real-time conversation interface with streaming responses."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager("data/collaborate.db")  # Use correct db_path
        self.ai_manager = AIClientManager(self.config_manager)
        self.response_coordinator = ResponseCoordinator(self.config_manager)
        self.streaming_coordinator = StreamingResponseCoordinator(
            self.config_manager, self.response_coordinator
        )
        
    async def run_streaming_conversation(self, conversation_id: str):
        """Run a conversation with real-time streaming responses."""
        session = self.db_manager.get_conversation_session(conversation_id)
        if not session:
            print("❌ Conversation not found.")
            return
        
        print(f"\n🚀 Starting REAL-TIME conversation: {session.conversation.title}")
        print("=" * 60)
        print("✨ Responses will appear in real-time as AIs think and respond")
        print("Type 'exit' to end, 'history' to see conversation history")
        print("=" * 60)
        
        # Show existing messages
        if session.messages:
            print("\n📜 Conversation History:")
            self.show_messages(session.messages[-5:])  # Show last 5 messages
        
        while True:
            try:
                # Get user input (this would need to be adapted for async)
                user_input = await self.async_input("\n👤 You: ")
                
                if user_input.lower() == 'exit':
                    print("👋 Ending conversation...")
                    break
                
                if user_input.lower() == 'history':
                    session = self.db_manager.get_conversation_session(conversation_id)
                    if session and session.messages:
                        print("\n📜 Full Conversation History:")
                        self.show_messages(session.messages)
                    else:
                        print("📜 No messages in conversation yet.")
                    continue
                
                if not user_input.strip():
                    continue
                
                # Create and save user message
                user_message = Message(
                    conversation_id=conversation_id,
                    participant="user",
                    content=user_input
                )
                self.db_manager.create_message(user_message)
                
                # Get context for AI responses
                session = self.db_manager.get_conversation_session(conversation_id)
                if session:
                    context_messages = session.get_context_messages(
                        self.config_manager.config.conversation.max_context_tokens
                    )
                    
                    # Stream AI responses in real-time
                    await self.stream_ai_responses(user_message, context_messages, conversation_id)
                else:
                    print("❌ Could not load conversation session")
                
            except KeyboardInterrupt:
                print("\n👋 Ending conversation...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def stream_ai_responses(self, user_message: Message, context: List[Message], conversation_id: str):
        """Stream AI responses in real-time."""
        available_providers = self.ai_manager.get_available_providers()
        
        print(f"\n💭 Processing your message...")
        
        # Stream responses with interruption support
        active_responses = {}
        current_provider = None
        
        async for update in self.streaming_coordinator.stream_with_interruption_support(
            user_message, context[:-1], available_providers, self.ai_manager
        ):
            update_type = update['type']
            
            if update_type == 'queue_determined':
                print(f"🎯 {update['message']}")
                
            elif update_type == 'interruption_detected':
                print(f"🚨 {update['message']}")
                
            elif update_type == 'repair_needed':
                print(f"🔧 {update['message']}")
                
            elif update_type == 'provider_starting':
                current_provider = update['provider']
                print(f"\n{update['message']}")
                active_responses[current_provider] = ""
                
            elif update_type == 'response_chunk':
                provider = update['provider']
                chunk = update['chunk']
                
                # Print chunk in real-time
                print(chunk, end='', flush=True)
                active_responses[provider] += chunk
                
            elif update_type == 'provider_completed':
                provider = update['provider']
                response = update['response']
                
                print(f"\n{update['message']}")
                
                # Save complete response to database
                try:
                    ai_message = Message(
                        conversation_id=conversation_id,
                        participant=provider,
                        content=response
                    )
                    self.db_manager.create_message(ai_message)
                    print(f"💾 Saved {provider.upper()} response to database")
                except Exception as e:
                    print(f"⚠️ Error saving response: {e}")
                
            elif update_type == 'chain_detected':
                print(f"\n{update['message']}")
                
            elif update_type == 'queue_updated':
                print(f"📝 {update['message']}")
                
            elif update_type == 'provider_error':
                print(f"\n❌ {update['message']}")
                
            elif update_type == 'conversation_completed':
                print(f"\n{update['message']}")
                
            # Small delay to make streaming visible
            await asyncio.sleep(0.05)
    
    async def async_input(self, prompt: str) -> str:
        """Async version of input() function."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)
    
    def show_messages(self, messages: List[Message]):
        """Display conversation messages."""
        for message in messages:
            timestamp = message.timestamp.strftime("%H:%M:%S")
            
            if message.participant == "user":
                print(f"[{timestamp}] 👤 You: {message.content}")
            else:
                provider_emoji = "🤖" if message.participant == "openai" else "🤖"
                print(f"[{timestamp}] {provider_emoji} {message.participant.upper()}: {message.content}")


async def run_streaming_demo():
    """Run a demonstration of streaming conversation."""
    interface = RealTimeConversationInterface()
    
    print("🚀 REAL-TIME STREAMING CONVERSATION DEMO")
    print("=" * 50)
    print("This demo shows AI responses appearing in real-time as they're generated,")
    print("creating a more natural, Slack-like conversation experience.")
    print("=" * 50)
    
    # Create a demo conversation
    conversation = Conversation(
        project_id="demo-project",
        title="Real-Time Streaming Demo"
    )
    
    interface.db_manager.create_conversation(conversation)
    
    # Run the streaming conversation
    await interface.run_streaming_conversation(conversation.id)


def run_comparison_demo():
    """Run a side-by-side comparison of old vs new response flow."""
    print("\n📊 RESPONSE FLOW COMPARISON")
    print("=" * 40)
    
    interface = RealTimeConversationInterface()
    
    print("🔄 OLD WAY (Batch Processing):")
    print("1. User sends message")
    print("2. System determines all responses")
    print("3. Waits for ALL AIs to complete")
    print("4. Displays all responses at once")
    print("⏱️  User waits ~10-30 seconds for responses")
    
    print("\n✨ NEW WAY (Real-Time Streaming):")
    print("1. User sends message") 
    print("2. System determines response queue")
    print("3. First AI starts responding immediately")
    print("4. Response appears word-by-word as AI thinks")
    print("5. When AI finishes, next AI starts immediately")
    print("6. Chaining cues trigger additional responses instantly")
    print("⚡ User sees progress immediately, feels like live chat")
    
    print("\n🎯 BENEFITS:")
    print("• More engaging and natural conversation flow")
    print("• Immediate feedback and progress indication")
    print("• True conversation chaining with real-time handoffs")
    print("• Better handling of interruptions and clarifications")
    print("• Slack-like real-time conversation experience")


if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Run real-time streaming conversation")
    print("2. Show comparison of old vs new approach")
    
    choice = input("\nEnter choice (1-2): ").strip()
    
    if choice == "1":
        try:
            asyncio.run(run_streaming_demo())
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
    elif choice == "2":
        run_comparison_demo()
    else:
        print("Invalid choice. Please run again and select 1 or 2.")
