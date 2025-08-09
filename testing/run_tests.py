#!/usr/bin/env python3
"""
Test runner for API Gateway tests.

This script provides convenient ways to run API Gateway tests
with different configurations and options.
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules
from testing.test_api import run_single_test, run_all_tests


def setup_test_environment():
    """Set up test environment."""
    # Set environment variables for testing
    test_env = {
        "API_GATEWAY_URL": "http://localhost:8001",
        "SERVICE_HOST": "localhost", 
        "SERVICE_PORT": "8001",
        "LOG_LEVEL": "DEBUG",
        "DATABASE_URL": "postgresql://eunice:eunice@localhost:5432/eunice_test"
    }
    
    for key, value in test_env.items():
        os.environ.setdefault(key, value)
    
    print("🔧 Test environment configured")


def check_api_gateway_availability():
    """Check if API Gateway is available."""
    import httpx
    
    api_url = os.getenv("API_GATEWAY_URL", "http://localhost:8001")
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{api_url}/health")
            if response.status_code == 200:
                print(f"✅ API Gateway is available at {api_url}")
                return True
            else:
                print(f"❌ API Gateway returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ API Gateway is not available at {api_url}: {e}")
        return False


def run_pytest_tests(test_pattern=None, verbose=False, coverage=False):
    """Run tests using pytest."""
    import subprocess
    
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.extend(["-v", "-s"])
    
    if coverage:
        cmd.extend(["--cov=api-gateway/src", "--cov-report=html", "--cov-report=term"])
    
    if test_pattern:
        cmd.extend(["-k", test_pattern])
    
    # Add test directory
    cmd.append("testing/")
    
    print(f"🚀 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run API Gateway tests")
    parser.add_argument(
        "--test", "-t",
        help="Run specific test (e.g., 'health_check' or 'test_health_check')"
    )
    parser.add_argument(
        "--pattern", "-p",
        help="Run tests matching pattern (pytest -k option)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all tests"
    )
    parser.add_argument(
        "--check-service", "-c",
        action="store_true",
        help="Check if API Gateway service is available"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="Use pytest instead of direct test runner"
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Skip API Gateway availability check"
    )
    
    args = parser.parse_args()
    
    # Setup test environment
    setup_test_environment()
    
    # Check service availability unless skipped
    if not args.no_check and not args.check_service:
        if not check_api_gateway_availability():
            print("\n⚠️  API Gateway is not available. Tests may fail.")
            print("   Make sure the API Gateway service is running on http://localhost:8001")
            print("   Use --no-check to skip this check.")
            response = input("\nContinue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    if args.check_service:
        # Just check service and exit
        available = check_api_gateway_availability()
        sys.exit(0 if available else 1)
    
    if args.pytest or args.coverage:
        # Use pytest
        success = run_pytest_tests(args.pattern, args.verbose, args.coverage)
        sys.exit(0 if success else 1)
    
    elif args.test:
        # Run specific test
        test_name = args.test
        if not test_name.startswith('test_'):
            test_name = f"test_{test_name}"
        
        print(f"🎯 Running test: {test_name}")
        run_single_test(test_name)
    
    elif args.all:
        # Run all tests
        print("🚀 Running all tests...")
        success = run_all_tests()
        sys.exit(0 if success else 1)
    
    else:
        # Show help
        parser.print_help()
        print("\nExamples:")
        print("  python run_tests.py --all                    # Run all tests")
        print("  python run_tests.py --test health_check      # Run specific test")
        print("  python run_tests.py --pattern project        # Run tests matching 'project'")
        print("  python run_tests.py --check-service          # Check if API Gateway is running")
        print("  python run_tests.py --pytest --coverage      # Run with pytest and coverage")


if __name__ == "__main__":
    main()
