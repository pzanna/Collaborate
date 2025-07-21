"""
Main entry point for the Eunice application
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from .config.config_manager import ConfigManager
from .storage.hierarchical_database import HierarchicalDatabaseManager


def main():
    """Main entry point for the Eunice application."""
    # Ensure directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    
    # Initialize configuration
    config_manager = ConfigManager()
    
    # Set up logging
    config_manager.setup_logging()
    
    # Initialize database
    db_manager = HierarchicalDatabaseManager(config_manager.config.storage.database_path)
    
    print("✓ Eunice application initialized successfully")
    print("📋 Use web_server.py to start the web interface")
    print("🤖 Use agent_launcher.py to start research agents")
    print("🔧 Use mcp_server.py to start the MCP server")


if __name__ == "__main__":
    main()
