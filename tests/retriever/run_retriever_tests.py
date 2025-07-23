#!/usr/bin/env python3
"""
RetrieverAgent Test Launcher

Simple script to launch the appropriate test application.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Main launcher function."""
    print("RetrieverAgent Test Launcher")
    print("============================")
    
    # Check if test files exist
    standalone_test = Path("test_retriever_standalone.py")
    full_test = Path("test_retriever_debug.py")
    ssl_diagnostics = Path("ssl_diagnostics.py")
    
    if not standalone_test.exists() and not full_test.exists():
        print("❌ No test files found!")
        print("Make sure you're in the correct directory.")
        return 1
    
    print("\nAvailable Test Options:")
    print("1. Standalone Test (Recommended) - Works without full Eunice system")
    print("2. Full System Test - Requires complete Eunice installation")
    print("3. Interactive Standalone Debug")
    print("4. Interactive Full System Debug")
    print("5. SSL Diagnostics - Diagnose SSL/certificate issues")
    print("6. Check Dependencies")
    print("7. Run Quick Connectivity Test")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (0-7): ").strip()
            
            if choice == "0":
                print("Goodbye!")
                return 0
            
            elif choice == "1":
                if standalone_test.exists():
                    print("Launching standalone test suite...")
                    return subprocess.call([sys.executable, str(standalone_test)])
                else:
                    print("❌ Standalone test not found!")
            
            elif choice == "2":
                if full_test.exists():
                    print("Launching full system test suite...")
                    return subprocess.call([sys.executable, str(full_test)])
                else:
                    print("❌ Full system test not found!")
            
            elif choice == "3":
                if standalone_test.exists():
                    print("Launching interactive standalone debugger...")
                    return subprocess.call([sys.executable, str(standalone_test), "--interactive"])
                else:
                    print("❌ Standalone test not found!")
            
            elif choice == "4":
                if full_test.exists():
                    print("Launching interactive full system debugger...")
                    return subprocess.call([sys.executable, str(full_test), "--interactive"])
                else:
                    print("❌ Full system test not found!")
            
            elif choice == "5":
                if ssl_diagnostics.exists():
                    print("Running SSL diagnostics...")
                    return subprocess.call([sys.executable, str(ssl_diagnostics)])
                else:
                    print("❌ SSL diagnostics not found!")
            
            elif choice == "6":
                check_dependencies()
            
            elif choice == "7":
                run_quick_connectivity_test()
            
            else:
                print("Invalid choice. Please enter 0-7.")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\nChecking Dependencies...")
    print("=" * 30)
    
    required_packages = [
        "aiohttp",
        "beautifulsoup4",
        "certifi",
        "asyncio"  # Built-in, but let's check
    ]
    
    optional_packages = [
        "rich",
        "colorama",
        "pytest"
    ]
    
    all_good = True
    
    print("Required packages:")
    for package in required_packages:
        try:
            if package == "asyncio":
                import asyncio
                print(f"  ✅ {package} (built-in)")
            else:
                __import__(package)
                print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            all_good = False
    
    print("\nOptional packages:")
    for package in optional_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ⚠️  {package} - not installed (optional)")
    
    if not all_good:
        print("\n🔧 To install missing packages:")
        print("   pip install -r test_requirements.txt")
        print("   # or individually:")
        print("   pip install aiohttp beautifulsoup4 certifi")
    else:
        print("\n✅ All required dependencies are installed!")
    
    print("\n" + "=" * 30)


def run_quick_connectivity_test():
    """Run a quick connectivity test to verify internet access."""
    print("\nRunning Quick Connectivity Test...")
    print("=" * 40)
    
    try:
        import urllib.request
        import ssl
        import time
        
        test_urls = [
            "https://httpbin.org/get",
            "https://api.duckduckgo.com/",
            "https://www.google.com/",
        ]
        
        # Test with certifi SSL context
        try:
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            print("✅ Using certifi SSL context")
        except ImportError:
            ssl_context = ssl.create_default_context()
            print("⚠️  Using default SSL context (certifi not available)")
        
        successful_tests = 0
        
        for url in test_urls:
            try:
                start_time = time.time()
                
                # Create HTTPS handler with SSL context
                https_handler = urllib.request.HTTPSHandler(context=ssl_context)
                opener = urllib.request.build_opener(https_handler)
                
                request = urllib.request.Request(url)
                request.add_header('User-Agent', 'RetrieverAgent-Test/1.0')
                
                response = opener.open(request, timeout=10)
                duration = time.time() - start_time
                
                if response.getcode() == 200:
                    print(f"  ✅ {url} - {response.getcode()} ({duration:.2f}s)")
                    successful_tests += 1
                else:
                    print(f"  ⚠️  {url} - {response.getcode()} ({duration:.2f}s)")
                
                response.close()
                
            except Exception as e:
                print(f"  ❌ {url} - {str(e)[:60]}...")
        
        success_rate = (successful_tests / len(test_urls)) * 100
        print(f"\nConnectivity Test Results:")
        print(f"  Success Rate: {success_rate:.1f}% ({successful_tests}/{len(test_urls)})")
        
        if success_rate == 100:
            print("  🎉 Perfect connectivity! Ready for retrieval testing.")
        elif success_rate >= 66:
            print("  ✅ Good connectivity. Some services may have issues.")
        elif success_rate >= 33:
            print("  ⚠️  Poor connectivity. Check network/firewall settings.")
        else:
            print("  ❌ Severe connectivity issues. Check internet connection.")
    
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
    
    print("\n" + "=" * 40)


if __name__ == "__main__":
    sys.exit(main())
