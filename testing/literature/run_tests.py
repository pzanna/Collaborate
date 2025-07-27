#!/usr/bin/env python3
"""
LiteratureAgent Test Runner

Consolidated test runner for all LiteratureAgent functionality.
Replaces the multiple separate test runners with a single, comprehensive solution.
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_test_command(command: list, description: str) -> bool:
    """Run a test command and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Set PYTHONPATH to include the project root
        project_root = Path(__file__).parent.parent.parent
        env = dict(os.environ)
        env["PYTHONPATH"] = str(project_root / "src")
        
        # Run the command
        result = subprocess.run(
            command,
            cwd=project_root,
            env=env,
            text=True
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully in {duration:.2f}s")
            return True
        else:
            print(f"❌ {description} failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ {description} failed with error: {e} (after {duration:.2f}s)")
        return False


def main():
    """Main test runner function."""
    print("LiteratureAgent Test Runner")
    print("=" * 40)
    print("Consolidated test suite for all LiteratureAgent functionality")
    
    print("\nAvailable Test Options:")
    print("1. 🚀 Run All Tests (Comprehensive)")
    print("2. 🧪 Run Pytest Suite")
    print("3. 🔬 Run Standalone Tests")
    print("4. 📊 Run Specific Test Category")
    print("5. 🔍 Check Test Environment")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (0-5): ").strip()
            
            if choice == "0":
                print("Goodbye!")
                return 0
            
            elif choice == "1":
                print("Running comprehensive test suite...")
                
                tests = [
                    (
                        ["python", "-m", "pytest", "tests/literature/test_literature_complete.py", "-v"],
                        "Pytest Test Suite"
                    ),
                    (
                        ["python", "tests/literature/test_literature_complete.py"],
                        "Standalone Test Suite"
                    )
                ]
                
                passed = 0
                total = len(tests)
                
                for command, description in tests:
                    if run_test_command(command, description):
                        passed += 1
                
                print(f"\n📊 Overall Results: {passed}/{total} test suites passed")
                return 0 if passed == total else 1
            
            elif choice == "2":
                return run_test_command(
                    ["python", "-m", "pytest", "tests/literature/test_literature_complete.py", "-v"],
                    "Pytest Test Suite"
                )
            
            elif choice == "3":
                return run_test_command(
                    ["python", "tests/literature/test_literature_complete.py"],
                    "Standalone Test Suite"
                )
            
            elif choice == "4":
                print("\nAvailable Test Categories:")
                print("a. Basic functionality tests")
                print("b. Workflow function tests")
                print("c. Semantic Scholar integration tests")
                print("d. Error handling tests")
                
                category = input("Enter category (a-d): ").strip().lower()
                
                if category == "a":
                    return run_test_command(
                        ["python", "-m", "pytest", "tests/literature/test_literature_complete.py::TestLiteratureAgent::test_basic_search_functionality", "-v"],
                        "Basic Functionality Tests"
                    )
                elif category == "b":
                    return run_test_command(
                        ["python", "-m", "pytest", "tests/literature/test_literature_complete.py", "-k", "workflow", "-v"],
                        "Workflow Function Tests"
                    )
                elif category == "c":
                    return run_test_command(
                        ["python", "-m", "pytest", "tests/literature/test_literature_complete.py::TestLiteratureAgent::test_semantic_scholar_integration", "-v"],
                        "Semantic Scholar Integration Tests"
                    )
                elif category == "d":
                    return run_test_command(
                        ["python", "-m", "pytest", "tests/literature/test_literature_complete.py::TestLiteratureAgent::test_error_handling", "-v"],
                        "Error Handling Tests"
                    )
                else:
                    print("Invalid category selection.")
                    continue
            
            elif choice == "5":
                print("Checking test environment...")
                
                # Check Python version
                print(f"Python version: {sys.version}")
                
                # Check if project structure exists
                project_root = Path(__file__).parent.parent.parent
                print(f"Project root: {project_root}")
                
                required_paths = [
                    project_root / "src" / "agents" / "literature_agent.py",
                    project_root / "src" / "config" / "config_manager.py",
                    project_root / "tests" / "literature" / "test_literature_complete.py"
                ]
                
                all_good = True
                for path in required_paths:
                    if path.exists():
                        print(f"✅ {path.relative_to(project_root)}")
                    else:
                        print(f"❌ {path.relative_to(project_root)} (missing)")
                        all_good = False
                
                # Check dependencies
                try:
                    import pytest
                    print(f"✅ pytest version: {pytest.__version__}")
                except ImportError:
                    print("❌ pytest not installed")
                    all_good = False
                
                if all_good:
                    print("\n✅ Test environment looks good!")
                else:
                    print("\n❌ Test environment has issues that need to be resolved.")
                
                continue
            
            else:
                print("Invalid choice. Please enter 0-5.")
                continue
                
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
            return 1
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
