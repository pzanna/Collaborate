#!/usr/bin/env python3
"""
Test export functionality
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.config_manager import ConfigManager
from storage.database import DatabaseManager
from models.data_models import Project, Conversation, Message
from utils.export_manager import ExportManager


def test_export_functionality():
    """Test the export functionality."""
    print("🧪 Testing Export Functionality")
    print("=" * 50)
    
    # Initialize components
    config_manager = ConfigManager()
    db_manager = DatabaseManager(":memory:")  # Use in-memory database for testing
    export_manager = ExportManager("test_exports")
    
    # Create test data
    print("\n🧪 Test 1: Create Test Data")
    project = Project(name="Export Test Project", description="Testing export functionality")
    db_manager.create_project(project)
    print(f"✅ Project created: {project.name}")
    
    conversation = Conversation(
        project_id=project.id,
        title="Sample AI Ethics Discussion"
    )
    db_manager.create_conversation(conversation)
    print(f"✅ Conversation created: {conversation.title}")
    
    # Add test messages
    messages = [
        Message(
            conversation_id=conversation.id,
            participant="user",
            content="What are the main ethical considerations when developing AI systems?"
        ),
        Message(
            conversation_id=conversation.id,
            participant="openai",
            content="Key ethical considerations include fairness, transparency, accountability, privacy protection, and ensuring AI systems benefit humanity while minimizing potential harm."
        ),
        Message(
            conversation_id=conversation.id,
            participant="xai",
            content="I'd add that we should also consider the long-term societal impact, potential job displacement, algorithmic bias, and ensuring AI development is inclusive and representative of diverse perspectives."
        ),
        Message(
            conversation_id=conversation.id,
            participant="user",
            content="How can we ensure transparency in AI decision-making?"
        ),
        Message(
            conversation_id=conversation.id,
            participant="openai",
            content="Transparency can be achieved through explainable AI techniques, clear documentation of model capabilities and limitations, open-source development where possible, and providing users with insights into how decisions are made."
        )
    ]
    
    for msg in messages:
        db_manager.create_message(msg)
    
    print(f"✅ Added {len(messages)} test messages")
    
    # Get conversation session
    session = db_manager.get_conversation_session(conversation.id)
    if not session:
        print("❌ Failed to retrieve conversation session")
        return False
    
    print(f"✅ Session retrieved with {len(session.messages)} messages")
    
    # Test each export format
    formats = export_manager.get_export_formats()
    print(f"\n🧪 Test 2: Export Formats Available: {formats}")
    
    for format_type in formats:
        try:
            print(f"\n📤 Testing {format_type.upper()} export...")
            filepath = export_manager.export_conversation(session, format_type, f"test_{format_type}")
            
            if Path(filepath).exists():
                file_size = Path(filepath).stat().st_size
                print(f"✅ {format_type.upper()} export successful: {filepath} ({file_size} bytes)")
            else:
                print(f"❌ {format_type.upper()} export failed: File not created")
                
        except Exception as e:
            print(f"❌ {format_type.upper()} export failed: {e}")
    
    # Test list exports
    print(f"\n🧪 Test 3: List Exports")
    exports = export_manager.list_exports()
    print(f"✅ Found {len(exports)} exported files:")
    for export in exports:
        print(f"   - {export['filename']} ({export['format']}, {export['size']} bytes)")
    
    print("\n🎉 Export functionality tests completed!")
    return True


if __name__ == "__main__":
    try:
        success = test_export_functionality()
        if success:
            print("\n✅ All export tests passed!")
        else:
            print("\n❌ Some export tests failed!")
    except Exception as e:
        print(f"\n❌ Export test failed with error: {e}")
        import traceback
        traceback.print_exc()
