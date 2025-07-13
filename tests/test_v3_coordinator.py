#!/usr/bin/env python3
"""Test script for Response Coordinator V3."""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.response_coordinator import ResponseCoordinator
from src.config.config_manager import ConfigManager
from src.models.data_models import Message


def test_v3_workflow():
    """Test the V3 workflow implementation."""
    print("Testing Response Coordinator V3...")
    
    # Initialize coordinator
    config_manager = ConfigManager()
    coordinator = ResponseCoordinator(config_manager)
    
    # Test data
    available_providers = ["openai", "xai"]
    
    # Test 1: Technical question (should favor openai)
    print("\n1. Testing technical question...")
    technical_msg = Message(
        id="test-1",
        conversation_id="test-conv",
        participant="user",
        content="How do I debug a Python function that's throwing an error?",
        timestamp=datetime.now()
    )
    
    result = coordinator.coordinate_responses(technical_msg, [], available_providers)
    print(f"   Result: {result}")
    print(f"   Expected: openai should be first due to technical content")
    
    # Test 2: Creative question (should favor xai)
    print("\n2. Testing creative question...")
    creative_msg = Message(
        id="test-2",
        conversation_id="test-conv",
        participant="user",
        content="I need some creative ideas for a brainstorming session",
        timestamp=datetime.now()
    )
    
    result = coordinator.coordinate_responses(creative_msg, [], available_providers)
    print(f"   Result: {result}")
    print(f"   Expected: xai should be first due to creative content")
    
    # Test 3: Explicit mention
    print("\n3. Testing explicit mention...")
    mention_msg = Message(
        id="test-3",
        conversation_id="test-conv",
        participant="user",
        content="@xai what do you think about this algorithm?",
        timestamp=datetime.now()
    )
    
    result = coordinator.coordinate_responses(mention_msg, [], available_providers)
    print(f"   Result: {result}")
    print(f"   Expected: xai should be first due to @mention")
    
    # Test 4: Chaining cue detection
    print("\n4. Testing chaining cue detection...")
    chain_response = "That's a great question! Your turn, openai."
    cued_provider = coordinator.detect_chaining_cue(chain_response, available_providers)
    print(f"   Detected cue: {cued_provider}")
    print(f"   Expected: openai")
    
    # Test 5: Process AI response and chaining
    print("\n5. Testing AI response processing...")
    next_provider = coordinator.process_ai_response(
        "Here's my analysis. What do you think, xai?",
        "openai", 
        available_providers
    )
    print(f"   Next provider to prepend: {next_provider}")
    print(f"   Expected: xai")
    
    print("\n✅ V3 workflow tests completed!")


if __name__ == "__main__":
    test_v3_workflow()
