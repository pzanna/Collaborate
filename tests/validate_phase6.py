#!/usr/bin/env python3
"""
Phase 6 Test Infrastructure Validation

This script validates that our Phase 6 testing infrastructure is properly
configured and working, without relying on external tools that may have
architecture compatibility issues.
"""

import sys
import os
import traceback
from pathlib import Path
from typing import Dict, Any, List

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def validate_imports():
    """Validate that all required modules can be imported."""
    print("🔍 Validating Phase 6 Test Infrastructure...")
    print("=" * 60)
    
    # Test configuration imports
    try:
        from config.config_manager import ConfigManager
        print("✅ ConfigManager import successful")
    except ImportError as e:
        print(f"❌ ConfigManager import failed: {e}")
        return False
    
    # Test database imports
    try:
        from storage.database import DatabaseManager
        print("✅ DatabaseManager import successful")
    except ImportError as e:
        print(f"❌ DatabaseManager import failed: {e}")
        return False
    
    # Test core imports
    try:
        from core.ai_client_manager import AIClientManager
        print("✅ AIClientManager import successful")
    except ImportError as e:
        print(f"❌ AIClientManager import failed: {e}")
        return False
    
    # Test models imports
    try:
        from models.data_models import Project, Conversation, Message
        print("✅ Data models import successful")
    except ImportError as e:
        print(f"❌ Data models import failed: {e}")
        return False
    
    # Test utility imports
    try:
        from utils.performance import PerformanceMonitor
        print("✅ PerformanceMonitor import successful")
    except ImportError as e:
        print(f"❌ PerformanceMonitor import failed: {e}")
        return False
    
    try:
        from utils.error_handler import ErrorHandler
        print("✅ ErrorHandler import successful")
    except ImportError as e:
        print(f"❌ ErrorHandler import failed: {e}")
        return False
    
    return True

def validate_test_fixtures():
    """Validate that test fixtures work correctly."""
    print("\n🧪 Validating Test Fixtures...")
    print("=" * 60)
    
    try:
        # Test configuration fixture
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        print("✅ ConfigManager fixture creation successful")
        
        # Test database fixture (in-memory)
        from storage.database import DatabaseManager
        db_manager = DatabaseManager(":memory:")
        print("✅ DatabaseManager fixture creation successful")
        
        # Test AI client manager fixture
        ai_manager = AIClientManager(config_manager)
        print("✅ AIClientManager fixture creation successful")
        
        # Test performance monitor fixture
        from utils.performance import PerformanceMonitor
        perf_monitor = PerformanceMonitor()
        print("✅ PerformanceMonitor fixture creation successful")
        
        # Test error handler fixture
        from utils.error_handler import ErrorHandler
        error_handler = ErrorHandler()
        print("✅ ErrorHandler fixture creation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Test fixture validation failed: {e}")
        traceback.print_exc()
        return False

def validate_unit_tests():
    """Validate unit test functionality."""
    print("\n🔬 Validating Unit Test Components...")
    print("=" * 60)
    
    try:
        # Test ConfigManager functionality
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # Test config loading
        assert hasattr(config_manager, 'config')
        assert hasattr(config_manager.config, 'ai_providers')
        print("✅ ConfigManager unit test validation successful")
        
        # Test DatabaseManager functionality
        from storage.database import DatabaseManager
        from models.data_models import Project, Conversation, Message
        
        db_manager = DatabaseManager(":memory:")
        
        # Test project creation
        project = Project(name="Test Project", description="Test")
        created_project = db_manager.create_project(project)
        assert created_project is not None
        print("✅ DatabaseManager unit test validation successful")
        
        # Test AI client manager
        ai_manager = AIClientManager(config_manager)
        providers = ai_manager.get_available_providers()
        assert isinstance(providers, list)
        print("✅ AIClientManager unit test validation successful")
        
        # Test performance monitor
        from utils.performance import PerformanceMonitor
        perf_monitor = PerformanceMonitor()
        
        perf_monitor.start_timer("test_operation")
        import time
        time.sleep(0.01)
        duration = perf_monitor.end_timer("test_operation")
        assert duration > 0
        print("✅ PerformanceMonitor unit test validation successful")
        
        # Test error handler
        from utils.error_handler import ErrorHandler
        error_handler = ErrorHandler()
        
        error_handler.handle_error("test_error", "Test error message")
        assert len(error_handler.recent_errors) > 0
        print("✅ ErrorHandler unit test validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Unit test validation failed: {e}")
        traceback.print_exc()
        return False

