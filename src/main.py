"""
Main entry point for the Collaborate application
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.interface import cli
from config.config_manager import ConfigManager
from storage.database import DatabaseManager


def main():
    """Main entry point for the Collaborate application."""
    # Ensure directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    
    # Initialize configuration
    config_manager = ConfigManager()
    
    # Initialize database
    db_manager = DatabaseManager(config_manager.config.storage.database_path)
    
    # Run CLI
    cli()


if __name__ == "__main__":
    main()
