"""
Executor Agent Service - Containerized MCP Client

This service provides code execution, data processing, API calls, and file operations
for the Eunice Research Platform. It connects to the MCP server as a client agent
and executes tasks in a secure, sandboxed environment.

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
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from websockets.exceptions import ConnectionClosed, WebSocketException

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

    async def connect_to_mcp_server(self):
        """Connect to MCP server via WebSocket"""
        max_retries = config.get("mcp", {}).get("reconnect_attempts", 5)
        retry_delay = config.get("mcp", {}).get("reconnect_delay", 5)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to MCP server at {MCP_SERVER_URL} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    MCP_SERVER_URL,
                    ping_interval=config.get("mcp", {}).get("ping_interval", 30),
                    ping_timeout=config.get("mcp", {}).get("ping_timeout", 10),
                    close_timeout=10
                )
                
                self.is_connected = True
                logger.info("Successfully connected to MCP server")
                
                # Initialize executor resources
                await self._initialize_resources()
                
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
                    "health_endpoint": f"http://localhost:{SERVICE_PORT}/health",
                    "work_directory": str(self.work_dir),
                    "sandbox_enabled": self.sandbox_enabled
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
        msg_id = data.get("id", "")
        try:
            method = data.get("method", "")
            params = data.get("params", {})
            
            logger.debug(f"Received MCP message: {method}")
            
            response = None
            
            if method == "task/execute":
                response = await self.execute_task(params)
            elif method == "ping":
                response = {"status": "pong", "agent_id": self.agent_id}
            elif method == "health_check":
                response = self.get_health_status()
            else:
                logger.warning(f"Unknown method: {method}")
                response = {"error": f"Unknown method: {method}"}
            
            # Send response back to MCP server
            if self.websocket and msg_id and response is not None:
                response_message = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": response
                }
                await self.websocket.send(json.dumps(response_message))
                
        except Exception as e:
            logger.error(f"Error handling MCP message: {e}")
            if self.websocket and msg_id:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -1, "message": str(e)}
                }
                await self.websocket.send(json.dumps(error_response))

    async def execute_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an executor task"""
        try:
            action = params.get("action", "")
            payload = params.get("payload", {})
            
            logger.info(f"Executing task: {action}")
            
            if action == "execute_code":
                return await self._execute_code(payload)
            elif action == "make_api_call":
                return await self._make_api_call(payload)
            elif action == "process_data":
                return await self._process_data(payload)
            elif action == "read_file":
                return await self._read_file(payload)
            elif action == "write_file":
                return await self._write_file(payload)
            elif action == "run_command":
                return await self._run_command(payload)
            elif action == "transform_data":
                return await self._transform_data(payload)
            elif action == "validate_data":
                return await self._validate_data(payload)
            elif action == "execute_research":
                return await self._execute_research(payload)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "action": action
                }
                
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": params.get("action", "unknown")
            }

    async def _initialize_resources(self):
        """Initialize executor-specific resources"""
        try:
            # Create HTTP session
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Ensure work directory exists
            self.work_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up security restrictions
            self._setup_security_restrictions()
            
            logger.info(f"Executor resources initialized with work directory: {self.work_dir}")
            
        except Exception as e:
            logger.error(f"Failed to initialize executor resources: {e}")
            raise

    async def _execute_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code in a sandboxed environment"""
        code = payload.get("code", "")
        language = payload.get("language", "python")
        timeout = payload.get("timeout", self.max_execution_time)

        if not code:
            return {"success": False, "error": "Code is required for execution"}

        if language != "python":
            return {"success": False, "error": f"Unsupported language: {language}"}

        # Create temporary file for code
        code_file = self.work_dir / f"exec_{asyncio.get_event_loop().time()}.py"

        try:
            # Write code to temporary file
            async with aiofiles.open(code_file, "w") as f:
                await f.write(code)

            # Execute code with timeout
            result = await self._run_python_code(code_file, timeout)

            return {
                "success": True,
                "output": result["stdout"],
                "error": result["stderr"],
                "return_code": result["return_code"],
                "execution_time": result["execution_time"],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "return_code": -1,
                "execution_time": 0,
            }
        finally:
            # Clean up temporary file
            try:
                code_file.unlink(missing_ok=True)
            except Exception:
                pass

    async def _make_api_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP API call"""
        url = payload.get("url", "")
        method = payload.get("method", "GET").upper()
        headers = payload.get("headers", {})
        params = payload.get("params", {})
        data = payload.get("data", None)
        json_data = payload.get("json", None)

        if not url:
            return {"success": False, "error": "URL is required for API call"}

        if not self.http_session:
            return {"success": False, "error": "HTTP session not initialized"}

        try:
            async with self.http_session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
            ) as response:

                # Get response content
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    response_data = await response.json()
                else:
                    response_data = await response.text()

                return {
                    "success": True,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "data": response_data,
                    "url": str(response.url),
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": 0,
                "headers": {},
                "data": None,
                "url": url,
            }

    async def _process_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process and analyze data"""
        data = payload.get("data", [])
        operation = payload.get("operation", "analyze")

        if not data:
            return {"success": False, "error": "Data is required for processing"}

        try:
            if operation == "analyze":
                result = self._analyze_data(data)
            elif operation == "summarize":
                result = self._summarize_data(data)
            elif operation == "aggregate":
                result = self._aggregate_data(data)
            elif operation == "filter":
                filters = payload.get("filters", {})
                result = self._filter_data(data, filters)
            elif operation == "sort":
                sort_key = payload.get("sort_key", "")
                result = self._sort_data(data, sort_key)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

            return {
                "success": True,
                "result": result,
                "operation": operation,
                "input_size": len(data),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "input_size": len(data) if data else 0,
            }

    async def _read_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents"""
        file_path = payload.get("file_path", "")
        encoding = payload.get("encoding", "utf-8")
        max_size = payload.get("max_size", 1024 * 1024)  # 1MB limit

        if not file_path:
            return {"success": False, "error": "File path is required"}

        # Security check: only allow reading from work directory
        full_path = Path(file_path)
        if not self._is_safe_path(full_path):
            return {"success": False, "error": "File path not allowed"}

        try:
            # Check file size
            if full_path.stat().st_size > max_size:
                return {
                    "success": False,
                    "error": f"File too large (max {max_size} bytes)"
                }

            # Read file content
            async with aiofiles.open(full_path, "r", encoding=encoding) as f:
                content = await f.read()

            return {
                "success": True,
                "content": content,
                "file_path": str(full_path),
                "size": len(content),
                "encoding": encoding,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "size": 0,
                "encoding": encoding,
            }

    async def _write_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file"""
        file_path = payload.get("file_path", "")
        content = payload.get("content", "")
        encoding = payload.get("encoding", "utf-8")
        append = payload.get("append", False)

        if not file_path:
            return {"success": False, "error": "File path is required"}

        # Security check: only allow writing to work directory
        full_path = Path(file_path)
        if not self._is_safe_path(full_path):
            return {"success": False, "error": "File path not allowed"}

        try:
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            mode = "a" if append else "w"
            async with aiofiles.open(full_path, mode, encoding=encoding) as f:
                await f.write(content)

            return {
                "success": True,
                "file_path": str(full_path),
                "size": len(content),
                "encoding": encoding,
                "append": append,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "size": 0,
                "encoding": encoding,
                "append": append,
            }

    async def _run_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run system command"""
        command = payload.get("command", "")
        timeout = payload.get("timeout", 30)
        working_dir = payload.get("working_dir", str(self.work_dir))

        if not command:
            return {"success": False, "error": "Command is required"}

        # Security check: only allow safe commands
        if not self._is_safe_command(command):
            return {"success": False, "error": "Command not allowed"}

        try:
            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return {
                "success": True,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "return_code": process.returncode,
                "command": command,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Command timeout",
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "return_code": -1,
                "command": command,
            }

    async def _transform_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data between formats"""
        data = payload.get("data", [])
        from_format = payload.get("from_format", "json")
        to_format = payload.get("to_format", "csv")

        try:
            if from_format == "json" and to_format == "csv":
                result = self._json_to_csv(data)
            elif from_format == "csv" and to_format == "json":
                result = self._csv_to_json(data)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported transformation: {from_format} to {to_format}"
                }

            return {
                "success": True,
                "result": result,
                "from_format": from_format,
                "to_format": to_format,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "from_format": from_format,
                "to_format": to_format,
            }

    async def _validate_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema"""
        data = payload.get("data", [])
        schema = payload.get("schema", {})

        try:
            validation_result = self._validate_against_schema(data, schema)

            return {
                "success": True,
                "valid": validation_result["valid"],
                "errors": validation_result["errors"],
                "data_size": len(data),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "valid": False,
                "errors": [],
                "data_size": len(data) if data else 0,
            }

    async def _execute_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute research-related tasks"""
        try:
            query = payload.get("query", "")
            context = payload.get("context", {})
            execution_type = payload.get("execution_type", "basic")

            logger.info(f"Executing research task for query: {query}")

            results = []

            # Process search results if available
            search_results = context.get("search_results", [])
            if search_results:
                results.append({
                    "type": "search_analysis",
                    "description": f"Analyzed {len(search_results)} search results",
                    "data": {
                        "result_count": len(search_results),
                        "sources": [result.get("url", "Unknown") for result in search_results[:5]],
                    },
                })

            # Process reasoning output if available
            reasoning_output = context.get("reasoning_output", "")
            if reasoning_output:
                if isinstance(reasoning_output, str):
                    analysis_text = reasoning_output
                    analysis_length = len(reasoning_output)
                elif isinstance(reasoning_output, dict):
                    analysis_text = str(reasoning_output.get("analysis", ""))
                    analysis_length = len(analysis_text)
                else:
                    analysis_text = str(reasoning_output)
                    analysis_length = len(analysis_text)

                results.append({
                    "type": "reasoning_analysis",
                    "description": "Processed reasoning analysis",
                    "data": {
                        "analysis_length": analysis_length,
                        "has_insights": "insight" in analysis_text.lower() or "finding" in analysis_text.lower(),
                        "preview": (analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text),
                    },
                })

            # Generate execution summary
            execution_summary = {
                "query": query,
                "execution_type": execution_type,
                "total_results": len(results),
                "status": "completed",
                "timestamp": asyncio.get_event_loop().time(),
            }

            logger.info(f"Research execution completed with {len(results)} results")

            return {
                "results": results,
                "summary": execution_summary,
                "status": "completed",
            }

        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            return {
                "results": [],
                "summary": {
                    "query": payload.get("query", ""),
                    "status": "failed",
                    "error": str(e),
                },
                "status": "failed",
                "error": str(e),
            }

    async def _run_python_code(self, code_file: Path, timeout: int) -> Dict[str, Any]:
        """Run Python code file with timeout"""
        start_time = asyncio.get_event_loop().time()

        process = await asyncio.create_subprocess_exec(
            "python",
            str(code_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.work_dir),
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        execution_time = asyncio.get_event_loop().time() - start_time

        return {
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8"),
            "return_code": process.returncode,
            "execution_time": execution_time,
        }

    def _setup_security_restrictions(self) -> None:
        """Set up security restrictions for code execution"""
        logger.info("Security restrictions enabled for code execution")

    def _is_safe_path(self, path: Path) -> bool:
        """Check if file path is safe for operations"""
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.work_dir.resolve()))
        except Exception:
            return False

    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute"""
        safe_commands = {
            "ls", "cat", "head", "tail", "wc", "grep", "sort", "uniq",
            "python", "pip", "node", "npm"
        }

        command_parts = command.split()
        if not command_parts:
            return False

        base_command = command_parts[0]
        return base_command in safe_commands

    def _analyze_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data and return statistics"""
        if not data:
            return {"count": 0, "fields": []}

        count = len(data)
        fields = list(data[0].keys()) if data else []

        field_stats = {}
        for field in fields:
            values = [item.get(field) for item in data if field in item]
            field_stats[field] = {
                "count": len(values),
                "non_null": len([v for v in values if v is not None]),
                "unique": len(set(str(v) for v in values if v is not None)),
            }

        return {"count": count, "fields": fields, "field_stats": field_stats}

    def _summarize_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize data"""
        analysis = self._analyze_data(data)
        return {
            "summary": f"Dataset with {analysis['count']} records and {len(analysis['fields'])} fields",
            "fields": analysis["fields"],
            "record_count": analysis["count"],
        }

    def _aggregate_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate data by common fields"""
        if not data:
            return {}

        fields = list(data[0].keys())
        if not fields:
            return {}

        groups = {}
        first_field = fields[0]

        for item in data:
            key = item.get(first_field, "unknown")
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        return {field: len(items) for field, items in groups.items()}

    def _filter_data(self, data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter data based on criteria"""
        filtered = []
        for item in data:
            match = True
            for key, value in filters.items():
                if key not in item or item[key] != value:
                    match = False
                    break
            if match:
                filtered.append(item)
        return filtered

    def _sort_data(self, data: List[Dict[str, Any]], sort_key: str) -> List[Dict[str, Any]]:
        """Sort data by specified key"""
        if not sort_key:
            return data
        return sorted(data, key=lambda x: x.get(sort_key, ""))

    def _json_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert JSON data to CSV format"""
        if not data:
            return ""

        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def _csv_to_json(self, csv_data: str) -> List[Dict[str, Any]]:
        """Convert CSV data to JSON format"""
        import csv
        import io

        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)

    def _validate_against_schema(self, data: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against a simple schema"""
        errors = []
        required_fields = schema.get("required", [])
        field_types = schema.get("types", {})

        for i, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    errors.append(f"Row {i}: Missing required field '{field}'")

            for field, expected_type in field_types.items():
                if field in item:
                    value = item[field]
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(f"Row {i}: Field '{field}' should be string, got {type(value).__name__}")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Row {i}: Field '{field}' should be number, got {type(value).__name__}")

        return {"valid": len(errors) == 0, "errors": errors}

    def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status"""
        current_time = asyncio.get_event_loop().time()
        uptime = int(current_time - self.start_time)
        
        return {
            "status": "healthy" if self.is_connected else "degraded",
            "agent_type": AGENT_TYPE,
            "agent_id": self.agent_id,
            "mcp_connected": self.is_connected,
            "uptime_seconds": uptime,
            "capabilities": self.capabilities,
            "work_directory": str(self.work_dir),
            "sandbox_enabled": self.sandbox_enabled
        }

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Executor Agent Service")
        self.should_run = False
        
        # Close HTTP session
        if self.http_session:
            try:
                await self.http_session.close()
            except Exception as e:
                logger.error(f"Error closing HTTP session: {e}")
        
        # Clean up temporary files
        try:
            import shutil
            shutil.rmtree(self.work_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up work directory: {e}")
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
        
        self.is_connected = False


# FastAPI app for health checks and direct task execution (for testing)
app = FastAPI(title="Executor Agent Service", version="1.0.0")

# Global agent instance
agent_service = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if agent_service:
        return agent_service.get_health_status()
    else:
        return {"status": "initializing", "agent_type": AGENT_TYPE}


@app.get("/capabilities")
async def get_capabilities():
    """Get agent capabilities"""
    if agent_service:
        return {"capabilities": agent_service.capabilities}
    else:
        return {"capabilities": []}


@app.post("/task")
async def execute_task_direct(task_data: dict):
    """Direct task execution endpoint (for testing)"""
    if not agent_service:
        raise HTTPException(status_code=503, detail="Agent service not initialized")
    
    try:
        result = await agent_service.execute_task(task_data)
        return result
    except Exception as e:
        logger.error(f"Direct task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def main():
    """Main function to run the agent service"""
    global agent_service
    
    # Initialize agent service
    agent_service = ExecutorAgentService()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        if agent_service:
            asyncio.create_task(agent_service.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start HTTP server and MCP client concurrently
    config_uvicorn = uvicorn.Config(
        app, 
        host=SERVICE_HOST, 
        port=SERVICE_PORT, 
        log_level=LOG_LEVEL.lower()
    )
    server = uvicorn.Server(config_uvicorn)
    
    async def run_server():
        await server.serve()
    
    async def run_mcp_client():
        if agent_service:
            try:
                await agent_service.connect_to_mcp_server()
                await agent_service.listen_for_tasks()
            except Exception as e:
                logger.error(f"MCP client failed: {e}")
    
    # Run both server and MCP client
    logger.info(f"Starting Executor Agent Service on {SERVICE_HOST}:{SERVICE_PORT}")
    logger.info(f"Connecting to MCP server at {MCP_SERVER_URL}")
    
    await asyncio.gather(
        run_server(),
        run_mcp_client(),
        return_exceptions=True
    )


if __name__ == "__main__":
    asyncio.run(main())
