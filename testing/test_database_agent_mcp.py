#!/usr/bin/env python3
"""
Test suite for the Database Agent's Enhanced MCP Client.

This test validates:
- Database agent MCP client functionality
- Integration with enhanced MCP server
- WebSocket connection management
- Task routing and execution
- Error handling and recovery
"""

import asyncio
import json
import logging
import os
import sys
import uuid
import websockets
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.database.base_mcp_agent import BaseMCPAgent

# Test configuration
MOCK_DATABASE_CONFIG = {
    "mcp_server_url": "ws://localhost:9000",
    "heartbeat_interval": 10,
    "ping_timeout": 5,
    "max_retries": 3,
    "base_retry_delay": 1,
    "task_timeout": 60
}

class MockDatabaseAgent(BaseMCPAgent):
    """Mock Database Agent for testing MCP functionality."""
    
    def get_capabilities(self) -> List[str]:
        """Return database agent capabilities."""
        return [
            "database/query",
            "database/insert", 
            "database/update",
            "database/delete",
            "database/schema",
            "database/backup",
            "database/restore"
        ]
    
    def setup_task_handlers(self):
        """Setup task handlers for database operations."""
        return {
            "database/query": self._handle_database_query,
            "database/insert": self._handle_database_insert,
            "database/update": self._handle_database_update,
            "database/delete": self._handle_database_delete,
            "database/schema": self._handle_database_schema,
            "database/backup": self._handle_database_backup,
            "database/restore": self._handle_database_restore
        }
    
    async def _handle_database_query(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database query request."""
        query = data.get("query", "")
        params = data.get("params", [])
        
        # Mock database query execution
        await asyncio.sleep(0.1)  # Simulate query time
        
        mock_results = [
            {"id": 1, "name": "Test Record 1", "status": "active"},
            {"id": 2, "name": "Test Record 2", "status": "inactive"}
        ]
        
        return {
            "success": True,
            "query": query,
            "params": params,
            "results": mock_results,
            "row_count": len(mock_results),
            "execution_time": 0.1
        }
    
    async def _handle_database_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database insert request."""
        table = data.get("table", "")
        values = data.get("values", {})
        
        # Mock insert operation
        await asyncio.sleep(0.05)
        
        return {
            "success": True,
            "table": table,
            "inserted_values": values,
            "inserted_id": 123,
            "affected_rows": 1
        }
    
    async def _handle_database_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database update request."""
        table = data.get("table", "")
        values = data.get("values", {})
        conditions = data.get("conditions", {})
        
        # Mock update operation
        await asyncio.sleep(0.05)
        
        return {
            "success": True,
            "table": table,
            "updated_values": values,
            "conditions": conditions,
            "affected_rows": 2
        }
    
    async def _handle_database_delete(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database delete request."""
        table = data.get("table", "")
        conditions = data.get("conditions", {})
        
        # Mock delete operation
        await asyncio.sleep(0.05)
        
        return {
            "success": True,
            "table": table,
            "conditions": conditions,
            "affected_rows": 1
        }
    
    async def _handle_database_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database schema request."""
        operation = data.get("operation", "describe")
        table = data.get("table", "")
        
        # Mock schema operation
        await asyncio.sleep(0.1)
        
        mock_schema = {
            "table": table,
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "name", "type": "VARCHAR(255)", "nullable": False},
                {"name": "status", "type": "VARCHAR(50)", "nullable": True}
            ],
            "indexes": [
                {"name": "idx_name", "columns": ["name"]}
            ]
        }
        
        return {
            "success": True,
            "operation": operation,
            "schema": mock_schema
        }
    
    async def _handle_database_backup(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database backup request."""
        backup_type = data.get("type", "full")
        destination = data.get("destination", "/backups/")
        
        # Mock backup operation
        await asyncio.sleep(0.2)
        
        return {
            "success": True,
            "backup_type": backup_type,
            "destination": destination,
            "backup_file": f"{destination}backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
            "size_mb": 150.5
        }
    
    async def _handle_database_restore(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database restore request."""
        backup_file = data.get("backup_file", "")
        target_db = data.get("target_database", "")
        
        # Mock restore operation
        await asyncio.sleep(0.3)
        
        return {
            "success": True,
            "backup_file": backup_file,
            "target_database": target_db,
            "restored_tables": 5,
            "restored_records": 1250
        }

class MockMCPServer:
    """Mock MCP Server for testing."""
    
    def __init__(self, host="localhost", port=9000):
        self.host = host
        self.port = port
        self.clients = {}
        self.pending_messages = {}
        self.message_handlers = {
            "agent_register": self._handle_agent_register,
            "agent_unregister": self._handle_agent_unregister,
            "heartbeat": self._handle_heartbeat,
            "heartbeat_ack": self._handle_heartbeat_ack
        }
    
    async def start(self):
        """Start mock MCP server."""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        print(f"Mock MCP Server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop mock MCP server."""
        if hasattr(self, 'server'):
            self.server.close()
            await self.server.wait_closed()
        print("Mock MCP Server stopped")
    
    async def _handle_client(self, websocket, path):
        """Handle client connections."""
        client_id = f"client-{uuid.uuid4().hex[:8]}"
        self.clients[client_id] = {
            "websocket": websocket,
            "agent_id": None,
            "agent_type": None,
            "capabilities": [],
            "connected_at": datetime.now(),
            "last_heartbeat": datetime.now()
        }
        
        print(f"Client {client_id} connected")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(client_id, data)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from {client_id}: {e}")
                except Exception as e:
                    print(f"Error processing message from {client_id}: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        finally:
            self.clients.pop(client_id, None)
    
    async def _process_message(self, client_id: str, data: Dict[str, Any]):
        """Process message from client."""
        message_type = data.get("type")
        if message_type in self.message_handlers:
            await self.message_handlers[message_type](client_id, data)
        else:
            print(f"Unknown message type from {client_id}: {message_type}")
    
    async def _handle_agent_register(self, client_id: str, data: Dict[str, Any]):
        """Handle agent registration."""
        agent_id = data.get("agent_id")
        agent_type = data.get("agent_type")
        capabilities = data.get("capabilities", [])
        
        self.clients[client_id].update({
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities
        })
        
        print(f"Agent registered: {agent_id} ({agent_type}) with {len(capabilities)} capabilities")
        
        # Send registration confirmation
        response = {
            "type": "registration_confirmed",
            "server_id": "mock-mcp-server",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._send_to_client(client_id, response)
    
    async def _handle_agent_unregister(self, client_id: str, data: Dict[str, Any]):
        """Handle agent unregistration."""
        agent_id = data.get("agent_id")
        print(f"Agent unregistered: {agent_id}")
    
    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat from agent."""
        self.clients[client_id]["last_heartbeat"] = datetime.now()
        agent_id = data.get("agent_id")
        
        # Send heartbeat ack
        response = {
            "type": "agent/ping",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._send_to_client(client_id, response)
    
    async def _handle_heartbeat_ack(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat acknowledgment."""
        # Just update last heartbeat time
        self.clients[client_id]["last_heartbeat"] = datetime.now()
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client."""
        if client_id in self.clients:
            try:
                websocket = self.clients[client_id]["websocket"]
                await websocket.send(json.dumps(message))
            except Exception as e:
                print(f"Error sending to {client_id}: {e}")
    
    async def send_task_to_agent(self, agent_type: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send task to specific agent type."""
        # Find agent by type
        target_client = None
        for client_id, client_info in self.clients.items():
            if client_info.get("agent_type") == agent_type:
                target_client = client_id
                break
        
        if not target_client:
            return {"error": f"No agent of type {agent_type} found"}
        
        task_id = str(uuid.uuid4())
        task_message = {
            "type": "task_request",
            "task_id": task_id,
            "task_type": task_type,
            "data": task_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store pending message for result tracking
        self.pending_messages[task_id] = {
            "client_id": target_client,
            "sent_at": datetime.now(),
            "completed": False,
            "result": None
        }
        
        await self._send_to_client(target_client, task_message)
        
        # Wait for result (with timeout)
        timeout = 30
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if self.pending_messages[task_id]["completed"]:
                result = self.pending_messages[task_id]["result"]
                self.pending_messages.pop(task_id)
                return result
            await asyncio.sleep(0.1)
        
        # Timeout
        self.pending_messages.pop(task_id)
        return {"error": "Task timeout"}

async def test_database_agent_functionality():
    """Test Database Agent MCP client functionality."""
    print("\n" + "="*60)
    print("TESTING DATABASE AGENT MCP CLIENT")
    print("="*60)
    
    # Start mock MCP server
    mock_server = MockMCPServer()
    await mock_server.start()
    
    try:
        # Give server time to start
        await asyncio.sleep(1)
        
        # Create and start database agent
        print("\n1. Creating Database Agent...")
        db_agent = MockDatabaseAgent("database", MOCK_DATABASE_CONFIG)
        
        # Start agent in background
        agent_task = asyncio.create_task(db_agent.start())
        
        # Give agent time to connect and register
        await asyncio.sleep(2)
        
        # Test 1: Verify agent registration
        print("\n2. Testing Agent Registration...")
        registered_agents = [
            client for client in mock_server.clients.values()
            if client.get("agent_type") == "database"
        ]
        assert len(registered_agents) == 1, "Database agent should be registered"
        print("✅ Database agent successfully registered")
        
        # Test 2: Test database query task
        print("\n3. Testing Database Query Task...")
        query_result = await mock_server.send_task_to_agent(
            "database", 
            "database/query",
            {
                "query": "SELECT * FROM users WHERE active = ?",
                "params": [True]
            }
        )
        assert "error" not in query_result, f"Query failed: {query_result.get('error')}"
        assert query_result.get("status") == "completed", "Query should complete successfully"
        assert "result" in query_result, "Query should return results"
        print("✅ Database query task completed successfully")
        
        # Test 3: Test database insert task
        print("\n4. Testing Database Insert Task...")
        insert_result = await mock_server.send_task_to_agent(
            "database",
            "database/insert", 
            {
                "table": "users",
                "values": {"name": "John Doe", "email": "john@example.com"}
            }
        )
        assert "error" not in insert_result, f"Insert failed: {insert_result.get('error')}"
        assert insert_result.get("status") == "completed", "Insert should complete successfully"
        print("✅ Database insert task completed successfully")
        
        # Test 4: Test database schema task
        print("\n5. Testing Database Schema Task...")
        schema_result = await mock_server.send_task_to_agent(
            "database",
            "database/schema",
            {
                "operation": "describe",
                "table": "users"
            }
        )
        assert "error" not in schema_result, f"Schema failed: {schema_result.get('error')}"
        assert schema_result.get("status") == "completed", "Schema should complete successfully"
        print("✅ Database schema task completed successfully")
        
        # Test 5: Test database backup task
        print("\n6. Testing Database Backup Task...")
        backup_result = await mock_server.send_task_to_agent(
            "database",
            "database/backup",
            {
                "type": "full",
                "destination": "/tmp/backups/"
            }
        )
        assert "error" not in backup_result, f"Backup failed: {backup_result.get('error')}"
        assert backup_result.get("status") == "completed", "Backup should complete successfully"
        print("✅ Database backup task completed successfully")
        
        # Test 6: Test invalid task type
        print("\n7. Testing Invalid Task Handling...")
        invalid_result = await mock_server.send_task_to_agent(
            "database",
            "invalid/task_type",
            {"test": "data"}
        )
        assert "error" not in invalid_result, "Should get proper error response"
        assert invalid_result.get("status") == "error", "Should indicate error status"
        print("✅ Invalid task properly handled")
        
        # Test 7: Test heartbeat functionality
        print("\n8. Testing Heartbeat Functionality...")
        agent_info = registered_agents[0]
        last_heartbeat = agent_info["last_heartbeat"]
        
        # Wait for heartbeat
        await asyncio.sleep(12)  # heartbeat_interval is 10 seconds
        
        current_heartbeat = agent_info["last_heartbeat"]
        assert current_heartbeat > last_heartbeat, "Heartbeat should be updated"
        print("✅ Heartbeat functionality working")
        
        print("\n" + "="*60)
        print("ALL DATABASE AGENT TESTS PASSED! ✅")
        print("="*60)
        
        # Stop agent
        db_agent.running = False
        agent_task.cancel()
        
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
    
    finally:
        await mock_server.stop()

def main():
    """Main test runner."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(test_database_agent_functionality())
        print("\n🎉 Database Agent MCP Client Integration Test: SUCCESS!")
        return 0
    except Exception as e:
        print(f"\n❌ Database Agent MCP Client Integration Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
