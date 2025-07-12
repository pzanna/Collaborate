#!/usr/bin/env python3
"""
Test enhanced error handling functionality
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.error_handler import (
    ErrorHandler, CollaborateError, NetworkError, APIError, 
    DatabaseError, ConfigurationError, ValidationError, FileError,
    handle_errors, safe_execute, format_error_for_user
)


def test_error_types():
    """Test different error types."""
    print("🧪 Testing Error Types...")
    
    # Test NetworkError
    network_error = NetworkError("Connection timeout", {"host": "example.com"})
    print(f"✓ NetworkError: {network_error}")
    
    # Test APIError
    api_error = APIError("Rate limit exceeded", "openai", 429)
    print(f"✓ APIError: {api_error}")
    
    # Test DatabaseError
    db_error = DatabaseError("Table not found", "query", {"table": "projects"})
    print(f"✓ DatabaseError: {db_error}")
    
    # Test ValidationError
    validation_error = ValidationError("Invalid email format", "email", "invalid-email")
    print(f"✓ ValidationError: {validation_error}")
    
    # Test FileError
    file_error = FileError("Permission denied", "/tmp/test.txt", "read")
    print(f"✓ FileError: {file_error}")
    
    # Test error serialization
    error_dict = api_error.to_dict()
    assert "message" in error_dict
    assert "error_type" in error_dict
    assert "timestamp" in error_dict
    print("✓ Error serialization works")


def test_error_handler():
    """Test error handler functionality."""
    print("\n🧪 Testing Error Handler...")
    
    error_handler = ErrorHandler()
    
    # Test handling different types of errors
    try:
        raise ValueError("Test error")
    except Exception as e:
        collaborate_error = error_handler.handle_error(e, "test_context")
        print(f"✓ Handled ValueError: {collaborate_error}")
    
    try:
        raise ConnectionError("Network timeout")
    except Exception as e:
        collaborate_error = error_handler.handle_error(e, "network_test")
        print(f"✓ Handled ConnectionError: {collaborate_error}")
    
    # Test error statistics
    stats = error_handler.get_error_stats()
    assert stats["total_errors"] >= 2
    print(f"✓ Error stats: {stats['total_errors']} total errors")
    
    # Test error reset
    error_handler.reset_stats()
    stats = error_handler.get_error_stats()
    assert stats["total_errors"] == 0
    print("✓ Error stats reset works")


def test_error_decorator():
    """Test error handling decorator."""
    print("\n🧪 Testing Error Decorator...")
    
    @handle_errors(context="test_function", reraise=False, fallback_return="fallback")
    def failing_function():
        raise ValueError("This function always fails")
    
    @handle_errors(context="test_function")
    def working_function():
        return "success"
    
    # Test fallback return
    result = failing_function()
    assert result == "fallback"
    print("✓ Error decorator fallback works")
    
    # Test normal execution
    result = working_function()
    assert result == "success"
    print("✓ Error decorator normal execution works")


def test_safe_execute():
    """Test safe execution utility."""
    print("\n🧪 Testing Safe Execute...")
    
    def failing_function():
        raise ValueError("This fails")
    
    def working_function(x, y):
        return x + y
    
    # Test safe execution with failure
    result = safe_execute(failing_function, context="test", fallback_return="failed")
    assert result == "failed"
    print("✓ Safe execute with failure works")
    
    # Test safe execution with success
    result = safe_execute(working_function, 2, 3, context="test")
    assert result == 5
    print("✓ Safe execute with success works")


def test_user_error_formatting():
    """Test user-friendly error formatting."""
    print("\n🧪 Testing User Error Formatting...")
    
    # Test different error types
    errors = [
        NetworkError("Connection timeout"),
        APIError("Rate limit exceeded", "openai", 429),
        DatabaseError("Table not found", "query"),
        ConfigurationError("API key missing"),
        ValidationError("Invalid input", "email"),
        FileError("Permission denied", "/tmp/test.txt", "read")
    ]
    
    for error in errors:
        user_message = format_error_for_user(error)
        assert user_message.startswith("⚠️")
        print(f"✓ {error.error_type.value}: {user_message}")


def test_error_context_conversion():
    """Test automatic error type conversion."""
    print("\n🧪 Testing Error Context Conversion...")
    
    error_handler = ErrorHandler()
    
    # Test network error conversion
    try:
        raise ConnectionError("Connection timeout")
    except Exception as e:
        error = error_handler.handle_error(e)
        assert error.error_type.value == "network_error"
        print("✓ Network error conversion works")
    
    # Test database error conversion
    try:
        raise Exception("sqlite3.OperationalError: database is locked")
    except Exception as e:
        error = error_handler.handle_error(e)
        assert error.error_type.value == "database_error"
        print("✓ Database error conversion works")
    
    # Test API error conversion
    try:
        raise Exception("HTTP request failed")
    except Exception as e:
        error = error_handler.handle_error(e)
        assert error.error_type.value == "api_error"
        print("✓ API error conversion works")


def test_integration_example():
    """Test a realistic integration example."""
    print("\n🧪 Testing Integration Example...")
    
    @handle_errors(context="simulated_ai_call", reraise=False)
    def simulate_ai_call(provider: str, message: str):
        """Simulate an AI API call that might fail."""
        if provider == "failing_provider":
            raise ConnectionError("Network timeout")
        elif provider == "rate_limited":
            raise Exception("HTTP 429: Rate limit exceeded")
        else:
            return f"Response from {provider}: {message}"
    
    # Test successful call
    result = simulate_ai_call("openai", "Hello")
    assert "Response from openai" in result
    print("✓ Successful AI call simulation")
    
    # Test network failure
    result = simulate_ai_call("failing_provider", "Hello")
    assert result is None  # Default fallback
    print("✓ Network failure handling")
    
    # Test rate limit
    result = simulate_ai_call("rate_limited", "Hello")
    assert result is None  # Default fallback
    print("✓ Rate limit handling")


if __name__ == "__main__":
    try:
        test_error_types()
        test_error_handler()
        test_error_decorator()
        test_safe_execute()
        test_user_error_formatting()
        test_error_context_conversion()
        test_integration_example()
        
        print("\n🎉 All error handling tests passed!")
        print("\nKey Features Tested:")
        print("• Custom error types with context")
        print("• Error handler with statistics")
        print("• Error handling decorator")
        print("• Safe execution utility")
        print("• User-friendly error formatting")
        print("• Automatic error type conversion")
        print("• Real-world integration scenarios")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
