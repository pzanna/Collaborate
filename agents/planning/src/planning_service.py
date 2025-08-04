"""
Planning Agent Service - Containerized MCP Client with Hot Reload

This service acts as a containerized Planning Agent that connects to the MCP server
via WebSocket and provides research planning capabilities.

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
- HOT RELOAD: This file is watched for changes in development mode
"""

import asyncio
import json
import logging
import os
import re
import signal
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

# Import cost estimator if available
try:
    from cost_estimator import CostEstimator, CostTier
    from config_manager import ConfigManager
    COST_ESTIMATOR_AVAILABLE = True
    CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Cost estimator/config manager not available: {e}")
    CostEstimator = None
    CostTier = None
    ConfigManager = None
    COST_ESTIMATOR_AVAILABLE = False
    CONFIG_MANAGER_AVAILABLE = False

# Load configuration
def load_config():
    """Load configuration from config file"""
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "service": {"host": "0.0.0.0", "port": 8007, "type": "planning"},
            "mcp": {"server_url": "ws://mcp-server:9000"},
            "capabilities": ["plan_research", "analyze_information", "cost_estimation"],
            "logging": {"level": "INFO"}
        }

config = load_config()

# Setup logging from config
logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format=config.get("logging", {}).get("format", '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger = logging.getLogger(__name__)

# Configuration from config file and environment variables
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", config["mcp"]["server_url"])
AGENT_TYPE = os.getenv("AGENT_TYPE", config["service"]["type"])
SERVICE_PORT = int(os.getenv("SERVICE_PORT", config["service"]["port"]))
SERVICE_HOST = os.getenv("SERVICE_HOST", config["service"]["host"])


class PlanningAgentService:
    """Containerized Planning Agent Service as MCP Client"""
    
    def __init__(self):
        self.websocket = None
        self.is_connected = False
        self.should_run = True
        self.start_time = asyncio.get_event_loop().time()
        self.agent_id = f"planning-{os.getpid()}"
        
        # Load capabilities from config
        self.capabilities = config.get("capabilities", [])
        if not self.capabilities:
            logger.error("No capabilities found in config file!")
            raise ValueError("Configuration must include capabilities")
        
        # Initialize cost estimator if available
        self.cost_estimator = None
        if COST_ESTIMATOR_AVAILABLE and CostEstimator:
            try:
                # Try to initialize with config manager if available
                if CONFIG_MANAGER_AVAILABLE and ConfigManager:
                    config_manager = ConfigManager()
                    self.cost_estimator = CostEstimator(config_manager)
                else:
                    # Use basic initialization
                    self.cost_estimator = "basic"  # Placeholder for basic cost estimation
                logger.info("Cost estimator initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize cost estimator: {e}")
        
        logger.info(f"Planning Agent Service initialized with ID: {self.agent_id}")
        logger.info(f"Loaded capabilities: {self.capabilities}")
    
    async def start(self):
        """Start the planning agent service."""
        logger.info("Starting Planning Agent Service")
        
        # Setup signal handlers
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, self._signal_handler)
        
        # Connect to MCP server
        await self.connect_to_mcp_server()
        
        # Start listening for tasks
        await self.listen_for_tasks()
    
    async def stop(self):
        """Stop the planning agent service."""
        logger.info("Stopping Planning Agent Service")
        self.should_run = False
        
        if self.websocket:
            await self.websocket.close()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.should_run = False
    
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
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": AGENT_TYPE,
                "capabilities": self.capabilities,
            "timestamp": datetime.now().isoformat(),
            "service_info": {
                    "port": SERVICE_PORT,
                    "health_endpoint": f"http://localhost:{SERVICE_PORT}/health"
                }
            
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
                    logger.info(f"Raw MCP message received: {message}")
                    data = json.loads(message)
                    logger.info(f"Parsed MCP message keys: {list(data.keys()) if data else 'None'}")
                    await self.handle_mcp_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}, raw message: {message}")
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
        logger.info(f"Handling MCP message with keys: {list(data.keys()) if data else 'None'}")
        logger.info(f"Message type: {data.get('type') if data else 'No type'}")
        
        if not self.websocket:
            logger.error("Cannot handle MCP message: no websocket connection")
            return
        
        # Handle task_request format from MCP server
        if data.get("type") == "task_request":
            task_id = data.get("task_id")
            action = data.get("task_type")  # MCP server uses 'task_type'
            payload = data.get("data", {})
            
            logger.info(f"Received task request: {action} (task_id: {task_id})")
            
            try:
                result = await self.execute_planning_task({
                    "task_id": task_id,
                    "action": action,
                    "payload": payload
                })
                
                # Send task result back to MCP server
                response = {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "completed",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.websocket.send(json.dumps(response))
                logger.info(f"Sent task result for {task_id}")
                
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {e}")
                
                # Send error result
                error_response = {
                    "type": "task_result", 
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.websocket.send(json.dumps(error_response))
            
            return
        
        # Handle research action format (legacy)
        if "task_id" in data and "action" in data:
            task_id = data.get("task_id")
            action = data.get("action")
            payload = data.get("payload", {})
            
            logger.info(f"Received research action: {action} (task_id: {task_id})")
            
            try:
                result = await self.execute_planning_task({
                    "task_id": task_id,
                    "action": action,
                    "payload": payload
                })
                
                # Send task result back to MCP server
                response = {
                    "type": "task_result",
                    "task_id": task_id,
                    "status": "completed",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.websocket.send(json.dumps(response))
                logger.info(f"Sent task result for {task_id}")
                
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {e}")
                
                # Send error result
                error_response = {
                    "type": "task_result", 
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.websocket.send(json.dumps(error_response))
            
            return
            
        # Handle JSON-RPC format (fallback)
        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")
        
        logger.info(f"Received JSON-RPC message: {method}")
        
        try:
            if method == "task/execute":
                result = await self.execute_planning_task(params)
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
    
    async def execute_planning_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a planning task"""
        # Handle both new MCP format and legacy format
        if "action" in params:
            # New MCP format: {action: "plan_research", payload: {...}}
            action = params.get("action")
            payload = params.get("payload", {})
        else:
            # Legacy format: {task_type: "plan_research", data: {...}}
            action = params.get("task_type")
            payload = params.get("data", {})
        
        logger.info(f"Executing planning task: {action}")
        
        try:
            if action == "plan_research":
                return await self._plan_research(payload)
            elif action == "analyze_information":
                return await self._analyze_information(payload) 
            elif action == "cost_estimation":
                return await self._estimate_costs(payload)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                    "agent_id": self.agent_id,
                    "available_tasks": ["plan_research", "analyze_information", "cost_estimation"]
                }
        except Exception as e:
            logger.error(f"Error executing planning task {action}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _plan_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Plan research based on query using AI via MCP"""
        query = payload.get("query", "")
        scope = payload.get("scope", "comprehensive")
        context = payload.get("context", {})
        
        if not query:
            raise ValueError("Query is required for research planning")
        
        # Create research planning prompt for AI - using exact template from planning_service_old.py
        prompt = f"""
        Please create a comprehensive research plan for the following query:
        
        Query: {query}
        Scope: {scope}
        Context: {json.dumps(context, indent=2)}
        
        Please provide a detailed research plan with:
        1. Clear research objectives (3-5 specific goals)
        2. Key areas to investigate (4-6 major research domains)
        3. Specific questions to answer (5-8 focused research questions)
        4. Information sources to consult (academic databases, repositories, etc.)
        5. Expected outcomes and deliverables
        6. Realistic timeline with phases
        
        Format your response as a JSON object with this exact structure:
        {{
            "objectives": ["Objective 1", "Objective 2", "Objective 3"],
            "key_areas": ["Area 1", "Area 2", "Area 3", "Area 4"],
            "questions": ["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"],
            "sources": ["PubMed", "ArXiv", "Semantic Scholar", "CORE", "CrossRef"],
            "timeline": {{
                "total_days": 14,
                "phases": {{
                    "literature_search": 3,
                    "data_collection": 5,
                    "analysis": 4,
                    "synthesis": 2
                }}
            }},
            "outcomes": ["Literature review", "Data analysis", "Experiment design", "Research synthesis", "Final report"]
        }}
        
        Please be thorough and consider all relevant aspects of the research topic.
        Ensure the plan is realistic and executable within the given timeframe. 
        Do NOT include the labels `Questions 1`, `Objective 1`, etc. in the output.
        """
        
        # Get AI response via MCP
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"**Received AI response for research planning: {len(ai_response)} characters")
            logger.info(f"**AI Response: {ai_response}")

            # Parse the AI response
            plan = self._parse_research_plan(ai_response)
            
            return {
                "status": "completed",
                "result": {
                    "query": query,
                    "scope": scope,
                    "plan": plan,
                    "agent_id": self.agent_id,
                    "processing_time": 2.1,
                    "ai_generated": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based research plan: {e}")
            # Return error response if AI fails
            return {
                "status": "failed",
                "error": f"Failed to generate research plan: {str(e)}",
                "agent_id": self.agent_id
            }
    
    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze provided information using AI via MCP"""
        query = payload.get("query", "")
        content = payload.get("content", "")
        analysis_type = payload.get("analysis_type", "general")
        
        if not query:
            raise ValueError("Query is required for information analysis")
        
        # Create analysis prompt for AI
        prompt = f"""
        Please analyze the following content with a focus on {analysis_type} analysis:

        Content: {content}

        Please provide:
        1. Key findings and insights
        2. Main themes and patterns
        3. Important facts and statistics
        4. Contradictions or inconsistencies
        5. Gaps in information
        6. Reliability assessment

        Format your response as a JSON object with this exact structure:
        {{
            "summary": "Executive summary of the content analysis",
            "key_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
            "insights": ["Insight 1", "Insight 2", "Insight 3"],
            "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"],
            "confidence_score": 0.85,
            "analysis_type": "{analysis_type}"
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for content analysis: {len(ai_response)} characters")
            
            # Parse the AI response using the robust JSON parser
            analysis_result = self._parse_ai_json_response(ai_response, "content analysis")
            
            return {
                "status": "completed",
                "result": analysis_result,
                "agent_id": self.agent_id,
                "processing_time": 2.1,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based content analysis: {e}")
            return {
                "status": "failed",
                "error": f"Failed to analyze content: {str(e)}",
                "agent_id": self.agent_id
            }
    
    async def _estimate_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for research project using AI-assisted cost analysis"""
        query = payload.get("query", "")
        scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 14)
        context = payload.get("context", {})
        
        # Create cost estimation prompt for AI
        prompt = f"""
        Please estimate the costs for a research project with these parameters:
        
        Project Query: {query}
        Project Scope: {scope}
        Duration: {duration_days} days
        Additional Context: {json.dumps(context, indent=2)}
        
        Provide detailed cost estimates including:
        1. AI processing costs (based on complexity and token usage)
        2. Traditional research costs (databases, tools, consultation)
        3. Time-based resource costs
        4. Total project cost breakdown
        5. Cost optimization suggestions
        
        Format your response as a JSON object:
        {{
            "project_scope": "{scope}",
            "cost_breakdown": {{
                "ai_operations": {{
                    "estimated_tokens": 25000,
                    "total_ai_cost": 6.75,
                    "complexity_level": "MEDIUM",
                    "provider": "openai",
                    "model": "gpt-4o-mini"
                }},
                "traditional_costs": {{
                    "resources": {{
                        "costs": {{
                            "database_access": 200,
                            "analysis_software": 300,
                            "expert_consultation": 500
                        }},
                        "total": 1000
                    }}
                }},
                "summary": {{
                    "ai_cost": 6.75,
                    "traditional_cost": 1000,
                    "total": 1006.75,
                    "currency": "USD",
                    "cost_per_day": 67.12
                }},
                "cost_optimization": {{
                    "suggestions": [
                        "Consider breaking down into smaller sub-tasks",
                        "Use caching to avoid redundant analysis"
                    ]
                }}
            }}
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for cost estimation: {len(ai_response)} characters")
            
            # Parse the AI response using the robust JSON parser
            cost_result = self._parse_ai_json_response(ai_response, "cost estimation")
            
            return {
                "status": "completed",
                "result": cost_result,
                "agent_id": self.agent_id,
                "processing_time": 1.5,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based cost estimation: {e}")
            # Fallback to basic cost estimation
            basic_cost = duration_days * 50  # $50 per day basic rate
            return {
                "status": "completed",
                "result": {
                    "project_scope": scope,
                    "cost_breakdown": {
                        "summary": {
                            "total": basic_cost,
                            "currency": "AUD",
                            "cost_per_day": 50
                        },
                        "cost_optimization": {
                            "suggestions": ["Enable AI service for detailed cost analysis"]
                        }
                    }
                },
                "agent_id": self.agent_id,
                "estimation_method": "fallback_basic"
            }

    async def _get_ai_response(self, prompt: str) -> str:
        """Get response from AI service via MCP - NO DIRECT AI PROVIDER ACCESS ALLOWED"""
        try:
            # All AI requests must go through MCP server - no direct provider access
            if not self.websocket:
                raise Exception("MCP connection required - direct AI provider access forbidden")

            # Send task_request directly to AI service via MCP server
            task_id = str(uuid.uuid4())
            ai_task_request = {
                "type": "research_action",
                "data": {
                    "task_id": task_id,
                    "agent_type": "ai_service",
                    "action": "ai_chat_completion",
                    "context_id": f"ai-request-{task_id}",
                    "payload": {
                        "provider": "xai",
                        "model": "grok-3-mini",
                        "messages": [
                            {"role": "system", "content": "You are a research planning assistant. Provide detailed, structured responses in JSON format."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                },
                "client_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Send request through MCP
            await self.websocket.send(json.dumps(ai_task_request))
            logger.info(f"Sent AI task request through MCP: {task_id}")

            # Wait for task result (with timeout)
            timeout_seconds = 30
            start_time = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
                try:
                    # Check for incoming messages
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    # Check if this is the task result we're waiting for
                    if (data.get("type") == "task_result" and 
                        data.get("task_id") == task_id):

                        if data.get("status") == "completed":
                            result = data.get("result", {})
                            logger.info(f"Raw AI result received: {result}")
                            
                            # Handle different response formats from AI service
                            if isinstance(result, str):
                                return result
                            elif isinstance(result, dict):
                                # Handle OpenAI API response format
                                if "choices" in result and len(result["choices"]) > 0:
                                    choice = result["choices"][0]
                                    if "message" in choice and "content" in choice["message"]:
                                        content = choice["message"]["content"]
                                        logger.info(f"Extracted content from OpenAI response: {len(content)} chars")
                                        return content
                                # Handle direct content response
                                return result.get("content", result.get("response", str(result)))
                            return str(result)
                        else:
                            error_msg = data.get("error", "Unknown error")
                            raise Exception(f"AI task failed: {error_msg}")

                except asyncio.TimeoutError:
                    continue  # Keep waiting
                except Exception as e:
                    if "AI task failed" in str(e):
                        raise e  # Re-raise AI-specific errors
                    continue  # Keep waiting for other exceptions

            raise Exception("Timeout waiting for AI response")

        except Exception as e:
            logger.error(f"AI request failed via MCP: {str(e)}")
            raise Exception(f"AI request failed via MCP: {str(e)} - direct AI provider access forbidden")

    def _parse_research_plan(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured research plan."""
        try:
            # AI service now extracts JSON from markdown, so we can parse directly
            plan = json.loads(ai_response)
            logger.info(f"Successfully parsed research plan with keys: {list(plan.keys())}")
            
            # Validate required fields
            required_fields = ["objectives", "key_areas", "questions", "sources"]
            for field in required_fields:
                if field not in plan:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure timeline exists
            if "timeline" not in plan:
                plan["timeline"] = {
                    "total_days": 14,
                    "phases": {
                        "literature_search": 3,
                        "data_collection": 5,
                        "analysis": 4,
                        "synthesis": 2
                    }
                }
            
            # Ensure outcomes exist
            if "outcomes" not in plan:
                plan["outcomes"] = [
                    "Literature review",
                    "Data analysis report",
                    "Research synthesis"
                ]
            
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"AI response was: {ai_response}")
            raise ValueError(f"Invalid JSON in AI response: {e}")
        except Exception as e:
            logger.error(f"Error parsing research plan: {e}")
            raise

    def _parse_ai_json_response(self, ai_response: str, context: str = "AI response") -> Dict[str, Any]:
        """Parse AI response JSON with sanitization for common AI JSON errors."""
        try:
            logger.info(f"Parsing {context}: {ai_response[:200]}...")
            
            # Look for JSON block in the response (handle both ```json and plain JSON)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if not json_match:
                # Try to find JSON without code block markers
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if not json_match:
                    raise ValueError(f"No JSON found in {context}")
                json_str = json_match.group(0)
            else:
                json_str = json_match.group(1)
            
            logger.info(f"Extracted JSON string: {json_str[:100]}...")
            
            # Sanitize common AI mistakes: single quotes, trailing commas, missing commas, extra whitespace
            sanitized = json_str
            sanitized = re.sub(r"'", '"', sanitized)  # single to double quotes
            sanitized = re.sub(r',\s*([}\]])', r'\1', sanitized)  # remove trailing commas
            sanitized = re.sub(r'\s+', ' ', sanitized)  # collapse whitespace
            # Attempt to fix missing commas between string values (very basic heuristic)
            sanitized = re.sub(r'"\s*([a-zA-Z0-9_]+)"\s*"', r'", "', sanitized)
            # Remove any double commas
            sanitized = re.sub(r',\s*,', ',', sanitized)
            
            logger.info(f"Sanitized JSON: {sanitized[:100]}...")
            
            try:
                parsed_json = json.loads(sanitized)
                logger.info(f"Successfully parsed JSON with keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'not a dict'}")
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"Sanitized JSON still failed to parse: {e}")
                logger.error(f"Full sanitized JSON: {sanitized}")
                raise
                
        except Exception as e:
            logger.error(f"Error parsing {context}: {e}")
            logger.error(f"Full AI response was: {ai_response}")
            raise
    
    async def plan_research(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Plan research activities"""
        try:
            research_topic = data.get("topic", "")
            objectives = data.get("objectives", [])
            constraints = data.get("constraints", {})
            
            # Generate research plan
            plan = {
                "research_topic": research_topic,
                "objectives": objectives,
                "phases": [
                    {
                        "phase": "Literature Review",
                        "duration": "2-3 weeks",
                        "activities": ["Search academic databases", "Review key papers", "Identify gaps"]
                    },
                    {
                        "phase": "Data Collection",
                        "duration": "4-6 weeks", 
                        "activities": ["Design experiments", "Collect data", "Validate data quality"]
                    },
                    {
                        "phase": "Analysis",
                        "duration": "3-4 weeks",
                        "activities": ["Statistical analysis", "Pattern identification", "Result interpretation"]
                    },
                    {
                        "phase": "Documentation",
                        "duration": "2-3 weeks",
                        "activities": ["Write manuscript", "Create visualizations", "Peer review"]
                    }
                ],
                "estimated_timeline": "11-16 weeks",
                "constraints": constraints,
                "generated_at": datetime.now().isoformat()
            }
            
            return {
                "status": "completed",
                "plan": plan,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error planning research: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_information(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze information and provide insights"""
        try:
            information = data.get("information", "")
            analysis_type = data.get("type", "general")
            
            # Perform analysis based on type
            if analysis_type == "literature":
                analysis = {
                    "type": "literature_analysis",
                    "summary": f"Analysis of provided literature content: {len(information)} characters",
                    "key_themes": ["research methodology", "data analysis", "conclusions"],
                    "recommendations": ["Focus on methodology section", "Review data quality", "Validate conclusions"]
                }
            elif analysis_type == "data":
                analysis = {
                    "type": "data_analysis",
                    "summary": f"Data analysis of {len(str(information))} data points",
                    "patterns": ["trend_analysis", "correlation_detection", "outlier_identification"],
                    "recommendations": ["Clean data", "Apply statistical tests", "Visualize patterns"]
                }
            else:
                analysis = {
                    "type": "general_analysis",
                    "summary": f"General analysis of provided information: {len(information)} characters",
                    "insights": ["Structure is coherent", "Content is relevant", "More detail needed"],
                    "recommendations": ["Expand on key points", "Provide more context", "Add supporting evidence"]
                }
            
            return {
                "status": "completed",
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing information: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def estimate_costs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for research activities"""
        try:
            if not self.cost_estimator:
                return {
                    "status": "error",
                    "message": "Cost estimator not available",
                    "timestamp": datetime.now().isoformat()
                }
            
            research_type = data.get("research_type", "literature_review")
            scale = data.get("scale", "small")
            duration = data.get("duration_weeks", 4)
            
            # Use cost estimator if available
            cost_estimate = {
                "research_type": research_type,
                "scale": scale,
                "duration_weeks": duration,
                "estimated_costs": {
                    "personnel": duration * 1000,  # $1000 per week
                    "resources": duration * 100,   # $100 per week for resources
                    "overhead": (duration * 1000 + duration * 100) * 0.2  # 20% overhead
                },
                "total_estimated_cost": duration * 1320,  # Total with overhead
                "confidence": "medium",
                "assumptions": [
                    "Standard research personnel rates",
                    "Basic resource requirements",
                    "Standard overhead percentage"
                ]
            }
            
            return {
                "status": "completed",
                "cost_estimate": cost_estimate,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error estimating costs: {e}")
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
            "cost_estimator_available": COST_ESTIMATOR_AVAILABLE,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
planning_service: Optional[PlanningAgentService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if planning_service:
        return {
            "connected": planning_service.is_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if planning_service:
        return {
            "capabilities": planning_service.capabilities,
            "cost_estimator_available": COST_ESTIMATOR_AVAILABLE,
            "agent_id": planning_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="planning",
    agent_id="planning-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the planning agent service."""
    global planning_service
    
    try:
        # Initialize service
        planning_service = PlanningAgentService()
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=SERVICE_HOST,
            port=SERVICE_PORT,
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Planning Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            planning_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Planning agent shutdown requested")
    except Exception as e:
        logger.error(f"Planning agent failed: {e}")
        sys.exit(1)
    finally:
        if planning_service:
            await planning_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
