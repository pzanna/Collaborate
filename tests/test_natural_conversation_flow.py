"""Test suite for natural conversation flow improvements.

This module tests the enhanced ResponseCoordinator to verify that conversations
flow more naturally compared to the original algorithmic approach.
"""

import pytest
import unittest
from datetime import datetime
from typing import List, Dict
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.response_coordinator import ResponseCoordinator
from src.models.data_models import Message
from src.config.config_manager import ConfigManager


class TestNaturalConversationFlow(unittest.TestCase):
    """Test natural conversation flow improvements."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config manager
        self.config_manager = ConfigManager()
        self.coordinator = ResponseCoordinator(self.config_manager)
        self.available_providers = ["openai", "xai"]

    def create_message(self, participant: str, content: str, conversation_id: str = "test") -> Message:
        """Helper to create test messages."""
        return Message(
            conversation_id=conversation_id,
            participant=participant,
            content=content,
            timestamp=datetime.now()
        )

    def test_interruption_detection(self):
        """Test that interruption opportunities are detected correctly."""
        # Test strong interruption cues
        interruption_msg = self.create_message("user", "Wait, actually I disagree with that approach.")
        context = [
            self.create_message("openai", "I think we should use a linear algorithm."),
            self.create_message("xai", "Yes, linear would be efficient.")
        ]
        
        scores = self.coordinator.detect_interruption_opportunity(interruption_msg, context)
        
        # Both providers should have elevated interruption scores
        self.assertGreater(scores["openai"], 0.25, "OpenAI should have interruption opportunity")
        self.assertGreater(scores["xai"], 0.25, "XAI should have interruption opportunity")
        
        # Test urgent questions
        urgent_msg = self.create_message("user", "Am I wrong? Does that make sense?")
        scores = self.coordinator.detect_interruption_opportunity(urgent_msg, context)
        
        self.assertGreater(scores["openai"], 0.3, "Should detect urgent question")
        self.assertGreater(scores["xai"], 0.3, "Should detect urgent question")

    def test_conversation_repair_detection(self):
        """Test that conversation repair needs are detected."""
        context = [
            self.create_message("openai", "The algorithm complexity is O(n log n)."),
            self.create_message("user", "I don't understand what that means."),
            self.create_message("xai", "Let me explain differently.")
        ]
        
        repair_provider = self.coordinator.detect_conversation_repair_needs(context)
        self.assertEqual(repair_provider, "openai", "Should route repair to original explainer")

    def test_conversational_momentum_calculation(self):
        """Test momentum calculation for natural flow."""
        current_msg = self.create_message("user", "Let's continue discussing the algorithm optimization.")
        context = [
            self.create_message("user", "I need help with algorithm optimization."),
            self.create_message("openai", "Happy to help with optimization techniques."),
            self.create_message("xai", "What type of algorithm are we optimizing?"),
            self.create_message("user", "@openai can you elaborate on that approach?")
        ]
        
        momentum = self.coordinator.calculate_conversational_momentum(current_msg, context)
        
        # OpenAI should have higher momentum due to being mentioned and topic continuity
        self.assertGreater(momentum["openai"], momentum["xai"], 
                          "OpenAI should have higher momentum due to mention and topic match")

    def test_natural_vs_rigid_speaking_queue(self):
        """Compare natural speaking queue with old rigid approach."""
        msg = self.create_message("user", "What are some creative and technical approaches to this problem?")
        context = [
            self.create_message("user", "I'm working on a complex software project."),
            self.create_message("openai", "Here's a technical approach..."),
            self.create_message("xai", "Here's a creative angle...")
        ]
        
        # Test natural queue building
        queue = self.coordinator.coordinate_responses(msg, context, self.available_providers)
        
        # Should allow both providers since both are relevant
        self.assertGreaterEqual(len(queue), 1, "Should have at least one provider")
        
        # Test that close scores result in multiple responses
        self.coordinator.enable_multi_response = True
        queue_multi = self.coordinator.coordinate_responses(msg, context, self.available_providers)
        
        # For a question that's both creative and technical, should potentially get both
        print(f"Natural queue for mixed question: {queue_multi}")

    def test_conversation_energy_assessment(self):
        """Test conversation energy level detection."""
        # High energy conversation
        high_energy_context = [
            self.create_message("user", "Quick question"),
            self.create_message("openai", "Sure"),
            self.create_message("xai", "Yes?"),
            self.create_message("user", "Thanks"),
            self.create_message("openai", "No problem"),
            self.create_message("xai", "Glad to help")
        ]
        
        energy = self.coordinator._assess_conversation_energy(high_energy_context)
        self.assertEqual(energy, "high", "Should detect high energy conversation")
        
        # Low energy conversation
        low_energy_context = [
            self.create_message("user", "I have a complex question about machine learning algorithms and their performance characteristics in distributed systems."),
            self.create_message("openai", "This is a comprehensive topic that involves multiple considerations...")
        ]
        
        energy = self.coordinator._assess_conversation_energy(low_energy_context)
        self.assertEqual(energy, "low", "Should detect low energy conversation")

    def test_collaboration_context_generation(self):
        """Test that collaboration context adapts to conversation flow."""
        history = [
            self.create_message("user", "I need help with performance optimization."),
            self.create_message("openai", "I'd suggest profiling first. @xai, what creative approaches might work?"),
            self.create_message("user", "Yes, let's hear both perspectives.")
        ]
        
        # Test context for XAI (being called upon by OpenAI)
        context = self.coordinator._add_collaboration_context("xai", history)
        
        self.assertIn("openai", context.lower(), "Should reference OpenAI in collaboration context")
        self.assertIn("respond directly", context.lower(), "Should encourage direct response")
        
        print(f"Collaboration context for XAI: {context}")

    def test_scenario_natural_interruption_flow(self):
        """Test a realistic interruption scenario."""
        context = [
            self.create_message("user", "How should I structure this database?"),
            self.create_message("openai", "I recommend a normalized relational structure with proper indexing..."),
        ]
        
        # User interrupts with disagreement
        interruption = self.create_message("user", "Actually, wait - I disagree. NoSQL might be better here.")
        
        queue = self.coordinator.coordinate_responses(interruption, context, self.available_providers)
        
        # Should prioritize response due to interruption cues
        self.assertGreater(len(queue), 0, "Should generate response queue for interruption")
        print(f"Interruption response queue: {queue}")

    def test_scenario_back_and_forth_discussion(self):
        """Test that discussions encourage natural back-and-forth."""
        context = [
            self.create_message("user", "What do you think about AI ethics?"),
            self.create_message("openai", "AI ethics requires careful consideration of bias and fairness."),
            self.create_message("xai", "I agree, but we should also consider creative approaches to transparency."),
        ]
        
        follow_up = self.create_message("user", "Interesting perspectives. Let's discuss this more.")
        
        queue = self.coordinator.coordinate_responses(follow_up, context, self.available_providers)
        
        # For a discussion, should encourage the non-last-speaker to respond
        if context[-1].participant == "xai":
            # OpenAI should be encouraged to respond for back-and-forth
            print(f"Discussion continuation queue: {queue}")

    def test_scenario_multi_response_appropriateness(self):
        """Test when multiple responses are appropriate vs when they're not."""
        # Scenario 1: Simple question - should get one focused response
        simple_context = [
            self.create_message("user", "What's 2+2?")
        ]
        simple_queue = self.coordinator.coordinate_responses(
            simple_context[0], [], self.available_providers
        )
        
        # Scenario 2: Complex question requiring multiple perspectives
        complex_msg = self.create_message(
            "user", 
            "I need both technical implementation details and creative design approaches for this project."
        )
        complex_queue = self.coordinator.coordinate_responses(
            complex_msg, [], self.available_providers
        )
        
        print(f"Simple question queue: {simple_queue}")
        print(f"Complex question queue: {complex_queue}")

    def test_natural_vs_algorithmic_comparison(self):
        """Compare natural flow with purely algorithmic approach."""
        msg = self.create_message("user", "Actually, hold on - I think we're approaching this wrong.")
        context = [
            self.create_message("openai", "Here's a systematic approach to the problem."),
            self.create_message("xai", "Building on that, here's an innovative twist.")
        ]
        
        # Test with natural flow enabled
        self.coordinator.enable_interruptions = True
        natural_queue = self.coordinator.coordinate_responses(msg, context, self.available_providers)
        
        # Test with natural flow disabled (simulate old behavior)
        self.coordinator.enable_interruptions = False
        algorithmic_queue = self.coordinator.coordinate_responses(msg, context, self.available_providers)
        
        print(f"Natural flow queue: {natural_queue}")
        print(f"Algorithmic flow queue: {algorithmic_queue}")
        
        # Natural flow should be more responsive to interruption cues
        # (This would require implementing the disable flag in the actual logic)

    def run_conversation_flow_demo(self):
        """Run a complete conversation flow demo."""
        print("\n=== Natural Conversation Flow Demo ===")
        
        conversation = [
            ("user", "I'm building a web application and need help with both the technical architecture and user experience design."),
            ("openai", "For the technical architecture, I'd recommend a microservices approach with a React frontend and Node.js backend."),
            ("xai", "Great technical foundation! For UX, consider a mobile-first design with intuitive navigation. @openai, how would you handle the API design?"),
            ("user", "Wait, actually - I'm not sure microservices is the right approach for my small team."),
            ("user", "What do you both think about this concern?")
        ]
        
        context = []
        for participant, content in conversation:
            msg = self.create_message(participant, content)
            if participant == "user":
                queue = self.coordinator.coordinate_responses(msg, context, self.available_providers)
                print(f"\nUser: {content}")
                print(f"Response queue: {queue}")
                
                # Show collaboration context for each provider
                for provider in queue:
                    collab_context = self.coordinator._add_collaboration_context(provider, context)
                    if collab_context:
                        print(f"{provider.upper()} collaboration context: {collab_context}")
            
            context.append(msg)


if __name__ == "__main__":
    # Run the demo to see natural flow in action
    test_suite = TestNaturalConversationFlow()
    test_suite.setUp()
    test_suite.run_conversation_flow_demo()
    
    # Run unit tests
    unittest.main(verbosity=2)
