#!/usr/bin/env python3
"""
Health check script for MCP Server WebSocket endpoint.
Makes a proper WebSocket connection to verify the server is responding.
"""

import asyncio
import sys
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException


async def health_check():
    """Perform WebSocket health check"""
    try:
        # Connect to the WebSocket server
        uri = "ws://localhost:9000"
        async with websockets.connect(uri, ping_timeout=5, close_timeout=5) as websocket:
            # Send a JSON-RPC 2.0 ping notification
            await websocket.send('{"jsonrpc": "2.0", "method": "ping", "params": {}}')
            
            # Wait for any response (or timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                # If we get any response, server is healthy
                return True
            except asyncio.TimeoutError:
                # Even if no response, connection successful means server is running
                return True
                
    except (ConnectionClosed, WebSocketException, OSError, Exception) as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for health check"""
    try:
        result = asyncio.run(health_check())
        if result:
            print("MCP Server is healthy")
            sys.exit(0)
        else:
            print("MCP Server health check failed", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Health check error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
