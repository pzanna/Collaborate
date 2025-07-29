#!/usr/bin/env python3
"""
Test script for the Authentication Service
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from main import app
    from database import create_db_and_tables
    
    print("✅ Authentication Service imports successful!")
    print("✅ All dependencies resolved")
    
    # Test database creation
    create_db_and_tables()
    print("✅ Database tables created successfully")
    
    print("\n🎉 Authentication Service is ready!")
    print("To start the service, run:")
    print("  cd services/auth-service")
    print("  python -m uvicorn src.main:app --host 0.0.0.0 --port 8013 --reload")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install the required dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
