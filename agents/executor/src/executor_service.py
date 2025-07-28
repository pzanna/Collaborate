"""
Executor Agent Service - Containerized MCP Client

This service provides code execution, data processing, API calls, and file operations
for the Eunice Research Platform. It connects to the MCP server as a client agent
and executes tasks in a secure, sandboxed environment.

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic

Architecture:
- Connects to MCP Server as a client agent via WebSocket
- Receives execution tasks from MCP Server
- Provides sandboxed code execution capabilities
- Handles file operations within restricted work directory
- Makes HTTP API calls and processes data
- Returns execution results through MCP protocol
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import aiohttp
import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

# Configuration
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8008"))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://localhost:9000")
AGENT_TYPE = os.getenv("AGENT_TYPE", "executor")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config_path = Path(__file__).parent.parent / "config" / "config.json"
config = {}

if config_path.exists():
    with open(config_path, 'r') as f:
        config = json.load(f)
        logger.info("Configuration loaded from config.json")
else:
    logger.warning("config.json not found, using environment variables only")


class ExecutorAgentService:
    """Containerized Executor Agent Service as MCP Client"""
    
    def __init__(self):
        self.websocket = None
        self.is_connected = False
        self.should_run = True
        self.start_time = asyncio.get_event_loop().time()
        self.agent_id = f"executor-{os.getpid()}"
        
        # Execution configuration
        self.sandbox_enabled = config.get("sandbox", {}).get("enabled", True)
        self.max_execution_time = config.get("execution", {}).get("max_time", 30)
        self.allowed_imports = set(config.get("execution", {}).get("allowed_imports", [
            "pandas", "numpy", "json", "csv", "datetime", "math", "statistics",
            "requests", "urllib", "pathlib", "os", "sys", "io", "collections"
        ]))

        # Working directory for temporary files
        self.work_dir = Path(tempfile.mkdtemp(prefix="executor_"))
        
        # HTTP session for API calls
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Load capabilities from config
        self.capabilities = config.get("capabilities", [
            "execute_code", "make_api_call", "process_data", "read_file",
            "write_file", "run_command", "transform_data", "validate_data",
            "execute_research"
        ])
        
        if not self.capabilities:
            logger.error("No capabilities found in config file!")
            raise ValueError("Configuration must include capabilities")
        
        logger.info(f"Executor Agent Service initialized with ID: {self.agent_id}")
        logger.info(f"Loaded capabilities: {self.capabilities}")
        logger.info(f"Work directory: {self.work_dir}")
    
    async def start(self):
        """Start the executor agent service."""
        logger.info("Starting Executor Agent Service")
        
        # Initialize HTTP session
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Eunice-Research-Platform/1.0'}
        )
        
        # Setup signal handlers
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, self._signal_handler)
        
        # Connect to MCP server
        await self.connect_to_mcp_server()
        
        # Start listening for tasks
        await self.listen_for_tasks()
    
    async def stop(self):
        """Stop the executor agent service."""
        logger.info("Stopping Executor Agent Service")
        self.should_run = False
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
        
        # Close WebSocket connection
        if self.websocket:
            await self.websocket.close()
        
        # Cleanup work directory
        try:
            import shutil
            shutil.rmtree(self.work_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up work directory: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.should_run = False
    
    async def connect_to_mcp_server(self):
        """Connect to MCP server via WebSocket"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to MCP server at {MCP_SERVER_URL} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    MCP_SERVER_URL,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10
                )
                
                self.is_connected = True
                logger.info("Successfully connected to MCP server")
                
                # Register agent with MCP server
                await self.register_agent()
                return
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Could not connect to MCP server")
                    raise
    
    async def register_agent(self):
        """Register this agent with the MCP server"""
        if not self.websocket:
            logger.error("Cannot register agent: no websocket connection")
            return
            
        registration_message = {
            "jsonrpc": "2.0",
            "method": "agent/register",
            "params": {
                "agent_id": self.agent_id,
                "agent_type": AGENT_TYPE,
                "capabilities": self.capabilities,
                "service_info": {
                    "port": SERVICE_PORT,
                    "health_endpoint": f"http://localhost:{SERVICE_PORT}/health"
                }
            },
            "id": f"register_{self.agent_id}"
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered agent {self.agent_id} with MCP server")
    
    async def listen_for_tasks(self):
        """Listen for tasks from MCP server"""
        if not self.websocket:
            logger.error("Cannot listen for tasks: no websocket connection")
            return
            
        logger.info("Starting to listen for tasks from MCP server")
        
        try:
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.handle_mcp_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.is_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.is_connected = False
    
    async def handle_mcp_message(self, data: Dict[str, Any]):
        """Handle incoming MCP message"""
        if not self.websocket:
            logger.error("Cannot handle MCP message: no websocket connection")
            return
            
        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")
        
        logger.info(f"Received MCP message: {method}")
        
        try:
            if method == "task/execute":
                result = await self.execute_task(params)
            elif method == "agent/ping":
                result = {"status": "alive", "timestamp": datetime.now().isoformat()}
            elif method == "agent/status":
                result = await self.get_agent_status()
            else:
                result = {"error": f"Unknown method: {method}"}
            
            # Send response
            if msg_id:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }
                await self.websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error handling MCP message: {e}")
            
            if msg_id:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                await self.websocket.send(json.dumps(error_response))
    
    async def execute_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task via MCP protocol"""
        task_type = params.get("task_type")
        task_data = params.get("data", {})
        
        logger.info(f"Executing task: {task_type}")
        
        if task_type == "execute_code":
            return await self.execute_code(task_data)
        elif task_type == "make_api_call":
            return await self.make_api_call(task_data)
        elif task_type == "process_data":
            return await self.process_data(task_data)
        elif task_type == "read_file":
            return await self.read_file(task_data)
        elif task_type == "write_file":
            return await self.write_file(task_data)
        elif task_type == "run_command":
            return await self.run_command(task_data)
        else:
            return {
                "status": "error",
                "message": f"Unknown task type: {task_type}",
                "available_tasks": list(self.capabilities)
            }
    
    async def execute_code(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code in a sandboxed environment"""
        try:
            code = data.get("code", "")
            if not code:
                return {"status": "error", "message": "No code provided"}
            
            # Create temporary file for code execution
            temp_file = self.work_dir / f"exec_{uuid.uuid4()}.py"
            
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(code)
            
            # Execute code with timeout
            try:
                result = await asyncio.wait_for(
                    self._run_python_code(temp_file),
                    timeout=self.max_execution_time
                )
                
                return {
                    "status": "completed",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
            except asyncio.TimeoutError:
                return {
                    "status": "error",
                    "message": f"Code execution timed out after {self.max_execution_time} seconds",
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                # Cleanup
                if temp_file.exists():
                    temp_file.unlink()
                    
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _run_python_code(self, code_file: Path) -> Dict[str, Any]:
        """Run Python code file and capture output"""
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(code_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else "",
                "return_code": process.returncode
            }
            
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
    
    async def make_api_call(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP API call"""
        try:
            url = data.get("url", "")
            method = data.get("method", "GET").upper()
            headers = data.get("headers", {})
            params = data.get("params", {})
            json_data = data.get("json")
            
            if not url:
                return {"status": "error", "message": "No URL provided"}
            
            if not self.http_session:
                return {"status": "error", "message": "HTTP session not initialized"}
            
            async with self.http_session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data
            ) as response:
                
                response_data = {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "content": await response.text()
                }
                
                # Try to parse JSON if possible
                try:
                    response_data["json"] = await response.json()
                except:
                    pass
                
                return {
                    "status": "completed",
                    "response": response_data,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error making API call: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data using pandas or other libraries"""
        try:
            operation = data.get("operation", "")
            input_data = data.get("data", [])
            
            if operation == "csv_to_json":
                # Convert CSV data to JSON
                import pandas as pd
                import io
                
                if isinstance(input_data, str):
                    df = pd.read_csv(io.StringIO(input_data))
                else:
                    df = pd.DataFrame(input_data)
                
                result = df.to_json(orient='records')
                
            elif operation == "json_to_csv":
                # Convert JSON data to CSV
                import pandas as pd
                
                df = pd.DataFrame(input_data)
                result = df.to_csv(index=False)
                
            elif operation == "statistics":
                # Calculate basic statistics
                import pandas as pd
                
                df = pd.DataFrame(input_data)
                result = df.describe().to_dict()
                
            else:
                return {
                    "status": "error",
                    "message": f"Unknown operation: {operation}",
                    "available_operations": ["csv_to_json", "json_to_csv", "statistics"]
                }
            
            return {
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def read_file(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Read file from work directory"""
        try:
            filename = data.get("filename", "")
            if not filename:
                return {"status": "error", "message": "No filename provided"}
            
            file_path = self.work_dir / filename
            
            if not file_path.exists():
                return {"status": "error", "message": f"File {filename} not found"}
            
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            
            return {
                "status": "completed",
                "content": content,
                "filename": filename,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def write_file(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Write file to work directory"""
        try:
            filename = data.get("filename", "")
            content = data.get("content", "")
            
            if not filename:
                return {"status": "error", "message": "No filename provided"}
            
            file_path = self.work_dir / filename
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)
            
            return {
                "status": "completed",
                "filename": filename,
                "size": len(content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run shell command (restricted)"""
        try:
            command = data.get("command", "")
            if not command:
                return {"status": "error", "message": "No command provided"}
            
            # Security: only allow specific safe commands
            allowed_commands = ["ls", "pwd", "cat", "echo", "grep", "wc", "head", "tail"]
            cmd_parts = command.split()
            
            if not cmd_parts or cmd_parts[0] not in allowed_commands:
                return {
                    "status": "error",
                    "message": f"Command '{cmd_parts[0] if cmd_parts else 'empty'}' not allowed",
                    "allowed_commands": allowed_commands
                }
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir)
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10  # 10 second timeout for commands
            )
            
            return {
                "status": "completed",
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else "",
                "return_code": process.returncode,
                "timestamp": datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "message": "Command execution timed out",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        uptime = asyncio.get_event_loop().time() - self.start_time
        
        return {
            "agent_id": self.agent_id,
            "agent_type": AGENT_TYPE,
            "status": "ready" if self.is_connected else "disconnected",
            "capabilities": self.capabilities,
            "uptime_seconds": int(uptime),
            "mcp_connected": self.is_connected,
            "work_directory": str(self.work_dir),
            "sandbox_enabled": self.sandbox_enabled,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
executor_service: Optional[ExecutorAgentService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if executor_service:
        return {
            "connected": executor_service.is_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if executor_service:
        return {
            "capabilities": executor_service.capabilities,
            "sandbox_enabled": executor_service.sandbox_enabled,
            "work_directory": str(executor_service.work_dir),
            "agent_id": executor_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="executor",
    agent_id="executor-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the executor agent service."""
    global executor_service
    
    try:
        # Initialize service
        executor_service = ExecutorAgentService()
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=SERVICE_HOST,
            port=SERVICE_PORT,
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Executor Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            executor_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Executor agent shutdown requested")
    except Exception as e:
        logger.error(f"Executor agent failed: {e}")
        sys.exit(1)
    finally:
        if executor_service:
            await executor_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
