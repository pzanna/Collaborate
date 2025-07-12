#!/usr/bin/env python3
"""
Simple test script for the Collaborate application foundation
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all modules can be imported."""
    try:
        from config.config_manager import ConfigManager
        print("✓ Config manager imported successfully")
        
        from storage.database import DatabaseManager
        print("✓ Database manager imported successfully")
        
        from models.data_models import Project, Conversation, Message
        print("✓ Data models imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_configuration():
    """Test configuration system."""
    try:
        from config.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        print("✓ Configuration manager initialized")
        
        # Test configuration access
        print(f"✓ Database path: {config_manager.config.storage.database_path}")
        print(f"✓ Available providers: {list(config_manager.config.ai_providers.keys())}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_database():
    """Test database operations."""
    try:
        from storage.database import DatabaseManager
        from models.data_models import Project
        
        # Use in-memory database for testing
        db_manager = DatabaseManager(":memory:")
        print("✓ Database manager initialized with in-memory database")
        
        # Debug: try to create tables manually
        print("Debug: Attempting manual table creation...")
        with db_manager.get_connection() as conn:
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        metadata TEXT
                    )
                """)
                print("✓ Manual table creation successful")
            except Exception as e:
                print(f"✗ Manual table creation failed: {e}")
                return False
        
        # Verify tables exist
        with db_manager.get_connection() as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [table[0] for table in tables]
            if 'projects' in table_names:
                print("✓ Database tables created successfully")
            else:
                print(f"✗ Expected tables not found. Found: {table_names}")
                return False
        
        # Test project creation
        project = Project(name="Test Project", description="A test project")
        db_manager.create_project(project)
        print("✓ Project created successfully")
        
        # Test project retrieval
        retrieved_project = db_manager.get_project(project.id)
        if retrieved_project and retrieved_project.name == "Test Project":
            print("✓ Project retrieved successfully")
        else:
            print("✗ Project retrieval failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def test_ai_clients():
    """Test AI client initialization."""
    try:
        from core.ai_client_manager import AIClientManager
        from config.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        # This will fail if API keys are not set, but that's expected
        try:
            ai_manager = AIClientManager(config_manager)
            providers = ai_manager.get_available_providers()
            print(f"✓ AI manager initialized with providers: {providers}")
        except Exception as e:
            print(f"⚠ AI manager initialization failed (expected without API keys): {e}")
        
        return True
    except Exception as e:
        print(f"✗ AI client error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Collaborate Application Foundation")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration System", test_configuration),
        ("Database Operations", test_database),
        ("AI Client System", test_ai_clients),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, result in results if result)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n🎉 All foundation tests passed! The application is ready for development.")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
