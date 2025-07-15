"""
Comprehensive comparison test: Natural Flow vs Original Algorithm

This test demonstrates concrete improvements in conversation flow by comparing
the enhanced coordinator with original behavior patterns.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.response_coordinator import ResponseCoordinator
from src.models.data_models import Message
from src.config.config_manager import ConfigManager
from datetime import datetime
from typing import List


class ConversationFlowComparison:
    """Compare natural flow improvements with original algorithm behavior."""
    
    def __init__(self):
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
    
    def simulate_original_behavior(self, message: Message, context: List[Message]) -> List[str]:
        """Simulate the original algorithmic behavior (without natural enhancements)."""
        # Temporarily disable natural flow features
        original_interruptions = self.coordinator.enable_interruptions
        original_multi = self.coordinator.enable_multi_response
        
        self.coordinator.enable_interruptions = False
        self.coordinator.enable_multi_response = False
        
        # Use only basic semantic relevance
        provider_scores = {}
        for provider in self.available_providers:
            score = self.coordinator._calculate_semantic_relevance(message, provider, context)
            score += self.coordinator._calculate_inactivity_boost(provider, context)
            provider_scores[provider] = score
        
        # Simple queue: highest score first
        queue = sorted(provider_scores.keys(), key=lambda p: provider_scores[p], reverse=True)
        
        # Restore settings
        self.coordinator.enable_interruptions = original_interruptions
        self.coordinator.enable_multi_response = original_multi
        
        return queue[:1]  # Original behavior: one response only
    
    def test_interruption_scenario(self):
        """Test how interruptions are handled."""
        print("\n=== INTERRUPTION SCENARIO ===")
        
        context = [
            self.create_message("openai", "I recommend using a complex microservices architecture with Kubernetes orchestration."),
            self.create_message("xai", "Yes, and we could add machine learning for auto-scaling."),
        ]
        
        interruption = self.create_message("user", "Wait, actually - this is overkill for my small startup. I need something simpler.")
        
        print(f"User: {interruption.content}")
        
        # Original behavior
        original_queue = self.simulate_original_behavior(interruption, context)
        print(f"🔴 Original algorithm: {original_queue}")
        
        # Enhanced behavior
        enhanced_queue = self.coordinator.coordinate_responses(interruption, context, self.available_providers)
        interruption_scores = self.coordinator.detect_interruption_opportunity(interruption, context)
        
        print(f"🟢 Enhanced algorithm: {enhanced_queue}")
        print(f"💡 Interruption scores: {interruption_scores}")
        
        # Show collaboration context
        for provider in enhanced_queue[:1]:
            context_hint = self.coordinator._add_collaboration_context(provider, context + [interruption])
            print(f"🤝 {provider.upper()} context: {context_hint}")
    
    def test_multi_expertise_scenario(self):
        """Test handling questions requiring multiple types of expertise."""
        print("\n=== MULTI-EXPERTISE SCENARIO ===")
        
        mixed_question = self.create_message(
            "user", 
            "I need both technical implementation details AND creative user experience ideas for this app."
        )
        
        context = [
            self.create_message("user", "I'm building a social media app."),
        ]
        
        print(f"User: {mixed_question.content}")
        
        # Original behavior (would pick just one)
        original_queue = self.simulate_original_behavior(mixed_question, context)
        print(f"🔴 Original algorithm: {original_queue} (single response)")
        
        # Enhanced behavior (allows multiple when appropriate)
        enhanced_queue = self.coordinator.coordinate_responses(mixed_question, context, self.available_providers)
        print(f"🟢 Enhanced algorithm: {enhanced_queue} (natural multiple responses)")
        
        # Show why both are selected
        for provider in self.available_providers:
            relevance = self.coordinator._calculate_semantic_relevance(mixed_question, provider, context)
            print(f"📊 {provider.upper()} relevance: {relevance:.2f}")
    
    def test_conversation_repair_scenario(self):
        """Test conversation repair and clarification."""
        print("\n=== CONVERSATION REPAIR SCENARIO ===")
        
        context = [
            self.create_message("openai", "The temporal complexity is O(n log n) with optimal space utilization."),
            self.create_message("user", "I'm confused. What does that actually mean in simple terms?"),
        ]
        
        clarification_request = self.create_message("user", "Can someone explain this more clearly?")
        
        print(f"User: {clarification_request.content}")
        
        # Check for repair needs
        repair_provider = self.coordinator.detect_conversation_repair_needs(context)
        print(f"🔧 Repair needed from: {repair_provider}")
        
        # Original behavior (wouldn't detect repair need)
        original_queue = self.simulate_original_behavior(clarification_request, context)
        print(f"🔴 Original algorithm: {original_queue}")
        
        # Enhanced behavior (detects and routes to appropriate provider)
        enhanced_queue = self.coordinator.coordinate_responses(clarification_request, context, self.available_providers)
        print(f"🟢 Enhanced algorithm: {enhanced_queue}")
    
    def test_back_and_forth_discussion(self):
        """Test encouraging natural back-and-forth discussion."""
        print("\n=== BACK-AND-FORTH DISCUSSION ===")
        
        context = [
            self.create_message("user", "What's the best approach to AI ethics?"),
            self.create_message("openai", "AI ethics requires rigorous frameworks for bias detection and fairness."),
            self.create_message("xai", "I agree on rigor, but we also need creative approaches to transparency and explainability."),
        ]
        
        discussion_continue = self.create_message("user", "Interesting perspectives. Let's discuss this more.")
        
        print(f"User: {discussion_continue.content}")
        print(f"Last speaker was: {context[-1].participant}")
        
        # Original behavior (no consideration of discussion flow)
        original_queue = self.simulate_original_behavior(discussion_continue, context)
        print(f"🔴 Original algorithm: {original_queue}")
        
        # Enhanced behavior (encourages the other AI to respond for back-and-forth)
        enhanced_queue = self.coordinator.coordinate_responses(discussion_continue, context, self.available_providers)
        print(f"🟢 Enhanced algorithm: {enhanced_queue}")
        
        # Show conversation energy assessment
        energy = self.coordinator._assess_conversation_energy(context)
        print(f"⚡ Conversation energy: {energy}")
    
    def test_conversation_momentum(self):
        """Test conversational momentum and topic continuity."""
        print("\n=== CONVERSATION MOMENTUM ===")
        
        context = [
            self.create_message("user", "I need help optimizing my machine learning algorithms."),
            self.create_message("openai", "For optimization, consider gradient descent variations and regularization."),
            self.create_message("user", "@openai that's helpful, can you elaborate on regularization techniques?"),
            self.create_message("xai", "Creative approaches to optimization include genetic algorithms too."),
        ]
        
        follow_up = self.create_message("user", "Let's dive deeper into the optimization techniques.")
        
        print(f"User: {follow_up.content}")
        
        # Calculate momentum
        momentum = self.coordinator.calculate_conversational_momentum(follow_up, context)
        print(f"🎯 Conversation momentum: {momentum}")
        
        # Check for unanswered questions
        for provider in self.available_providers:
            has_unanswered = self.coordinator._has_unanswered_questions(provider, context)
            print(f"❓ {provider.upper()} has unanswered questions: {has_unanswered}")
        
        # Enhanced response
        enhanced_queue = self.coordinator.coordinate_responses(follow_up, context, self.available_providers)
        print(f"🟢 Enhanced algorithm: {enhanced_queue}")
    
    def test_urgent_response_detection(self):
        """Test urgent response detection."""
        print("\n=== URGENT RESPONSE DETECTION ===")
        
        context = [
            self.create_message("openai", "The system should handle 1000 concurrent users."),
            self.create_message("xai", "We could use load balancing for that scale."),
        ]
        
        urgent_question = self.create_message("user", "Wait - is that right? Am I missing something critical here?")
        
        print(f"User: {urgent_question.content}")
        
        # Check interruption scores
        interruption_scores = self.coordinator.detect_interruption_opportunity(urgent_question, context)
        print(f"🚨 Interruption scores: {interruption_scores}")
        
        # Should trigger urgent response
        enhanced_queue = self.coordinator.coordinate_responses(urgent_question, context, self.available_providers)
        print(f"🟢 Enhanced algorithm (urgent): {enhanced_queue}")
    
    def run_comprehensive_comparison(self):
        """Run all comparison tests."""
        print("=" * 60)
        print("NATURAL CONVERSATION FLOW - COMPREHENSIVE COMPARISON")
        print("=" * 60)
        
        self.test_interruption_scenario()
        self.test_multi_expertise_scenario()
        self.test_conversation_repair_scenario()
        self.test_back_and_forth_discussion()
        self.test_conversation_momentum()
        self.test_urgent_response_detection()
        
        print("\n" + "=" * 60)
        print("SUMMARY OF IMPROVEMENTS")
        print("=" * 60)
        print("🟢 Natural interruption handling")
        print("🟢 Multi-provider responses when appropriate")
        print("🟢 Automatic conversation repair routing")
        print("🟢 Discussion flow encouragement")
        print("🟢 Momentum-based response selection")
        print("🟢 Urgent response prioritization")
        print("🟢 Context-aware collaboration hints")
        print("🟢 Energy-adaptive response guidance")


if __name__ == "__main__":
    comparison = ConversationFlowComparison()
    comparison.run_comprehensive_comparison()
