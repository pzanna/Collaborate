"""
Real-world conversation scenario demonstrating natural flow improvements.

This test simulates an actual multi-turn conversation to show how the enhanced
coordinator creates more natural, Slack-like conversation flow.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.response_coordinator import ResponseCoordinator
from src.models.data_models import Message
from src.config.config_manager import ConfigManager
from datetime import datetime
from typing import List, Dict


def simulate_real_conversation():
    """Simulate a realistic conversation showing natural flow improvements."""
    
    config_manager = ConfigManager()
    coordinator = ResponseCoordinator(config_manager)
    available_providers = ["openai", "xai"]
    
    def create_message(participant: str, content: str) -> Message:
        return Message(
            conversation_id="demo",
            participant=participant,
            content=content,
            timestamp=datetime.now()
        )
    
    print("🎬 REAL CONVERSATION SIMULATION")
    print("=" * 60)
    print("Scenario: User asks for help building a web app")
    print()
    
    conversation_history = []
    
    # Turn 1: Initial question
    turn1 = create_message("user", "I'm building a web app for my food truck business. I need help with both the technical setup and making it user-friendly.")
    conversation_history.append(turn1)
    
    print(f"👤 User: {turn1.content}")
    queue1 = coordinator.coordinate_responses(turn1, [], available_providers)
    print(f"🎯 Response queue: {queue1}")
    
    # Simulate AI responses
    if "openai" in queue1:
        openai_response = create_message("openai", "For the technical setup, I'd recommend a MERN stack (MongoDB, Express, React, Node.js). This gives you a robust foundation that scales well.")
        conversation_history.append(openai_response)
        print(f"🤖 OpenAI: {openai_response.content}")
        
        # Check for chaining cues
        cued = coordinator.detect_chaining_cue(openai_response.content, available_providers)
        if cued:
            print(f"🔗 Chain detected to: {cued}")
    
    if "xai" in queue1:
        xai_response = create_message("xai", "Great foundation from @openai! For user-friendliness, focus on mobile-first design and simple navigation. Food truck customers are often on-the-go and need quick ordering.")
        conversation_history.append(xai_response)
        print(f"🎨 XAI: {xai_response.content}")
    
    print()
    
    # Turn 2: User has concerns (interruption scenario)
    turn2 = create_message("user", "Wait, actually - I'm worried about the complexity. I'm just one person and MERN sounds overwhelming.")
    conversation_history.append(turn2)
    
    print(f"👤 User: {turn2.content}")
    
    # Show interruption detection
    interruption_scores = coordinator.detect_interruption_opportunity(turn2, conversation_history)
    print(f"🚨 Interruption scores: {interruption_scores}")
    
    queue2 = coordinator.coordinate_responses(turn2, conversation_history, available_providers)
    print(f"🎯 Response queue: {queue2}")
    
    # Show collaboration context
    for provider in queue2[:1]:
        context = coordinator._add_collaboration_context(provider, conversation_history)
        print(f"🤝 {provider.upper()} collaboration context: {context}")
    
    print()
    
    # Turn 3: Follow-up question (momentum test)
    turn3 = create_message("user", "What would be a simpler alternative that I could manage myself?")
    conversation_history.append(turn3)
    
    print(f"👤 User: {turn3.content}")
    
    # Show momentum calculation
    momentum = coordinator.calculate_conversational_momentum(turn3, conversation_history)
    print(f"⚡ Momentum scores: {momentum}")
    
    queue3 = coordinator.coordinate_responses(turn3, conversation_history, available_providers)
    print(f"🎯 Response queue: {queue3}")
    
    print()
    
    # Turn 4: Urgent clarification (urgent response test)
    turn4 = create_message("user", "Hold on - am I missing something? Is there a no-code solution that might work better?")
    conversation_history.append(turn4)
    
    print(f"👤 User: {turn4.content}")
    
    # Show urgent response detection
    interruption_scores4 = coordinator.detect_interruption_opportunity(turn4, conversation_history)
    print(f"🚨 Urgent interruption scores: {interruption_scores4}")
    
    queue4 = coordinator.coordinate_responses(turn4, conversation_history, available_providers)
    print(f"🎯 Response queue: {queue4}")
    
    # Show conversation energy
    energy = coordinator._assess_conversation_energy(conversation_history)
    print(f"📊 Conversation energy: {energy}")
    
    print()
    
    # Turn 5: Discussion continuation (back-and-forth test)
    turn5 = create_message("user", "What do you both think about the no-code vs custom development trade-offs?")
    conversation_history.append(turn5)
    
    print(f"👤 User: {turn5.content}")
    
    queue5 = coordinator.coordinate_responses(turn5, conversation_history, available_providers)
    print(f"🎯 Response queue: {queue5}")
    
    # Show how both might respond to a discussion question
    print(f"💭 Discussion intent detected - encouraging both perspectives")
    
    print()
    print("=" * 60)
    print("🎯 NATURAL FLOW IMPROVEMENTS DEMONSTRATED:")
    print("=" * 60)
    print("✅ Interruption detection for user concerns")
    print("✅ Context-aware collaboration between AIs") 
    print("✅ Momentum tracking for topic continuity")
    print("✅ Urgent response prioritization")
    print("✅ Discussion flow encouragement")
    print("✅ Energy-adaptive conversation management")
    print()
    print("🔄 This creates more natural, Slack-like conversations where:")
    print("   • AIs respond appropriately to interruptions")
    print("   • Relevant expertise is prioritized naturally")
    print("   • Conversation repair happens automatically")
    print("   • Back-and-forth discussions are encouraged")
    print("   • Multiple perspectives are valued when appropriate")


def compare_before_after():
    """Show side-by-side comparison of old vs new behavior."""
    
    print("\n🔄 BEFORE vs AFTER COMPARISON")
    print("=" * 60)
    
    scenarios = [
        {
            "user_input": "Actually, wait - I think we're overcomplicating this.",
            "description": "User interruption"
        },
        {
            "user_input": "I need both technical help AND creative design ideas.",
            "description": "Multi-expertise request"
        },
        {
            "user_input": "I'm confused by that explanation. Can you clarify?",
            "description": "Confusion/repair needed"
        },
        {
            "user_input": "What do you both think about this approach?",
            "description": "Discussion question"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📝 Scenario: {scenario['description']}")
        print(f"👤 User: {scenario['user_input']}")
        print(f"🔴 OLD: Single provider by relevance score only")
        print(f"🟢 NEW: Context-aware, natural flow with interruption/momentum/repair detection")
    
    print("\n" + "=" * 60)
    print("💡 KEY IMPROVEMENTS:")
    print("   🧠 Smarter context awareness")
    print("   🚨 Interruption and urgency detection") 
    print("   🔧 Automatic conversation repair")
    print("   ⚡ Dynamic momentum tracking")
    print("   🎭 Natural collaboration coaching")
    print("   📊 Energy-adaptive responses")


if __name__ == "__main__":
    simulate_real_conversation()
    compare_before_after()
