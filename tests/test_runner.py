"""
Phase 6 Test Suite - Main Test Runner

This module provides the main test runner for Phase 6 comprehensive testing.
It includes utilities for running different types of tests and collecting results.
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest
from datetime import datetime
import json

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.performance import PerformanceMonitor
from utils.error_handler import ErrorHandler


class TestSuiteRunner:
    """Main test suite runner for Phase 6 testing."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()
        self.test_results = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Ensure test results directory exists
        self.results_dir = self.project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)
    
    def _parse_test_results(self, result: subprocess.CompletedProcess, test_type: str) -> Dict[str, Any]:
        """Parse test results from subprocess output."""
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "type": test_type
        }
    
    def run_unit_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run unit tests with comprehensive reporting."""
        print("🧪 Running Unit Tests...")
        print("=" * 50)
        
        try:
            # Run unit tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_phase6_unit.py", 
                "-v", "--tb=short",
                "-m", "unit"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Parse results
            return self._parse_test_results(result, "unit")
            
        except Exception as e:
            self.error_handler.handle_error(e, "unit_tests")
            return {"status": "error", "error": str(e)}
    
    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run integration tests."""
        print("🔗 Running Integration Tests...")
        print("=" * 50)
        
        try:
            # Run integration tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_phase6_integration.py", 
                "-v", "--tb=short",
                "-m", "integration"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Parse results
            return self._parse_test_results(result, "integration")
            
        except Exception as e:
            self.error_handler.handle_error(e, "integration_tests")
            return {"status": "error", "error": str(e)}
    
    def run_performance_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run performance tests."""
        print("⚡ Running Performance Tests...")
        print("=" * 50)
        
        try:
            # Run performance tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_phase6_performance.py", 
                "-v", "--tb=short",
                "-m", "performance"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Parse results
            return self._parse_test_results(result, "performance")
            
        except Exception as e:
            self.error_handler.handle_error(e, "performance_tests")
            return {"status": "error", "error": str(e)}
    
    def run_e2e_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run end-to-end tests."""
        print("🎯 Running End-to-End Tests...")
        print("=" * 50)
        
        try:
            # Run e2e tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_phase6_e2e.py", 
                "-v", "--tb=short",
                "-m", "e2e"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Parse results
            return self._parse_test_results(result, "e2e")
            
        except Exception as e:
            self.error_handler.handle_error(e, "e2e_tests")
            return {"status": "error", "error": str(e)}
    
    def run_all_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run all test suites."""
        print("🚀 Running Complete Test Suite - Phase 6")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        # Create test results directory
        os.makedirs("test_results", exist_ok=True)
        
        # Run all test types
        try:
            unit_result = self.run_unit_tests(verbose)
            integration_result = self.run_integration_tests(verbose)
            performance_result = self.run_performance_tests(verbose)
            e2e_result = self.run_e2e_tests(verbose)
            
            self.end_time = datetime.now()
            
            # Generate summary
            summary = self.generate_test_summary()
            
            # Save results
            self.save_test_results(summary)
            
            return summary
            
        except Exception as e:
            self.error_handler.handle_error(e, "run_all_tests")
            raise
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive test summary."""
        total_duration = 0.0
        if self.start_time and self.end_time:
            total_duration = (self.end_time - self.start_time).total_seconds()
        
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        total_tests = len(self.test_results)
        
        summary = {
            "summary": {
                "total_test_suites": total_tests,
                "passed_test_suites": passed_tests,
                "failed_test_suites": total_tests - passed_tests,
                "total_duration": total_duration,
                "start_time": self.start_time.isoformat() if self.start_time else "",
                "end_time": self.end_time.isoformat() if self.end_time else "",
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "test_results": self.test_results,
            "performance_stats": self.performance_monitor.get_performance_stats()
        }
        
        return summary
    
    def save_test_results(self, summary: Dict[str, Any]) -> None:
        """Save test results to file."""
        results_file = Path("test_results/phase6_test_summary.json")
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📊 Test results saved to: {results_file}")
    
    def print_test_summary(self) -> None:
        """Print a formatted test summary."""
        if not self.test_results:
            print("❌ No test results available")
            return
        
        print("\n" + "=" * 60)
        print("📊 PHASE 6 TEST SUMMARY")
        print("=" * 60)
        
        total_duration = 0.0
        if self.start_time and self.end_time:
            total_duration = (self.end_time - self.start_time).total_seconds()
        
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        total_tests = len(self.test_results)
        
        print(f"🏁 Total Test Suites: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"📈 Success Rate: {(passed_tests / total_tests * 100):.1f}%")
        
        print("\n📋 Test Suite Details:")
        for test_type, result in self.test_results.items():
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"  {test_type}: {status} ({result['duration']:.2f}s)")
        
        # Overall status
        if passed_tests == total_tests:
            print(f"\n🎉 All tests passed! Phase 6 testing complete.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed. Please review the results.")


def main():
    """Main entry point for test suite runner."""
    runner = TestSuiteRunner()
    
    # Check if specific test type is requested
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "unit":
            runner.run_unit_tests()
        elif test_type == "integration":
            runner.run_integration_tests()
        elif test_type == "performance":
            runner.run_performance_tests()
        elif test_type == "e2e":
            runner.run_e2e_tests()
        else:
            print(f"❌ Unknown test type: {test_type}")
            print("Available options: unit, integration, performance, e2e")
            sys.exit(1)
    else:
        # Run all tests
        runner.run_all_tests()
    
    # Print summary
    runner.print_test_summary()


if __name__ == "__main__":
    main()
