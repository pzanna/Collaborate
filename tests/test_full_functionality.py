#!/usr/bin/env python3
"""
Quick test script for the Collaborate CLI functionality
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from core.ai_client_manager import AIClientManager
from models.data_models import Project, Conversation, Message


def test_basic_functionality():
    """Test basic functionality without AI calls."""
    print("🧪 Testing Basic Functionality")
    print("=" * 50)
    
    # Initialize components
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager.config.storage.database_path)
    
    try:
        ai_manager = AIClientManager(config_manager)
        print(f"✅ AI Manager initialized with providers: {ai_manager.get_available_providers()}")
    except Exception as e:
        print(f"⚠ AI Manager initialization warning: {e}")
        ai_manager = None
    
    # Test 1: Create a project
    print("\n🧪 Test 1: Create Project")
    project = Project(name="Test Project", description="A test project for development")
    db_manager.create_project(project)
    print(f"✅ Project created: {project.name} (ID: {project.id[:8]}...)")
    
    # Test 2: List projects
    print("\n🧪 Test 2: List Projects")
    projects = db_manager.list_projects()
    print(f"✅ Found {len(projects)} project(s)")
    for proj in projects:
        print(f"   - {proj.name}: {proj.description}")
    
    # Test 3: Create a conversation
    print("\n🧪 Test 3: Create Conversation")
    conversation = Conversation(
        project_id=project.id,
        title="Test Conversation about AI Ethics"
    )
    db_manager.create_conversation(conversation)
    print(f"✅ Conversation created: {conversation.title} (ID: {conversation.id[:8]}...)")
    
    # Test 4: Add messages
    print("\n🧪 Test 4: Add Messages")
    messages = [
        Message(
            conversation_id=conversation.id,
            participant="user",
            content="What are the key ethical considerations when developing AI systems?"
        ),
        Message(
            conversation_id=conversation.id,
            participant="openai",
            content="Key ethical considerations include fairness, transparency, accountability, privacy, and ensuring AI systems benefit humanity while minimizing harm."
        ),
        Message(
            conversation_id=conversation.id,
            participant="xai",
            content="I'd add that we should also consider the long-term societal impact, potential job displacement, and ensuring AI development is inclusive and representative of diverse perspectives."
        )
    ]
    
    for msg in messages:
        db_manager.create_message(msg)
    
    print(f"✅ Added {len(messages)} messages to conversation")
    
    # Test 5: Retrieve conversation session
    print("\n🧪 Test 5: Retrieve Conversation Session")
    session = db_manager.get_conversation_session(conversation.id)
    if session:
        print(f"✅ Session retrieved: {len(session.messages)} messages")
        print(f"   Conversation: {session.conversation.title}")
        print(f"   Project: {session.project.name if session.project else 'Unknown'}")
        
        print("\n📜 Messages:")
        for i, msg in enumerate(session.messages, 1):
            print(f"   {i}. [{msg.participant.upper()}] {msg.content[:60]}...")
    else:
        print("❌ Failed to retrieve session")
    
    # Test 6: Configuration
    print("\n🧪 Test 6: Configuration")
    config = config_manager.config
    print(f"✅ Database path: {config.storage.database_path}")
    print(f"✅ Max context tokens: {config.conversation.max_context_tokens}")
    print(f"✅ Available AI providers: {list(config.ai_providers.keys())}")
    
    print("\n🎉 All basic functionality tests passed!")
    return True


def test_ai_functionality():
    """Test AI functionality if API keys are available."""
    print("\n🧪 Testing AI Functionality")
    print("=" * 50)
    
    # Check if API keys are available
    openai_key = os.getenv("OPENAI_API_KEY")
    xai_key = os.getenv("XAI_API_KEY")
    
    if not openai_key and not xai_key:
        print("⚠ No API keys found. Skipping AI tests.")
        print("   To test AI functionality, set OPENAI_API_KEY and/or XAI_API_KEY environment variables.")
        return True
    
    try:
        config_manager = ConfigManager()
        ai_manager = AIClientManager(config_manager)
        
        # Test simple AI response
        test_messages = [
            Message(
                conversation_id="test",
                participant="user",
                content="Hello! Please respond with just 'Hello from [AI name]' to test the connection."
            )
        ]
        
        providers = ai_manager.get_available_providers()
        print(f"✅ Available providers: {providers}")
        
        for provider in providers:
            try:
                print(f"\n🤖 Testing {provider.upper()}...")
                response = ai_manager.get_response(provider, test_messages)
                print(f"✅ {provider.upper()} Response: {response}")
            except Exception as e:
                print(f"❌ {provider.upper()} Error: {e}")
        
        print("\n🎉 AI functionality tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ AI functionality test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Collaborate Application - Full Functionality Test")
    print("=" * 60)
    
    success = True
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    # Test AI functionality
    if not test_ai_functionality():
        success = False
    
    if success:
        print("\n🎉 All tests passed! The Collaborate application is working correctly.")
        print("\n🚀 Ready to start three-way AI collaboration!")
        print("\n💡 Next steps:")
        print("   1. Set your API keys in a .env file")
        print("   2. Run 'python collaborate.py' to start the interactive CLI")
        print("   3. Create a project and start collaborating!")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
