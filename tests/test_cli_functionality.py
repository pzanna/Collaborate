#!/usr/bin/env python3
"""
Test suite for CLI functionality and user experience
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the CLI class
sys.path.insert(0, str(Path(__file__).parent.parent))
from collaborate import SimpleCollaborateCLI


class TestCLIFunctionality(unittest.TestCase):
    """Test CLI functionality and user experience."""
    
    def setUp(self):
        """Set up test environment."""
        self.cli = None
        
    def tearDown(self):
        """Clean up after tests."""
        if self.cli:
            del self.cli
    
    def test_cli_initialization(self):
        """Test CLI initialization."""
        try:
            self.cli = SimpleCollaborateCLI()
            self.assertIsNotNone(self.cli)
            self.assertIsNotNone(self.cli.config_manager)
            self.assertIsNotNone(self.cli.db_manager)
            self.assertIsNotNone(self.cli.export_manager)
            print("✅ CLI initialization test passed")
        except Exception as e:
            self.fail(f"CLI initialization failed: {e}")
    
    def test_safe_input_eof_handling(self):
        """Test safe_input method handles EOF properly."""
        self.cli = SimpleCollaborateCLI()
        
        # Mock input to raise EOFError
        with patch('builtins.input', side_effect=EOFError()):
            with self.assertRaises(SystemExit):
                self.cli.safe_input("Test prompt: ")
        
        print("✅ Safe input EOF handling test passed")
    
    def test_safe_input_keyboard_interrupt(self):
        """Test safe_input method handles KeyboardInterrupt properly."""
        self.cli = SimpleCollaborateCLI()
        
        # Mock input to raise KeyboardInterrupt
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            with self.assertRaises(SystemExit):
                self.cli.safe_input("Test prompt: ")
        
        print("✅ Safe input KeyboardInterrupt handling test passed")
    
    def test_system_health_check(self):
        """Test system health check functionality."""
        self.cli = SimpleCollaborateCLI()
        
        # This should not raise any exceptions
        try:
            self.cli.check_system_health_standalone()
            print("✅ System health check test passed")
        except Exception as e:
            self.fail(f"System health check failed: {e}")
    
    def test_list_projects_empty(self):
        """Test listing projects when none exist."""
        self.cli = SimpleCollaborateCLI()
        
        # Mock empty projects list
        with patch.object(self.cli.db_manager, 'list_projects', return_value=[]):
            try:
                self.cli.list_projects()
                print("✅ List projects (empty) test passed")
            except Exception as e:
                self.fail(f"List projects failed: {e}")
    
    def test_list_conversations_empty(self):
        """Test listing conversations when none exist."""
        self.cli = SimpleCollaborateCLI()
        
        # Mock empty conversations list
        with patch.object(self.cli.db_manager, 'list_conversations', return_value=[]):
            try:
                self.cli.list_conversations()
                print("✅ List conversations (empty) test passed")
            except Exception as e:
                self.fail(f"List conversations failed: {e}")
    
    def test_show_configuration(self):
        """Test showing configuration."""
        self.cli = SimpleCollaborateCLI()
        
        try:
            self.cli.show_configuration()
            print("✅ Show configuration test passed")
        except Exception as e:
            self.fail(f"Show configuration failed: {e}")
    
    def test_ai_connection_test(self):
        """Test AI connection testing."""
        self.cli = SimpleCollaborateCLI()
        
        try:
            self.cli.test_ai_connections()
            print("✅ AI connection test passed")
        except Exception as e:
            self.fail(f"AI connection test failed: {e}")
    
    def test_view_response_stats(self):
        """Test viewing response statistics."""
        self.cli = SimpleCollaborateCLI()
        
        try:
            self.cli.view_response_stats()
            print("✅ View response stats test passed")
        except Exception as e:
            self.fail(f"View response stats failed: {e}")
    
    def test_menu_display(self):
        """Test menu display functionality."""
        self.cli = SimpleCollaborateCLI()
        
        try:
            self.cli.show_menu()
            print("✅ Menu display test passed")
        except Exception as e:
            self.fail(f"Menu display failed: {e}")
    
    def test_error_handling_in_methods(self):
        """Test error handling in various methods."""
        self.cli = SimpleCollaborateCLI()
        
        # Test with database errors - should handle gracefully
        with patch.object(self.cli.db_manager, 'list_projects', side_effect=Exception("Test error")):
            try:
                self.cli.list_projects()  # Should not raise exception, should print error message
                print("✅ Error handling in list_projects test passed")
            except Exception as e:
                self.fail(f"Error handling failed - method should catch and handle errors: {e}")
        
        with patch.object(self.cli.db_manager, 'list_conversations', side_effect=Exception("Test error")):
            try:
                self.cli.list_conversations()  # Should not raise exception, should print error message
                print("✅ Error handling in list_conversations test passed")
            except Exception as e:
                self.fail(f"Error handling failed - method should catch and handle errors: {e}")


def run_cli_tests():
    """Run all CLI tests."""
    print("🧪 Running CLI Functionality Tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCLIFunctionality)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All CLI tests passed!' if success else '❌ Some CLI tests failed!'}")
    
    return success


if __name__ == "__main__":
    success = run_cli_tests()
    sys.exit(0 if success else 1)
