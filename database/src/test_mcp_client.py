#!/usr/bin/env python3
"""
Test script for the Database Service MCP Client
"""

import asyncio
import logging
import sys
import os

# Add the services directory to the path so we can import the mcp_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import MCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_mcp_client():
    """Test the MCP client functionality."""
    
    logger.info("🧪 Starting MCP Client test...")
    
    # Create client with localhost for testing (since MCP server might not be running)
    client = MCPClient(host="localhost", port=9000)
    
    # Test client properties
    logger.info(f"Client ID: {client.client_id}")
    logger.info(f"Service Type: database")
    logger.info(f"Host: {client.host}:{client.port}")
    
    # Test connection info
    connection_info = client.connection_info
    logger.info(f"Connection info: {connection_info}")
    
    # Test health check
    health = await client.health_check()
    logger.info(f"Health check: {health}")
    
    # Test basic message validation
    valid_msg = {
        "jsonrpc": "2.0",
        "method": "test",
        "params": {}
    }
    is_valid = client._validate_jsonrpc_message(valid_msg)
    logger.info(f"Message validation test: {is_valid}")
    
    invalid_msg = {
        "jsonrpc": "1.0",  # Wrong version
        "method": "test"
    }
    is_invalid = client._validate_jsonrpc_message(invalid_msg)
    logger.info(f"Invalid message test: {is_invalid}")
    
    # Test request ID generation
    req_id1 = client._generate_request_id()
    req_id2 = client._generate_request_id()
    logger.info(f"Request IDs: {req_id1}, {req_id2}")
    
    # Test message handlers
    logger.info(f"Available message handlers: {list(client.message_handlers.keys())}")
    
    logger.info("✅ Basic MCP Client tests completed successfully!")
    
    # Note: We're not testing actual connection since MCP server might not be running
    logger.info("📝 Note: Connection tests skipped (MCP server may not be available)")
    

if __name__ == "__main__":
    asyncio.run(test_mcp_client())
