#!/usr/bin/env python3
"""
API Gateway Entry Point

This file serves as the main entry point for the API Gateway service,
importing and running the application from the src package.
"""

import sys
from pathlib import Path

# Add the current directory to Python path to enable src imports
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main application
if __name__ == "__main__":
    from src.main import sync_main
    sync_main()
