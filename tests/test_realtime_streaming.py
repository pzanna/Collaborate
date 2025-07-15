"""Test real-time streaming conversation functionality.

This test validates that the streaming coordinator works correctly and
provides the expected real-time conversation experience.
"""

import pytest
import asyncio
import unittest
from datetime import datetime
from typing import List, Dict
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.streaming_coordinator import StreamingResponseCoordinator
from src.core.response_coordinator import ResponseCoordinator
from src.config.config_manager import ConfigManager
from src.models.data_models import Message


class MockAIClientManager:
    """Mock AI client manager for testing streaming functionality."""
    
    def __init__(self):
        self.providers = ["openai", "xai"]
        
    def get_available_providers(self):
        return self.providers
    
    def get_response(self, provider: str, messages: List[Message], system_prompt: str = "") -> str:
        """Mock response generation."""
        if provider == "openai":
            return "This is a technical response from OpenAI about your question."
        elif provider == "xai":
            return "Here's a creative perspective from XAI on this topic."
        else:
            return f"Mock response from {provider}"
    
    def adapt_system_prompt(self, provider: str, content: str, messages: List[Message], collab_context: str = "") -> str:
        return f"System prompt for {provider} with collaboration context: {collab_context}"


class TestStreamingCoordinator(unittest.TestCase):
    """Test streaming conversation coordinator."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()
        self.response_coordinator = ResponseCoordinator(self.config_manager)
        self.streaming_coordinator = StreamingResponseCoordinator(
            self.config_manager, self.response_coordinator
        )
        self.mock_ai_manager = MockAIClientManager()

    def create_message(self, participant: str, content: str, conversation_id: str = "test") -> Message:
        """Helper to create test messages."""
        return Message(
            conversation_id=conversation_id,
            participant=participant,
            content=content,
            timestamp=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_streaming_conversation_chain(self):
        """Test that streaming conversation chain works correctly."""
        
        # Create test message and context
        user_message = self.create_message("user", "Can you help me with both technical implementation and creative design?")
        context = [
            self.create_message("user", "I'm working on a new project."),
            self.create_message("openai", "I can help with technical aspects."),
            self.create_message("xai", "I can provide creative insights.")
        ]
        
        available_providers = ["openai", "xai"]
        
        # Track streaming updates
        updates = []
        
        async for update in self.streaming_coordinator.stream_conversation_chain(
            user_message, context, available_providers, self.mock_ai_manager
        ):
            updates.append(update)
            # Limit updates to avoid infinite loops in tests
            if len(updates) > 20:
                break
        
        # Validate expected update types
        update_types = [update['type'] for update in updates]
        
        self.assertIn('queue_determined', update_types, "Should determine response queue")
        self.assertIn('provider_starting', update_types, "Should start provider response")
        self.assertIn('response_chunk', update_types, "Should stream response chunks")
        self.assertIn('provider_completed', update_types, "Should complete provider response")
        self.assertIn('conversation_completed', update_types, "Should complete conversation")
        
        print(f"✅ Streaming test completed with {len(updates)} updates")

    @pytest.mark.asyncio
    async def test_interruption_support(self):
        """Test streaming with interruption detection."""
        
        # Create interruption message
        user_message = self.create_message("user", "Wait, actually I disagree with that approach.")
        context = [
            self.create_message("openai", "I recommend using a microservices architecture."),
            self.create_message("xai", "That's a solid technical approach.")
        ]
        
        available_providers = ["openai", "xai"]
        
        # Track interruption detection
        interruption_detected = False
        
        async for update in self.streaming_coordinator.stream_with_interruption_support(
            user_message, context, available_providers, self.mock_ai_manager
        ):
            if update['type'] == 'interruption_detected':
                interruption_detected = True
                providers = update['providers']
                scores = update['scores']
                
                print(f"Interruption detected for providers: {providers}")
                print(f"Interruption scores: {scores}")
                
                # Should detect interruption for both providers
                self.assertTrue(len(providers) > 0, "Should detect interruption opportunities")
                
            # Limit updates for testing
            if update['type'] == 'conversation_completed':
                break
        
        self.assertTrue(interruption_detected, "Should detect interruption in message")
        print("✅ Interruption detection test passed")

    @pytest.mark.asyncio
    async def test_conversation_repair_routing(self):
        """Test conversation repair detection and routing."""
        
        # Create repair scenario
        user_message = self.create_message("user", "I don't understand what you meant by that.")
        context = [
            self.create_message("user", "How does machine learning work?"),
            self.create_message("openai", "Machine learning uses complex algorithms to analyze patterns in data."),
            self.create_message("user", "I don't understand what you meant by that.")
        ]
        
        available_providers = ["openai", "xai"]
        
        repair_detected = False
        
        async for update in self.streaming_coordinator.stream_with_interruption_support(
            user_message, context, available_providers, self.mock_ai_manager
        ):
            if update['type'] == 'repair_needed':
                repair_detected = True
                repair_provider = update['provider']
                
                print(f"Repair routed to: {repair_provider}")
                
                # Should route repair to OpenAI (who made the confusing statement)
                self.assertEqual(repair_provider, "openai", "Should route repair to original explainer")
                
            if update['type'] == 'conversation_completed':
                break
        
        self.assertTrue(repair_detected, "Should detect conversation repair need")
        print("✅ Conversation repair test passed")

    @pytest.mark.asyncio
    async def test_chaining_detection(self):
        """Test AI-to-AI chaining detection in streaming."""
        
        # This test would need a mock that returns responses with chaining cues
        user_message = self.create_message("user", "What do you both think about this approach?")
        context = []
        
        available_providers = ["openai", "xai"]
        
        # Override mock to include chaining cue
        original_response = self.mock_ai_manager.get_response
        
        def mock_response_with_cue(provider, messages, system_prompt=None):
            if provider == "openai":
                return "That's an interesting approach. @xai, what's your creative take on this?"
            else:
                return "I agree with OpenAI's technical analysis."
        
        self.mock_ai_manager.get_response = mock_response_with_cue
        
        chain_detected = False
        
        async for update in self.streaming_coordinator.stream_conversation_chain(
            user_message, context, available_providers, self.mock_ai_manager
        ):
            if update['type'] == 'chain_detected':
                chain_detected = True
                from_provider = update['from_provider']
                to_provider = update['to_provider']
                
                print(f"Chain detected: {from_provider} → {to_provider}")
                
                self.assertEqual(from_provider, "openai", "Should detect chain from OpenAI")
                self.assertEqual(to_provider, "xai", "Should detect chain to XAI")
                
            if update['type'] == 'conversation_completed':
                break
        
        # Restore original mock
        self.mock_ai_manager.get_response = original_response
        
        self.assertTrue(chain_detected, "Should detect chaining cue")
        print("✅ Chaining detection test passed")

    def test_stream_status_tracking(self):
        """Test stream status tracking functionality."""
        
        status = self.streaming_coordinator.get_stream_status()
        
        self.assertIn('active_streams', status)
        self.assertIn('stream_ids', status)
        self.assertIn('timestamp', status)
        
        # Initially no active streams
        self.assertEqual(status['active_streams'], 0)
        self.assertEqual(len(status['stream_ids']), 0)
        
        print("✅ Stream status tracking test passed")

    def run_streaming_performance_test(self):
        """Test streaming performance and timing."""
        import time
        
        print("\n🚀 STREAMING PERFORMANCE TEST")
        print("-" * 30)
        
        # Test different message types
        test_messages = [
            ("Simple question", "What is Python?"),
            ("Technical request", "Help me debug this algorithm implementation"),
            ("Creative request", "Brainstorm innovative approaches to this problem"),
            ("Interruption", "Wait, actually that's not what I meant"),
            ("Clarification", "I don't understand what you said about algorithms")
        ]
        
        for test_name, content in test_messages:
            start_time = time.time()
            
            user_message = self.create_message("user", content)
            context = []
            
            # Run basic coordination (non-streaming for timing)
            queue = self.response_coordinator.coordinate_responses(
                user_message, context, ["openai", "xai"]
            )
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            
            print(f"{test_name}: {duration:.2f}ms → Queue: {queue}")
        
        print("✅ Performance test completed")


async def run_async_tests():
    """Run async tests."""
    test_suite = TestStreamingCoordinator()
    test_suite.setUp()
    
    print("🧪 Running Streaming Coordinator Tests")
    print("=" * 40)
    
    await test_suite.test_streaming_conversation_chain()
    await test_suite.test_interruption_support()
    await test_suite.test_conversation_repair_routing()
    await test_suite.test_chaining_detection()
    
    test_suite.test_stream_status_tracking()
    test_suite.run_streaming_performance_test()
    
    print("\n🎉 All streaming tests completed successfully!")


if __name__ == "__main__":
    # Run async tests
    asyncio.run(run_async_tests())
