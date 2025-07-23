#!/usr/bin/env python3
"""
Configuration and Dependencies Management for Enhanced Thesis Generator
=====================================================================

This script checks dependencies and provides installation instructions for the
enhanced thesis generator system.

Author: GitHub Copilot for Paul Zanna
Date: July 23, 2025
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_dependencies():
    """Check Python package dependencies."""
    dependencies = {
        'jinja2': 'pip install jinja2',
        'pyyaml': 'pip install pyyaml',
        'jsonschema': 'pip install jsonschema',
        'openai': 'pip install openai'
    }
    
    missing = []
    for package, install_cmd in dependencies.items():
        try:
            importlib.import_module(package)
            print(f"✅ {package} - installed")
        except ImportError:
            print(f"❌ {package} - missing")
            missing.append((package, install_cmd))
    
    return missing

def check_system_dependencies():
    """Check system-level dependencies."""
    system_deps = {
        'pandoc': 'Required for PDF/DOCX conversion',
        'xelatex': 'Required for PDF generation (part of TeX Live)',
        'git': 'Required for version control'
    }
    
    missing = []
    for cmd, description in system_deps.items():
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
            print(f"✅ {cmd} - installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {cmd} - missing ({description})")
            missing.append((cmd, description))
    
    return missing

def check_eunice_integration():
    """Check Eunice AI client availability."""
    try:
        sys.path.append(str(Path(__file__).parent.parent))
        from src.ai_clients.openai_client import OpenAIClient, AIProviderConfig
        print("✅ Eunice AI clients - available")
        return True
    except ImportError:
        print("❌ Eunice AI clients - not available (will use fallback)")
        return False

def create_default_config():
    """Create default configuration file."""
    config_content = """# Enhanced Thesis Generator Configuration
# ======================================

# AI Configuration
ai:
  provider: openai
  model: gpt-4
  deterministic: true
  temperature: 0.0
  top_p: 1.0
  max_tokens: 4000

# Output Configuration
output:
  formats:
    - markdown
    - latex
    - html
  directory: thesis_output
  include_cache: true
  save_intermediate: true

# Processing Configuration
processing:
  use_cache: true
  cache_version: v1.1
  human_checkpoints: true
  theme_count: 5
  max_gaps: 5
  max_research_questions: 4

# Template Configuration
templates:
  directory: templates/thesis
  custom_filters: true
  
# Quality Settings
quality:
  min_theme_length: 200
  min_gap_description: 150
  citation_style: apa
  academic_rigor: phd

# Performance Settings
performance:
  parallel_processing: false
  max_retries: 3
  timeout_seconds: 120
"""
    
    config_file = Path('src/thesis/config/thesis_config.yaml')
    
    # Check if config already exists
    if config_file.exists():
        print(f"✅ Configuration already exists: {config_file}")
        return config_file
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Created default configuration: {config_file}")
    return config_file

def create_requirements_file():
    """Check if requirements are in main requirements.txt."""
    req_file = Path('requirements.txt')
    
    if req_file.exists():
        with open(req_file, 'r') as f:
            content = f.read()
            if 'jsonschema' in content and 'Thesis Generation Features' in content:
                print(f"✅ Thesis dependencies already in: {req_file}")
                return req_file
    
    print(f"⚠️  Please ensure thesis dependencies are in: {req_file}")
    print("   Required packages: jsonschema, python-dateutil, matplotlib, seaborn")
    return req_file

def main():
    """Main setup and dependency check."""
    print("Enhanced Thesis Generator - Dependency Check")
    print("=" * 50)
    
    # Check Python dependencies
    print("\n📦 Python Dependencies:")
    missing_python = check_python_dependencies()
    
    # Check system dependencies
    print("\n🔧 System Dependencies:")
    missing_system = check_system_dependencies()
    
    # Check Eunice integration
    print("\n🤖 AI Integration:")
    eunice_available = check_eunice_integration()
    
    # Create configuration files
    print("\n📄 Configuration Files:")
    config_file = create_default_config()
    req_file = create_requirements_file()
    
    # Summary and recommendations
    print("\n" + "=" * 50)
    print("SETUP SUMMARY")
    print("=" * 50)
    
    if missing_python:
        print("\n❌ Missing Python packages:")
        for package, cmd in missing_python:
            print(f"   {cmd}")
        print("\nOr install all at once:")
        print(f"   pip install -r requirements.txt")
    else:
        print("\n✅ All Python dependencies satisfied")
    
    if missing_system:
        print("\n❌ Missing system dependencies:")
        for cmd, desc in missing_system:
            print(f"   {cmd}: {desc}")
        print("\nInstallation instructions:")
        print("   macOS: brew install pandoc")
        print("   Ubuntu: sudo apt-get install pandoc texlive-xetex")
        print("   Windows: Download from https://pandoc.org/installing.html")
    else:
        print("\n✅ All system dependencies satisfied")
    
    if not eunice_available:
        print("\n⚠️  Eunice AI clients not available")
        print("   The system will use direct OpenAI integration")
        print("   Ensure OPENAI_API_KEY environment variable is set")
    else:
        print("\n✅ Eunice AI integration available")
    
    print("\n🚀 READY TO USE:")
    print(f"   python thesis_cli.py input.json")
    print(f"   python thesis_cli.py input.json -c {config_file}")
    
    print("\n📚 DOCUMENTATION:")
    print("   python thesis_cli.py --help")
    print("   See docs/Thesis_Generation_Documentation.md for detailed documentation")

if __name__ == "__main__":
    main()
