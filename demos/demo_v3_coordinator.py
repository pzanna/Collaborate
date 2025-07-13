#!/usr/bin/env python3
"""Demo script showcasing Response Coordinator V3 workflow capabilities."""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.response_coordinator import ResponseCoordinator
from src.config.config_manager import ConfigManager
from src.models.data_models import Message


def create_message(participant: str, content: str, msg_id: str, 
                  conversation_id: str = "demo-conv") -> Message:
    """Helper to create test messages."""
    return Message(
        id=msg_id,
        conversation_id=conversation_id,
        participant=participant,
        content=content,
        timestamp=datetime.now()
    )


def demo_v3_workflow():
    """Comprehensive demo of V3 workflow features."""
    print("🚀 Response Coordinator V3 Workflow Demo")
    print("=" * 50)
    
    # Initialize coordinator
    config_manager = ConfigManager()
    coordinator = ResponseCoordinator(config_manager)
    available_providers = ["openai", "xai"]
    
    # Show current configuration
    print(f"📋 Configuration: {coordinator.get_configuration()}")
    print()
    
    # Demo conversation context
    context = []
    
    # Scenario 1: Technical question with semantic relevance
    print("🔧 Scenario 1: Technical Question")
    print("-" * 30)
    user_msg = create_message(
        "user", 
        "I'm getting a syntax error in my Python code. Can you help me debug it?",
        "msg-1"
    )
    
    queue = coordinator.coordinate_responses(user_msg, context, available_providers)
    print(f"User: {user_msg.content}")
    print(f"Speaking queue: {queue}")
    print(f"✅ OpenAI prioritized due to technical keywords\n")
    
    # Simulate OpenAI response with chaining cue
    openai_response = create_message(
        "openai",
        "I can help you debug that! Let me analyze the error. What do you think, xai?",
        "msg-2"
    )
    context.extend([user_msg, openai_response])
    
    # Detect chaining cue
    next_cued = coordinator.process_ai_response(
        openai_response.content, "openai", available_providers
    )
    print(f"🔗 OpenAI response: {openai_response.content}")
    print(f"Chaining cue detected: {next_cued}")
    if next_cued:
        coordinator.update_speaking_queue(next_cued)
        print(f"Updated queue for next turn: [{next_cued}] + normal queue\n")
    
    # Scenario 2: Creative brainstorming  
    print("🎨 Scenario 2: Creative Brainstorming")
    print("-" * 30)
    user_msg2 = create_message(
        "user",
        "I need innovative ideas for a marketing campaign. Let's brainstorm!",
        "msg-3"
    )
    
    queue = coordinator.coordinate_responses(user_msg2, context, available_providers)
    print(f"User: {user_msg2.content}")
    print(f"Speaking queue: {queue}")
    print(f"✅ XAI prioritized due to creative keywords\n")
    
    # Scenario 3: Explicit mention override
    print("📢 Scenario 3: Explicit @Mention")
    print("-" * 30)
    user_msg3 = create_message(
        "user",
        "@openai can you review this creative strategy that was just proposed?",
        "msg-4"
    )
    
    queue = coordinator.coordinate_responses(user_msg3, context, available_providers)
    print(f"User: {user_msg3.content}")
    print(f"Speaking queue: {queue}")
    print(f"✅ OpenAI first due to @mention, despite creative content\n")
    
    # Scenario 4: Inactivity boost simulation
    print("😴 Scenario 4: Inactivity Boost")
    print("-" * 30)
    
    # Create context where OpenAI hasn't spoken for several turns
    inactive_context = [
        create_message("user", "Question 1", "m1"),
        create_message("xai", "XAI response 1", "m2"),
        create_message("user", "Question 2", "m3"),
        create_message("xai", "XAI response 2", "m4"), 
        create_message("user", "Question 3", "m5"),
        create_message("xai", "XAI response 3", "m6"),
        create_message("user", "Question 4", "m7"),
        create_message("xai", "XAI response 4", "m8"),
    ]
    
    user_msg4 = create_message(
        "user",
        "General question that could go to either provider",
        "msg-8"
    )
    
    queue = coordinator.coordinate_responses(user_msg4, inactive_context, available_providers)
    print(f"User: {user_msg4.content}")
    print(f"Speaking queue: {queue}")
    print(f"✅ OpenAI boosted due to inactivity (hasn't spoken in {coordinator.inactivity_turns}+ turns)\n")
    
    # Scenario 5: Veto system demonstration
    print("🚫 Scenario 5: Veto System")
    print("-" * 30)
    
    # Create repetitive context to trigger veto
    repetitive_msg = create_message(
        "user",
        "I'm getting a syntax error in my Python code. Can you help debug it?",  # Very similar to msg-1
        "msg-9"
    )
    
    queue = coordinator.coordinate_responses(repetitive_msg, context, available_providers)
    print(f"User: {repetitive_msg.content}")
    print(f"Speaking queue: {queue}")
    print(f"✅ Repetition check may affect provider selection\n")
    
    # Show statistics simulation
    print("📊 Scenario 6: Configuration & Stats")
    print("-" * 30)
    
    # Mock conversation session for stats
    mock_messages = [
        create_message("user", "Question 1", "s1"),
        create_message("openai", "OpenAI response 1", "s2"),
        create_message("user", "Question 2", "s3"),  
        create_message("xai", "XAI response 1", "s4"),
        create_message("user", "Question 3", "s5"),
        create_message("openai", "OpenAI response 2", "s6"),
    ]
    
    from src.models.data_models import ConversationSession, Conversation, Project
    
    mock_project = Project(name="Demo Project", description="Demo project for V3 coordinator")
    mock_conversation = Conversation(
        project_id=mock_project.id,
        title="Demo Session"
    )
    mock_session = ConversationSession(
        conversation=mock_conversation,
        messages=mock_messages,
        project=mock_project
    )
    
    stats = coordinator.get_response_stats(mock_session)
    print(f"Conversation stats: {stats}")
    
    # Update settings demo
    print(f"\nCurrent threshold: {coordinator.base_threshold}")
    coordinator.update_settings(base_threshold=0.25, baton_bonus=0.6)
    print(f"Updated threshold: {coordinator.base_threshold}")
    print(f"Updated baton bonus: {coordinator.baton_bonus}")
    
    print("\n🎉 V3 Workflow Demo Complete!")
    print("=" * 50)
    print("Key V3 Features Demonstrated:")
    print("• Intent classification and semantic relevance")
    print("• Provider profiles with keyword matching")
    print("• Inactivity boost for re-engaging silent providers")
    print("• Baton bonus for @mentions and cues")
    print("• Veto system for repetition and context limits") 
    print("• Chaining cue detection for natural conversation flow")
    print("• Speaking queue management")


if __name__ == "__main__":
    demo_v3_workflow()
