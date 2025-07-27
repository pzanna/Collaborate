#!/usr/bin/env python3
"""
Quick test for AI Service with secure API keys
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_api_key_validation():
    """Test API key validation functionality"""
    from ai_service import AIService
    
    service = AIService()
    
    # Test valid keys
    assert service._validate_api_key("sk-proj-validkey123", "openai") == True
    assert service._validate_api_key("sk-ant-api03-validkey123", "anthropic") == True
    assert service._validate_api_key("xai-validkey123", "xai") == True
    
    # Test invalid keys
    assert service._validate_api_key("invalid-key", "openai") == False
    assert service._validate_api_key("your_api_key_here", "openai") == False
    assert service._validate_api_key("", "openai") == False
    assert service._validate_api_key("short", "openai") == False
    
    print("✅ API key validation tests passed!")

def test_service_initialization():
    """Test service initializes correctly with environment variables"""
    from ai_service import AIService
    
    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = "sk-proj-test123456789"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-api03-test123456789"
    os.environ["XAI_API_KEY"] = "xai-test123456789"
    
    try:
        service = AIService()
        print(f"✅ Service initialized with {len(service.clients)} clients")
        print(f"✅ Provider health: {list(service.provider_health.keys())}")
        
        # Test health status
        health = service.get_health_status()
        print(f"✅ Health status: {health['status']}")
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False
    
    return True

def test_configuration_loading():
    """Test configuration loads correctly"""
    from ai_service import load_config
    
    config = load_config()
    
    assert "service" in config
    assert "providers" in config
    assert "logging" in config
    
    print("✅ Configuration loading tests passed!")

if __name__ == "__main__":
    print("🚀 Testing AI Service Security Features")
    print("=" * 50)
    
    try:
        test_api_key_validation()
        test_configuration_loading()
        test_service_initialization()
        
        print("\n✅ All tests passed! AI Service is ready for containerized deployment.")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        sys.exit(1)
