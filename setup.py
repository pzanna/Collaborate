#!/usr/bin/env python3
"""
Setup script for the Collaborate application
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create a .env file for API keys."""
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("🔧 Creating .env file for API keys...")
    
    # Copy from .env.example
    example_file = Path(".env.example")
    if example_file.exists():
        with open(example_file, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ .env file created from template")
        print("📝 Please edit .env and add your API keys:")
        print("   - OPENAI_API_KEY=your_openai_key_here")
        print("   - XAI_API_KEY=your_xai_key_here")
    else:
        print("❌ .env.example file not found")

def create_directories():
    """Create necessary directories."""
    directories = ["data", "logs", "exports"]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {dir_name}")
        else:
            print(f"✅ Directory already exists: {dir_name}")

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        ("pydantic", "pydantic"),
        ("openai", "openai"), 
        ("xai-sdk", "xai_sdk"),
        ("python-dotenv", "dotenv"),
        ("pyyaml", "yaml")
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - NOT INSTALLED")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install them with: pip install -r requirements.txt")
        return False
    
    return True

def test_foundation():
    """Test the basic foundation."""
    print("🧪 Testing foundation...")
    
    try:
        # Add src directory to path
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from config.config_manager import ConfigManager
        from storage.database import DatabaseManager
        
        # Test configuration
        config_manager = ConfigManager()
        print("✅ Configuration system working")
        
        # Test database
        db_manager = DatabaseManager(":memory:")
        print("✅ Database system working")
        
        return True
        
    except Exception as e:
        print(f"❌ Foundation test failed: {e}")
        return False

def main():
    """Run setup process."""
    print("🚀 Collaborate Application Setup")
    print("=" * 40)
    
    success = True
    
    # Step 1: Check dependencies
    if not check_dependencies():
        success = False
    
    # Step 2: Create directories
    print("\n📁 Creating directories...")
    create_directories()
    
    # Step 3: Create .env file
    print("\n🔐 Setting up environment...")
    create_env_file()
    
    # Step 4: Test foundation
    print("\n🧪 Testing foundation...")
    if not test_foundation():
        success = False
    
    # Step 5: Summary
    print("\n" + "=" * 40)
    if success:
        print("🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Edit .env file and add your API keys")
        print("2. Run 'python test_full_functionality.py' to test everything")
        print("3. Run 'python collaborate.py' to start the application")
        print("\n💡 Tip: You can also run 'python run_collaborate.py' as a shortcut")
    else:
        print("❌ Setup completed with errors")
        print("📋 Please fix the issues above before proceeding")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
