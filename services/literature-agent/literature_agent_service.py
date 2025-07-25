#!/usr/bin/env python3
"""
Literature Agent Service - Enhanced MCP Client
Phase 3.2 - Containerized Literature Agent

This service runs a Literature Agent as an MCP client that connects to
the Enhanced MCP Server for coordinated literature search tasks.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, Any, Optional

import websockets
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class SimpleLiteratureAgent:
    """Simplified Literature Agent for MCP integration testing"""
    
    def __init__(self):
        self.agent_id = os.getenv("AGENT_ID", "literature-agent-001")
        self.agent_type = os.getenv("AGENT_TYPE", "literature")
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "ws://localhost:9000")
        self.websocket = None
        self.running = False
        
        # Literature search capabilities
        self.capabilities = [
            "academic_search",
            "web_search", 
            "content_extraction",
            "result_ranking"
        ]
        
    async def connect_to_mcp_server(self, max_retries=5, retry_delay=3):
        """Connect to Enhanced MCP Server with retry logic"""
        logger.info("Connecting to Enhanced MCP Server", 
                   url=self.mcp_server_url, 
                   agent_id=self.agent_id)
        
        for attempt in range(max_retries):
            try:
                self.websocket = await websockets.connect(self.mcp_server_url)
                logger.info("Connected to Enhanced MCP Server successfully", 
                           attempt=attempt + 1)
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed", 
                              error=str(e), 
                              retry_in=retry_delay if attempt < max_retries - 1 else None)
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error("Failed to connect to MCP Server after all retries")
                    return False
        
        return False
    
    async def register_agent(self):
        """Register this agent with the Enhanced MCP Server"""
        if not self.websocket:
            logger.error("No WebSocket connection for registration")
            return False
        
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "max_concurrent": 3,
            "timeout": 300
        }
        
        try:
            await self.websocket.send(json.dumps(registration_message))
            logger.info("Sent agent registration", agent_id=self.agent_id)
            
            # Wait for confirmation
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "registration_confirmed":
                logger.info("Agent registration confirmed", 
                           server_id=response_data.get("server_id"))
                return True
            else:
                logger.error("Unexpected registration response", response=response_data)
                return False
                
        except Exception as e:
            logger.error("Agent registration failed", error=str(e))
            return False
    
    async def send_heartbeat(self):
        """Send heartbeat to Enhanced MCP Server"""
        if not self.websocket:
            return
        
        heartbeat_message = {
            "type": "heartbeat",
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "metrics": {
                "active_tasks": 0,
                "completed_tasks": 0,
                "memory_usage": "120MB"
            }
        }
        
        try:
            await self.websocket.send(json.dumps(heartbeat_message))
            logger.debug("Sent heartbeat", agent_id=self.agent_id)
        except Exception as e:
            logger.error("Failed to send heartbeat", error=str(e))
    
    async def process_literature_search(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a literature search task (simplified implementation)"""
        query = task_data.get("query", "")
        max_results = task_data.get("max_results", 5)
        
        logger.info("Processing literature search", 
                   query=query, 
                   max_results=max_results)
        
        # Simulate literature search results
        # In a real implementation, this would call actual search APIs
        mock_results = [
            {
                "title": f"Research Paper on {query} - Study {i+1}",
                "authors": ["Dr. Smith", "Dr. Johnson"],
                "abstract": f"This paper explores {query} through comprehensive analysis...",
                "url": f"https://example.com/paper{i+1}",
                "year": 2024,
                "citations": 42 + i,
                "relevance_score": 0.95 - (i * 0.1)
            }
            for i in range(min(max_results, 3))
        ]
        
        # Simulate processing delay
        await asyncio.sleep(1)
        
        result = {
            "status": "completed",
            "query": query,
            "results_count": len(mock_results),
            "results": mock_results,
            "processing_time": "1.2s",
            "agent_id": self.agent_id
        }
        
        logger.info("Literature search completed", 
                   results_count=len(mock_results))
        
        return result
    
    async def handle_messages(self):
        """Handle incoming messages from Enhanced MCP Server"""
        logger.info("Starting message handler")
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    logger.debug("Received message", type=message_type, data=data)
                    
                    if message_type == "task_submit":
                        # Process literature search task
                        task_id = data.get("task_id")
                        task_data = data.get("payload", {})
                        
                        logger.info("Received literature search task", task_id=task_id)
                        
                        # Process the task
                        result = await self.process_literature_search(task_data)
                        
                        # Send result back
                        response_message = {
                            "type": "task_result",
                            "task_id": task_id,
                            "agent_id": self.agent_id,
                            "status": "completed",
                            "result": result
                        }
                        
                        await self.websocket.send(json.dumps(response_message))
                        logger.info("Sent task result", task_id=task_id)
                    
                    elif message_type == "heartbeat_ack":
                        logger.debug("Received heartbeat acknowledgment")
                    
                    elif message_type == "shutdown":
                        logger.info("Received shutdown command")
                        self.running = False
                        break
                    
                    else:
                        logger.warning("Unknown message type", type=message_type)
                
                except json.JSONDecodeError:
                    logger.error("Invalid JSON message received")
                except Exception as e:
                    logger.error("Error processing message", error=str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error("Message handling error", error=str(e))
    
    async def heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            await self.send_heartbeat()
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
    
    async def start(self):
        """Start the Literature Agent service"""
        logger.info("Starting Literature Agent Service", 
                   agent_id=self.agent_id,
                   mcp_server_url=self.mcp_server_url)
        
        # Connect to MCP Server
        if not await self.connect_to_mcp_server():
            logger.error("Failed to connect to MCP Server")
            return False
        
        # Register agent
        if not await self.register_agent():
            logger.error("Failed to register agent")
            return False
        
        self.running = True
        
        # Start background tasks
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        message_task = asyncio.create_task(self.handle_messages())
        
        logger.info("Literature Agent Service started successfully")
        
        try:
            # Wait for shutdown signal
            await asyncio.gather(heartbeat_task, message_task)
        except asyncio.CancelledError:
            logger.info("Service tasks cancelled")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()
        
        logger.info("Literature Agent Service stopped")
        return True
    
    async def stop(self):
        """Stop the Literature Agent service"""
        self.running = False
        if self.websocket:
            await self.websocket.close()


# Global agent instance for signal handling
agent_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal", signal=signum)
    if agent_instance:
        asyncio.create_task(agent_instance.stop())


async def main():
    """Main entry point"""
    global agent_instance
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start agent
    agent_instance = SimpleLiteratureAgent()
    
    try:
        await agent_instance.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Service error", error=str(e))
    finally:
        if agent_instance:
            await agent_instance.stop()


if __name__ == "__main__":
    print("🚀 Literature Agent Service - Enhanced MCP Client")
    print("Phase 3.2 - Connecting to Enhanced MCP Server")
    print("="*60)
    
    asyncio.run(main())
