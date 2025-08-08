#!/usr/bin/env python3
"""
Validation script for containerized API Gateway

Validates that the service is configured correctly and can start properly.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def validate_files() -> Tuple[bool, List[str]]:
    """Validate that all required files exist"""
    required_files = [
        "main.py",
        "config.py", 
        "models.py",
        "mcp_client.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "README.md"
    ]
    
    errors = []
    
    for file_name in required_files:
        if not Path(file_name).exists():
            errors.append(f"Missing required file: {file_name}")
    
    return len(errors) == 0, errors


def validate_dockerfile() -> Tuple[bool, List[str]]:
    """Validate Dockerfile configuration"""
    errors = []
    
    try:
        with open("Dockerfile", "r") as f:
            content = f.read()
            
        # Check for required components
        required_components = [
            "FROM python:",
            "WORKDIR /app",
            "COPY requirements.txt",
            "RUN pip install",
            "EXPOSE 8001",
            "CMD [\"python\", \"main.py\"]"
        ]
        
        for component in required_components:
            if component not in content:
                errors.append(f"Dockerfile missing: {component}")
                
    except FileNotFoundError:
        errors.append("Dockerfile not found")
    except Exception as e:
        errors.append(f"Error reading Dockerfile: {e}")
    
    return len(errors) == 0, errors


def validate_docker_compose() -> Tuple[bool, List[str]]:
    """Validate docker-compose.yml configuration"""
    errors = []
    
    try:
        with open("docker-compose.yml", "r") as f:
            content = f.read()
            
        # Check for required components
        required_components = [
            "api-gateway:",
            "build:",
            "ports:",
            "8001:8001",
            "environment:",
            "MCP_SERVER_HOST",
            "depends_on:",
            "mcp-server"
        ]
        
        for component in required_components:
            if component not in content:
                errors.append(f"docker-compose.yml missing: {component}")
                
    except FileNotFoundError:
        errors.append("docker-compose.yml not found")
    except Exception as e:
        errors.append(f"Error reading docker-compose.yml: {e}")
    
    return len(errors) == 0, errors


def validate_python_imports() -> Tuple[bool, List[str]]:
    """Validate Python imports in main files"""
    errors = []
    
    files_to_check = [
        ("main.py", ["fastapi", "uvicorn", "pydantic"]),
        ("mcp_client.py", ["websockets", "asyncio", "json"]),
        ("models.py", ["pydantic", "uuid", "datetime"]),
        ("config.py", ["os", "typing"])
    ]
    
    for file_name, expected_imports in files_to_check:
        if not Path(file_name).exists():
            continue
            
        try:
            with open(file_name, "r") as f:
                content = f.read()
                
            for imp in expected_imports:
                if f"import {imp}" not in content and f"from {imp}" not in content:
                    errors.append(f"{file_name} missing import: {imp}")
                    
        except Exception as e:
            errors.append(f"Error checking imports in {file_name}: {e}")
    
    return len(errors) == 0, errors


def validate_configuration() -> Tuple[bool, List[str]]:
    """Validate configuration settings"""
    errors = []
    
    try:
        # Try to import and validate config
        sys.path.insert(0, ".")
        from config import Config
        
        # Check required configuration attributes
        required_attrs = [
            "HOST", "PORT", "MCP_SERVER_HOST", "MCP_SERVER_PORT",
            "API_TITLE", "API_VERSION", "LOG_LEVEL"
        ]
        
        for attr in required_attrs:
            if not hasattr(Config, attr):
                errors.append(f"Config missing attribute: {attr}")
        
        # Validate config methods
        try:
            mcp_config = Config.get_mcp_config()
            if not isinstance(mcp_config, dict):
                errors.append("Config.get_mcp_config() should return dict")
        except Exception as e:
            errors.append(f"Error in get_mcp_config(): {e}")
            
        try:
            server_config = Config.get_server_config()
            if not isinstance(server_config, dict):
                errors.append("Config.get_server_config() should return dict")
        except Exception as e:
            errors.append(f"Error in get_server_config(): {e}")
            
    except ImportError as e:
        errors.append(f"Cannot import config: {e}")
    except Exception as e:
        errors.append(f"Error validating configuration: {e}")
    
    return len(errors) == 0, errors


def validate_requirements() -> Tuple[bool, List[str]]:
    """Validate requirements.txt"""
    errors = []
    
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
            
        required_packages = [
            "fastapi", "uvicorn", "pydantic", "websockets",
            "aiohttp", "asyncpg", "redis"
        ]
        
        for package in required_packages:
            if package not in content:
                errors.append(f"requirements.txt missing package: {package}")
                
    except FileNotFoundError:
        errors.append("requirements.txt not found")
    except Exception as e:
        errors.append(f"Error reading requirements.txt: {e}")
    
    return len(errors) == 0, errors


def validate_test_script() -> Tuple[bool, List[str]]:
    """Validate test script"""
    errors = []
    
    if not Path("test_api_gateway.py").exists():
        errors.append("Missing test_api_gateway.py")
        return False, errors
    
    try:
        with open("test_api_gateway.py", "r") as f:
            content = f.read()
            
        # Check for required test methods
        required_tests = [
            "test_health_check",
            "test_status_endpoint", 
            "test_literature_search",
            "test_research_task_submission"
        ]
        
        for test in required_tests:
            if test not in content:
                errors.append(f"test_api_gateway.py missing test: {test}")
                
    except Exception as e:
        errors.append(f"Error reading test_api_gateway.py: {e}")
    
    return len(errors) == 0, errors


def main():
    """Run all validations"""
    print("🔍 Validating Containerized API Gateway Configuration")
    print("=" * 60)
    
    validations = [
        ("File Structure", validate_files),
        ("Dockerfile", validate_dockerfile),
        ("Docker Compose", validate_docker_compose),
        ("Python Imports", validate_python_imports),
        ("Configuration", validate_configuration),
        ("Requirements", validate_requirements),
        ("Test Script", validate_test_script)
    ]
    
    all_passed = True
    total_errors = []
    
    for validation_name, validation_func in validations:
        print(f"\n📋 {validation_name}:")
        
        try:
            passed, errors = validation_func()
            
            if passed:
                print(f"   ✅ Passed")
            else:
                print(f"   ❌ Failed ({len(errors)} errors)")
                for error in errors:
                    print(f"      - {error}")
                all_passed = False
                total_errors.extend(errors)
                
        except Exception as e:
            print(f"   ❌ Validation error: {e}")
            all_passed = False
            total_errors.append(f"{validation_name}: {e}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All validations passed! API Gateway is ready for deployment.")
        print("\nNext steps:")
        print("1. Build the container: ./start.sh build")
        print("2. Start the service: ./start.sh start") 
        print("3. Run tests: ./start.sh test")
        return 0
    else:
        print(f"❌ Validation failed with {len(total_errors)} errors.")
        print("\nPlease fix the above issues before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
