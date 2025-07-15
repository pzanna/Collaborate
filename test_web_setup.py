#!/usr/bin/env python3
"""
Demo script to test the web UI components
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all required components can be imported."""
    print("🧪 Testing component imports...")
    
    try:
        from config.config_manager import ConfigManager
        print("✅ ConfigManager imported successfully")
    except ImportError as e:
        print(f"❌ ConfigManager import failed: {e}")
        return False
    
    try:
        from storage.database import DatabaseManager
        print("✅ DatabaseManager imported successfully")
    except ImportError as e:
        print(f"❌ DatabaseManager import failed: {e}")
        return False
    
    try:
        from core.ai_client_manager import AIClientManager
        print("✅ AIClientManager imported successfully")
    except ImportError as e:
        print(f"❌ AIClientManager import failed: {e}")
        return False
    
    try:
        from core.streaming_coordinator import StreamingResponseCoordinator
        print("✅ StreamingResponseCoordinator imported successfully")
    except ImportError as e:
        print(f"❌ StreamingResponseCoordinator import failed: {e}")
        return False
    
    try:
        import fastapi
        import uvicorn
        print("✅ FastAPI and Uvicorn available")
    except ImportError as e:
        print(f"❌ Web framework imports failed: {e}")
        return False
    
    return True

def test_configuration():
    """Test basic configuration setup."""
    print("\n🔧 Testing configuration...")
    
    try:
        from config.config_manager import ConfigManager
        config = ConfigManager()
        print(f"✅ Configuration loaded successfully")
        print(f"   Database path: {config.config.storage.database_path}")
        print(f"   Export path: {config.config.storage.export_path}")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Collaborate Web UI - Component Test")
    print("=" * 50)
    
    if not test_imports():
        print("\n❌ Import tests failed. Check your environment setup.")
        return 1
    
    if not test_configuration():
        print("\n❌ Configuration tests failed. Check your config files.")
        return 1
    
    print("\n✅ All tests passed! The web UI components should work correctly.")
    print("\n🎯 Next steps:")
    print("1. Start the backend: python web_server.py")
    print("2. Install frontend deps: cd frontend && npm install")
    print("3. Start the frontend: npm start")
    print("4. Open browser: http://localhost:3000")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
