"""
MCP Test Client for Persona System

This client tests the persona consultation endpoints in the MCP server.
It demonstrates the full capability of the persona consultation system including:

- Persona capability discovery
- Expert consultation requests with context
- Consultation history retrieval
- Error handling for unknown expertise areas
- Real-time WebSocket communication

Usage:
    python tests/test_mcp_persona_client.py

Prerequisites:
    - MCP server running on localhost:9000
    - Persona system initialized
    - AI API keys configured (OpenAI, xAI, etc.)
"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union


class MCPTestClient:
    """Test client for MCP server persona functionality"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self.websocket: Optional[Any] = None
        self.client_id = f"test_client_{uuid.uuid4().hex[:8]}"
        
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        try:
            uri = f"ws://{self.host}:{self.port}/ws"
            print(f"🔌 Connecting to MCP server at {uri}...")
            self.websocket = await websockets.connect(uri)
            
            # Wait for connection confirmation
            response = await self.websocket.recv()
            connection_data = json.loads(response)
            
            if connection_data.get('type') == 'connection_established':
                print("✅ Connected to MCP server")
                return True
            else:
                print(f"❌ Unexpected connection response: {connection_data}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Disconnected from MCP server")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> None:
        """Send a message to the MCP server"""
        if not self.websocket:
            raise Exception("Not connected to MCP server")
        
        message = {
            'type': message_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def receive_message(self) -> Dict[str, Any]:
        """Receive a message from the MCP server"""
        if not self.websocket:
            raise Exception("Not connected to MCP server")
        
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def request_persona_consultation(
        self, 
        expertise_area: str, 
        query: str, 
        context: Optional[Dict[str, Any]] = None,
        preferred_persona: Optional[str] = None
    ) -> Dict[str, Any]:
        """Request a persona consultation"""
        request_id = f"consultation_{uuid.uuid4().hex[:8]}"
        
        consultation_request = {
            'request_id': request_id,
            'expertise_area': expertise_area,
            'query': query,
            'context': context or {},
            'preferred_persona': preferred_persona,
            'priority': 'normal',
            'created_at': datetime.now().isoformat()
        }
        
        print(f"📋 Requesting persona consultation...")
        print(f"   Request ID: {request_id}")
        print(f"   Expertise Area: {expertise_area}")
        print(f"   Preferred Persona: {preferred_persona or 'auto-select'}")
        
        await self.send_message('persona_consultation_request', consultation_request)
        
        # Wait for response
        response = await self.receive_message()
        
        if response.get('type') == 'persona_consultation_response':
            return response.get('data', {})
        else:
            raise Exception(f"Unexpected response type: {response.get('type')}")
    
    async def get_persona_capabilities(self) -> Dict[str, Any]:
        """Get information about available personas"""
        response_id = f"capabilities_{uuid.uuid4().hex[:8]}"
        
        print("🔍 Requesting persona capabilities...")
        await self.send_message('get_persona_capabilities', {'response_id': response_id})
        
        response = await self.receive_message()
        
        if response.get('type') == 'persona_capabilities_response':
            return response.get('data', {}).get('capabilities', {})
        else:
            raise Exception(f"Unexpected response type: {response.get('type')}")
    
    async def get_persona_history(self, limit: int = 5) -> Dict[str, Any]:
        """Get persona consultation history"""
        response_id = f"history_{uuid.uuid4().hex[:8]}"
        
        print("📊 Requesting persona consultation history...")
        await self.send_message('get_persona_history', {
            'response_id': response_id,
            'limit': limit
        })
        
        response = await self.receive_message()
        
        if response.get('type') == 'persona_history_response':
            return response.get('data', {}).get('history', {})
        else:
            raise Exception(f"Unexpected response type: {response.get('type')}")


async def test_persona_system():
    """Test the persona system via MCP client"""
    client = MCPTestClient()
    
    try:
        # Connect to server
        if not await client.connect():
            print("❌ Failed to connect to MCP server. Make sure it's running.")
            return
        
        print("\\n" + "="*60)
        print("🧠 MCP PERSONA SYSTEM TEST")
        print("="*60)
        
        # Test 1: Get persona capabilities
        print("\\n🔍 TEST 1: Get Persona Capabilities")
        print("-" * 40)
        
        capabilities = await client.get_persona_capabilities()
        print(f"Available personas: {len(capabilities.get('available_personas', {}))}")
        
        for persona_name, persona_info in capabilities.get('available_personas', {}).items():
            print(f"  ✓ {persona_name}: {persona_info.get('capabilities', [])}")
        
        # Test 2: Request neurobiologist consultation
        print("\\n🧬 TEST 2: Neurobiologist Consultation")
        print("-" * 40)
        
        consultation_response = await client.request_persona_consultation(
            expertise_area="neuron_preparation",
            query="What are the key considerations for maintaining hippocampal neurons in culture for LTP experiments?",
            context={
                "experiment_type": "LTP",
                "neuron_type": "hippocampal",
                "culture_duration": "21+ days"
            },
            preferred_persona="neurobiologist"
        )
        
        print(f"✅ Consultation Status: {consultation_response.get('status')}")
        print(f"🎯 Confidence: {consultation_response.get('confidence', 'N/A')}%")
        print(f"🤖 Persona: {consultation_response.get('persona_type')}")
        
        if consultation_response.get('expert_response'):
            response_preview = consultation_response['expert_response'][:200] + "..."
            print(f"📝 Response Preview: {response_preview}")
        
        if consultation_response.get('error'):
            print(f"❌ Error: {consultation_response['error']}")
        
        # Test 3: Get consultation history
        print("\\n📊 TEST 3: Consultation History")
        print("-" * 40)
        
        history = await client.get_persona_history()
        
        # Handle both possible data structures
        recent_consultations = history.get('recent_consultations', {})
        consultations = history.get('consultations', [])
        statistics = history.get('statistics', {})
        
        # Convert dict to list if needed
        if isinstance(recent_consultations, dict):
            consultation_list = list(recent_consultations.values())
        else:
            consultation_list = consultations
        
        print(f"Recent consultations: {len(consultation_list)}")
        print(f"Total consultations: {statistics.get('total_consultations', 0)}")
        print(f"Success rate: {statistics.get('success_rate', 0):.1%}")
        
        # Show recent consultations
        for i, consultation in enumerate(consultation_list[:3], 1):
            persona = consultation.get('persona_type', 'unknown')
            status = consultation.get('status', 'unknown')
            area = consultation.get('expertise_area', 'unknown')
            print(f"  {i}. {persona} - {status} - {area}")
        
        # Test 4: Test unknown expertise area
        print("\\n❓ TEST 4: Unknown Expertise Area")
        print("-" * 40)
        
        try:
            unknown_response = await client.request_persona_consultation(
                expertise_area="quantum_cooking",
                query="How do I cook pasta using quantum entanglement?",
                context={"difficulty": "impossible"}
            )
            
            print(f"Response Status: {unknown_response.get('status')}")
            if unknown_response.get('error'):
                print(f"Expected Error: {unknown_response['error']}")
            
        except Exception as e:
            print(f"Expected Exception: {e}")
        
        print("\\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()


async def main():
    """Main entry point"""
    print("🚀 Starting MCP Persona System Test Client")
    await test_persona_system()


if __name__ == "__main__":
    asyncio.run(main())