def validate_integration_tests():
    """Validate integration test functionality."""
    print("\n🔗 Validating Integration Test Components...")
    print("=" * 60)
    
    try:
        # Test database + models integration
        from storage.database import DatabaseManager
        from models.data_models import Project, Conversation, Message
        
        db_manager = DatabaseManager(":memory:")
        
        # Create project
        project = Project(name="Integration Test", description="Integration test")
        db_manager.create_project(project)
        
        # Create conversation
        conversation = Conversation(
            project_id=project.id,
            title="Integration Test Conversation"
        )
        db_manager.create_conversation(conversation)
        
        # Create message
        message = Message(
            conversation_id=conversation.id,
            participant="user",
            content="Integration test message"
        )
        db_manager.create_message(message)
        
        # Test session retrieval
        session = db_manager.get_conversation_session(conversation.id)
        assert session is not None
        assert len(session.messages) == 1
        print("✅ Database integration test validation successful")
        
        # Test AI client + config integration
        from config.config_manager import ConfigManager
        from core.ai_client_manager import AIClientManager
        
        config_manager = ConfigManager()
        ai_manager = AIClientManager(config_manager)
        
        # Test configuration access
        health = ai_manager.get_provider_health()
        assert isinstance(health, dict)
        print("✅ AI client integration test validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test validation failed: {e}")
        traceback.print_exc()
        return False

def validate_performance_tests():
    """Validate performance test functionality."""
    print("\n⚡ Validating Performance Test Components...")
    print("=" * 60)
    
    try:
        from utils.performance import PerformanceMonitor
        from storage.database import DatabaseManager
        from models.data_models import Project, Conversation, Message
        
        perf_monitor = PerformanceMonitor()
        db_manager = DatabaseManager(":memory:")
        
        # Test performance monitoring
        perf_monitor.start_timer("performance_test")
        
        # Create multiple projects quickly
        for i in range(100):
            project = Project(
                name=f"Performance Test Project {i}",
                description="Performance test"
            )
            db_manager.create_project(project)
        
        duration = perf_monitor.end_timer("performance_test")
        
        # Check results
        stats = perf_monitor.get_stats("performance_test")
        assert stats["count"] == 1
        assert duration > 0
        print("✅ Performance test validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test validation failed: {e}")
        traceback.print_exc()
        return False

def validate_export_functionality():
    """Validate export functionality."""
    print("\n📤 Validating Export Test Components...")
    print("=" * 60)
    
    try:
        from utils.export_manager import ExportManager
        from storage.database import DatabaseManager
        from models.data_models import Project, Conversation, Message
        import tempfile
        
        # Create temporary export directory
        with tempfile.TemporaryDirectory() as temp_dir:
            export_manager = ExportManager(temp_dir)
            db_manager = DatabaseManager(":memory:")
            
            # Create test data
            project = Project(name="Export Test", description="Export test")
            db_manager.create_project(project)
            
            conversation = Conversation(
                project_id=project.id,
                title="Export Test Conversation"
            )
            db_manager.create_conversation(conversation)
            
            message = Message(
                conversation_id=conversation.id,
                participant="user",
                content="Export test message"
            )
            db_manager.create_message(message)
            
            # Test export
            session = db_manager.get_conversation_session(conversation.id)
            assert session is not None
            
            # Test JSON export
            json_path = export_manager.export_conversation(session, "json", "test_export")
            assert Path(json_path).exists()
            print("✅ Export functionality validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Export test validation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("🚀 Phase 6 Testing Infrastructure Validation")
    print("=" * 80)
    
    validation_results = []
    
    # Run all validation tests
    validation_results.append(("Import Validation", validate_imports()))
    validation_results.append(("Test Fixtures", validate_test_fixtures()))
    validation_results.append(("Unit Tests", validate_unit_tests()))
    validation_results.append(("Integration Tests", validate_integration_tests()))
    validation_results.append(("Performance Tests", validate_performance_tests()))
    validation_results.append(("Export Functionality", validate_export_functionality()))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, result in validation_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"Total Tests: {len(validation_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL PHASE 6 TESTING INFRASTRUCTURE VALIDATED SUCCESSFULLY!")
        print("Your testing infrastructure is ready for comprehensive testing.")
    else:
        print(f"\n⚠️  {failed} validation test(s) failed. Please review the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
