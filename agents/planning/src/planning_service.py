"""
Planning Agent Service - Containerized MCP Client

This service acts as a containerized Planning Agent that connects to the MCP server
via WebSocket and provides research planning capabilities.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import uvicorn
import websockets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import cost estimator
try:
    from cost_estimator import CostEstimator, CostTier
    from config_manager import ConfigManager
    COST_ESTIMATOR_AVAILABLE = True
except ImportError:
    print("Warning: Cost estimator not available")
    CostEstimator = None
    CostTier = None
    COST_ESTIMATOR_AVAILABLE = False

# Load configuration
def load_config():
    """Load configuration from config file"""
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}, using defaults")
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

# FastAPI app for health checks and HTTP endpoints
app = FastAPI(title="Planning Agent Service", version="1.0.0")

class HealthResponse(BaseModel):
    status: str
    agent_type: str
    mcp_connected: bool
    uptime_seconds: int

# REMOVED: TaskRequest model - direct task execution via API forbidden
# All tasks must be executed through MCP protocol

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
        
        logger.info(f"Planning Agent Service initialized with ID: {self.agent_id}")
        logger.info(f"Loaded capabilities: {self.capabilities}")
    
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
        
        if method == "task/execute":
            # Execute planning task
            try:
                result = await self.execute_planning_task(params)
                response = {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": msg_id
                }
            except Exception as e:
                logger.error(f"Error executing task: {e}")
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": msg_id
                }
            
            await self.websocket.send(json.dumps(response))
            
        elif method == "agent/ping":
            # Respond to health check
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "status": "healthy",
                    "agent_id": self.agent_id,
                    "capabilities": self.capabilities
                },
                "id": msg_id
            }
            await self.websocket.send(json.dumps(response))
            
        else:
            logger.warning(f"Unknown MCP method: {method}")
    
    async def execute_planning_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a planning task"""
        action = params.get("action")
        payload = params.get("payload", {})
        
        logger.info(f"Executing planning task: {action}")
        
        try:
            if action == "plan_research":
                return await self._plan_research(payload)
            elif action == "analyze_information":
                return await self._analyze_information(payload)
            elif action == "cost_estimation":
                return await self._estimate_costs(payload)
            elif action == "chain_of_thought":
                return await self._chain_of_thought(payload)
            elif action == "summarize_content":
                return await self._summarize_content(payload)
            elif action == "extract_insights":
                return await self._extract_insights(payload)
            elif action == "compare_sources":
                return await self._compare_sources(payload)
            elif action == "evaluate_credibility":
                return await self._evaluate_credibility(payload)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                    "agent_id": self.agent_id
                }
        except Exception as e:
            logger.error(f"Error executing planning task {action}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _plan_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Plan research based on query using AI"""
        query = payload.get("query", "")
        scope = payload.get("scope", "comprehensive")
        context = payload.get("context", {})
        
        if not query:
            raise ValueError("Query is required for research planning")
        
        # Create research planning prompt for AI
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
            "sources": ["PubMed", "ArXiv", "Semantic Scholar", "Google Scholar", "IEEE Xplore"],
            "timeline": {{
                "total_days": 14,
                "phases": {{
                    "literature_search": 3,
                    "data_collection": 5,
                    "analysis": 4,
                    "synthesis": 2
                }}
            }},
            "outcomes": ["Literature review", "Data analysis", "Research synthesis", "Final report"]
        }}
        
        Please be thorough and consider all relevant aspects of the research topic.
        Ensure the plan is realistic and executable within the given timeframe.
        """
        
        # Get AI response
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for research planning: {len(ai_response)} characters")
            
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
                "success": False,
                "error": f"Failed to generate research plan: {str(e)}",
                "status": "failed",
                "result": None,
                "agent_id": self.agent_id
            }
    async def _get_ai_response(self, prompt: str) -> str:
        """Get response from AI service via MCP - NO DIRECT AI PROVIDER ACCESS ALLOWED"""
        try:
            # All AI requests must go through MCP server - no direct provider access
            if not self.websocket:
                raise Exception("MCP connection required - direct AI provider access forbidden")
                
            ai_request_message = {
                "type": "ai_request",
                "request_id": str(uuid.uuid4()),
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a research planning assistant. Provide detailed, structured responses in JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            }
            
            # Send request through MCP
            await self.websocket.send(json.dumps(ai_request_message))
            logger.info(f"Sent AI request through MCP: {ai_request_message['request_id']}")
            
            # Wait for AI response (with timeout)
            timeout_seconds = 30
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
                try:
                    # Check for incoming messages
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    # Check if this is the AI response we're waiting for
                    if (data.get("type") == "ai_response" and 
                        data.get("request_id") == ai_request_message["request_id"]):
                        
                        if data.get("success"):
                            response_content = data.get("data", {}).get("content", "")
                            logger.info("Received AI response through MCP")
                            return response_content
                        else:
                            error_msg = data.get("error", "Unknown AI service error")
                            logger.error(f"AI service error via MCP: {error_msg}")
                            raise Exception(f"AI service error: {error_msg}")
                            
                except asyncio.TimeoutError:
                    # Continue waiting
                    continue
                except Exception as e:
                    logger.error(f"Error receiving AI response: {e}")
                    break
            
            logger.error("Timeout waiting for AI response via MCP")
            raise Exception("Timeout waiting for AI response via MCP")
                
        except Exception as e:
            logger.error(f"Error getting AI response via MCP: {e}")
            raise Exception(f"AI request failed via MCP: {str(e)} - direct AI provider access forbidden")
    
    def _parse_research_plan(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured research plan"""
        try:
            # Try to extract JSON from the response
            import re
            
            # Look for JSON block in the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                plan = json.loads(json_str)
                
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
            else:
                raise ValueError("No JSON found in AI response")
                
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            logger.debug(f"AI response was: {ai_response}")
            raise
    
    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze provided information using AI via MCP"""
        content = payload.get("content", "")
        analysis_type = payload.get("analysis_type", "general")
        
        if not content:
            raise ValueError("Content is required for information analysis")
        
        # Create analysis prompt for AI
        prompt = f"""
        Please analyze the following content with a focus on {analysis_type} analysis:
        
        Content: {content}
        
        Provide a comprehensive analysis including:
        1. Executive summary of the content
        2. Key points and findings (3-5 main points)
        3. Deep insights and implications
        4. Actionable recommendations
        5. Confidence assessment of the analysis
        
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
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
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
                "success": False,
                "error": f"Failed to analyze content: {str(e)}",
                "status": "failed",
                "result": None,
                "agent_id": self.agent_id
            }
    
    async def _estimate_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for research project using the sophisticated cost estimator"""
        project_scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        query = payload.get("query", "Research project cost estimation")
        agents_needed = payload.get("agents", ["planning", "literature", "analysis"])
        parallel_execution = payload.get("parallel_execution", False)
        context_content = payload.get("context", "")
        
        # Always try to use the sophisticated cost estimator first
        if COST_ESTIMATOR_AVAILABLE and CostEstimator:
            try:
                # Import the config manager and create cost estimator
                from .config_manager import ConfigManager
                config_manager = ConfigManager()
                cost_estimator = CostEstimator(config_manager)
                
                # Use the sophisticated cost estimation
                cost_estimate = cost_estimator.estimate_task_cost(
                    query=query,
                    agents=agents_needed,
                    parallel_execution=parallel_execution,
                    context_content=context_content
                )
                
                # Get cost recommendations
                recommendations = cost_estimator.get_cost_recommendations(cost_estimate)
                
                # Calculate traditional costs
                traditional_costs = await self._calculate_traditional_costs(payload)
                
                # Create comprehensive cost breakdown
                cost_breakdown = {
                    "ai_operations": {
                        "estimated_tokens": cost_estimate.estimated_tokens,
                        "estimated_cost": cost_estimate.estimated_cost_usd,
                        "task_complexity": cost_estimate.task_complexity.value,
                        "agent_count": cost_estimate.agent_count,
                        "parallel_factor": cost_estimate.parallel_factor,
                        "confidence": cost_estimate.confidence,
                        "reasoning": cost_estimate.reasoning
                    },
                    "traditional_costs": traditional_costs,
                    "summary": {
                        "ai_cost": cost_estimate.estimated_cost_usd,
                        "traditional_cost": traditional_costs["resources"]["total"],
                        "total": cost_estimate.estimated_cost_usd + traditional_costs["resources"]["total"],
                        "currency": "USD",
                        "cost_per_day": (cost_estimate.estimated_cost_usd + traditional_costs["resources"]["total"]) / duration_days if duration_days > 0 else 0
                    },
                    "cost_optimization": {
                        "current_tier": recommendations["current_tier"],
                        "suggestions": recommendations["suggestions"],
                        "alternatives": recommendations["alternatives"]
                    },
                    "thresholds": {
                        "session_warning": config_manager.get("cost_settings.cost_thresholds.session_warning", 1.0),
                        "session_limit": config_manager.get("cost_settings.cost_thresholds.session_limit", 5.0),
                        "daily_limit": config_manager.get("cost_settings.cost_thresholds.daily_limit", 50.0),
                        "emergency_stop": config_manager.get("cost_settings.cost_thresholds.emergency_stop", 100.0)
                    }
                }
                
                return {
                    "status": "completed",
                    "result": {
                        "project_scope": project_scope,
                        "cost_breakdown": cost_breakdown,
                        "estimation_method": "sophisticated_ai_cost_estimator",
                        "recommendations": recommendations["suggestions"],
                        "agent_id": self.agent_id,
                        "processing_time": 0.8,
                        "cost_estimator_used": True,
                        "accuracy_level": "high"
                    }
                }
                
            except Exception as e:
                logger.error(f"Error using sophisticated cost estimator: {e}")
                # Fall back to enhanced estimation
                return await self._enhanced_cost_estimation(payload)
        else:
            # Fall back to enhanced estimation if sophisticated estimator not available
            logger.warning("Sophisticated cost estimator not available, using fallback method")
            return await self._enhanced_cost_estimation(payload)
    
    async def _enhanced_cost_estimation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced cost estimation using config-based approach with higher accuracy"""
        project_scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        agents_needed = payload.get("agents", ["planning", "literature", "analysis"])
        query = payload.get("query", "")
        
        # Load cost settings from config with more accurate defaults
        cost_settings = config.get("cost_settings", {})
        token_costs = cost_settings.get("token_costs", {})
        cost_thresholds = cost_settings.get("cost_thresholds", {})
        
        # More accurate token estimation based on query complexity and content
        estimated_tokens_per_agent = {
            "planning": 5000,
            "literature": 15000,
            "analysis": 10000,
            "synthesis": 8000,
            "screening": 12000,
            "writing": 20000,
            "research_manager": 3000,
            "ai_agent": 7000
        }
        
        # Better complexity assessment
        complexity_score = 0
        query_lower = query.lower()
        
        # Query complexity indicators (more comprehensive)
        high_complexity_keywords = [
            "comprehensive", "detailed analysis", "compare multiple", "research study",
            "in-depth", "systematic review", "correlation", "statistical analysis",
            "meta-analysis", "longitudinal", "multi-factor", "complex"
        ]
        
        medium_complexity_keywords = [
            "analyze", "compare", "summarize", "explain", "relationship",
            "trend", "pattern", "evaluate", "assess", "review"
        ]
        
        # Calculate complexity score
        if any(keyword in query_lower for keyword in high_complexity_keywords):
            complexity_score += 3
        elif any(keyword in query_lower for keyword in medium_complexity_keywords):
            complexity_score += 2
        else:
            complexity_score += 1
            
        # Agent count factor
        if len(agents_needed) >= 4:
            complexity_score += 2
        elif len(agents_needed) >= 2:
            complexity_score += 1
            
        # Query length factor (more tokens needed for longer queries)
        if len(query) > 500:
            complexity_score += 2
        elif len(query) > 200:
            complexity_score += 1
            
        # Determine complexity multiplier
        if complexity_score >= 6:
            scope_multiplier = 5.0  # HIGH complexity
            complexity_level = "HIGH"
        elif complexity_score >= 4:
            scope_multiplier = 2.5  # MEDIUM complexity
            complexity_level = "MEDIUM"
        else:
            scope_multiplier = 1.0  # LOW complexity
            complexity_level = "LOW"
        
        # Calculate total tokens with better estimation
        base_tokens = sum(estimated_tokens_per_agent.get(agent, 5000) for agent in agents_needed)
        query_tokens = max(len(query) // 4, 100)  # Rough tokenization
        context_tokens = max(len(payload.get("context", "")) // 4, 0)
        
        total_tokens = int((base_tokens + query_tokens + context_tokens) * scope_multiplier)
        
        # Use actual provider pricing from config
        primary_provider = config.get("research_manager", {}).get("provider", "openai")
        primary_model = config.get("research_manager", {}).get("model", "gpt-4o-mini")
        
        openai_costs = token_costs.get(primary_provider, {}).get(primary_model, {
            "input": 0.00015, "output": 0.0006
        })
        
        # More accurate input/output token distribution
        input_tokens = int(total_tokens * 0.75)  # Typically more input than output for research
        output_tokens = total_tokens - input_tokens
        
        ai_cost = (input_tokens / 1000 * openai_costs["input"]) + (output_tokens / 1000 * openai_costs["output"])
        
        # Calculate traditional costs with AI assistance
        traditional_costs = await self._calculate_traditional_costs(payload)
        traditional_total = traditional_costs["resources"]["total"]
        
        # Enhanced cost breakdown with more details
        cost_breakdown = {
            "ai_operations": {
                "estimated_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_per_1k_input": openai_costs["input"],
                "cost_per_1k_output": openai_costs["output"],
                "total_ai_cost": ai_cost,
                "agents_used": agents_needed,
                "complexity_multiplier": scope_multiplier,
                "complexity_level": complexity_level,
                "provider": primary_provider,
                "model": primary_model,
                "reasoning": f"Estimated {total_tokens} tokens for {len(agents_needed)} agents with {complexity_level} complexity"
            },
            "traditional_costs": traditional_costs,
            "summary": {
                "ai_cost": ai_cost,
                "traditional_cost": traditional_total,
                "total": ai_cost + traditional_total,
                "currency": "USD",
                "cost_per_day": (ai_cost + traditional_total) / duration_days if duration_days > 0 else 0,
                "cost_per_agent": (ai_cost + traditional_total) / len(agents_needed) if agents_needed else 0
            },
            "thresholds": {
                "session_warning": cost_thresholds.get("session_warning", 1.0),
                "session_limit": cost_thresholds.get("session_limit", 5.0),
                "daily_limit": cost_thresholds.get("daily_limit", 50.0),
                "emergency_stop": cost_thresholds.get("emergency_stop", 100.0)
            },
            "optimization_suggestions": []
        }
        
        # Add optimization suggestions based on cost analysis
        if ai_cost > 1.0:
            cost_breakdown["optimization_suggestions"].append("Consider breaking down into smaller sub-tasks")
        if len(agents_needed) > 3:
            cost_breakdown["optimization_suggestions"].append("Evaluate if all agents are necessary")
        if complexity_level == "HIGH":
            cost_breakdown["optimization_suggestions"].append("Use caching to avoid redundant analysis")
        
        return {
            "status": "completed",
            "result": {
                "project_scope": project_scope,
                "cost_breakdown": cost_breakdown,
                "estimation_method": "enhanced_config_based_v2",
                "recommendations": [
                    "Monitor token usage during execution",
                    "Consider batch processing to reduce API calls",
                    "Use caching for repeated queries",
                    "Set up cost alerts based on thresholds",
                    "Review agent selection for cost optimization"
                ],
                "agent_id": self.agent_id,
                "processing_time": 1.0,
                "accuracy_level": "medium-high"
            }
        }
    
    async def _calculate_traditional_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate traditional research costs using AI-assisted estimation via MCP"""
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        project_context = payload.get("context", "")
        
        # Create cost estimation prompt for AI
        prompt = f"""
        Please estimate traditional research costs for a project with the following parameters:
        
        Duration: {duration_days} days
        Resources needed: {resources_needed}
        Project context: {project_context}
        
        Provide detailed cost estimates for each resource category based on current market rates:
        1. Database access subscriptions
        2. Survey and data collection tools
        3. Analysis software licenses
        4. Expert consultation fees
        5. Cloud computing resources
        6. Additional operational costs
        
        Consider regional variations and current market pricing. Format your response as a JSON object:
        {{
            "resources": {{
                "items": {resources_needed},
                "costs": {{
                    "database_access": 200,
                    "survey_tools": 150,
                    "analysis_software": 300,
                    "expert_consultation": 500,
                    "data_collection": 400,
                    "cloud_compute": 100
                }},
                "total": 1650
            }},
            "duration_days": {duration_days},
            "cost_breakdown_reasoning": "Explanation of how costs were estimated",
            "market_factors": ["Factor 1", "Factor 2"],
            "cost_confidence": 0.8
        }}
        
        Provide realistic estimates based on 2024-2025 market rates.
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for traditional cost estimation: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                cost_result = json.loads(json_match.group(0))
                return cost_result
            else:
                raise ValueError("No valid JSON found in AI response")
                
        except Exception as e:
            logger.error(f"Error generating AI-based cost estimation: {e}")
            # Fallback to basic calculation if AI fails
            resource_costs_map = {
                "database_access": 200,
                "survey_tools": 150,
                "analysis_software": 300,
                "expert_consultation": 500,
                "data_collection": 400,
                "cloud_compute": 100
            }
            
            resource_total = sum(resource_costs_map.get(resource, 0) for resource in resources_needed)
            
            return {
                "resources": {
                    "items": resources_needed,
                    "costs": {resource: resource_costs_map.get(resource, 0) for resource in resources_needed},
                    "total": resource_total
                },
                "duration_days": duration_days,
                "cost_breakdown_reasoning": f"Fallback calculation due to AI error: {str(e)}",
                "market_factors": ["Standard market rates used"],
                "cost_confidence": 0.6
            }
    
    async def _get_traditional_total(self, payload: Dict[str, Any]) -> float:
        """Get total traditional costs"""
        traditional = await self._calculate_traditional_costs(payload)
        return traditional["resources"]["total"]
    
    async def _basic_cost_estimation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Basic cost estimation using AI-assisted analysis via MCP"""
        project_scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        project_description = payload.get("description", "Research project cost estimation")
        
        # Create comprehensive cost estimation prompt for AI
        prompt = f"""
        Please provide a detailed cost estimation for a research project with these parameters:
        
        Project Scope: {project_scope}
        Duration: {duration_days} days
        Resources Needed: {resources_needed}
        Project Description: {project_description}
        
        Estimate costs across these categories:
        1. Labor costs (daily rates based on expertise level and scope)
        2. Overhead and administrative costs
        3. Resource and tool costs
        4. Contingency planning
        5. Total project cost with breakdown
        
        Consider current market rates for research services, regional variations, and project complexity.
        
        Format your response as a JSON object with this exact structure:
        {{
            "labor": {{
                "daily_rate": 750,
                "duration_days": {duration_days},
                "total": 22500
            }},
            "overhead": {{
                "rate": 0.3,
                "total": 6750
            }},
            "resources": {{
                "items": {resources_needed},
                "costs": {{
                    "database_access": 200,
                    "survey_tools": 150,
                    "analysis_software": 300
                }},
                "total": 650
            }},
            "summary": {{
                "subtotal": 23150,
                "overhead": 6750,
                "total": 29900,
                "currency": "USD"
            }},
            "timeline": {{
                "estimated_duration": {duration_days},
                "cost_per_day": 997
            }},
            "cost_reasoning": "Detailed explanation of cost calculation methodology",
            "market_assumptions": ["Assumption 1", "Assumption 2"],
            "confidence_level": 0.8
        }}
        
        Base estimates on 2024-2025 market rates for research services.
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for basic cost estimation: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                cost_breakdown = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
            return {
                "status": "completed",
                "result": {
                    "project_scope": project_scope,
                    "cost_breakdown": cost_breakdown,
                    "estimation_method": "ai_assisted_basic",
                    "recommendations": [
                        "Consider phased approach to reduce upfront costs",
                        "Review resource requirements for optimization",
                        "Include 10-15% contingency buffer",
                        "Monitor actual costs vs estimates during execution"
                    ],
                    "agent_id": self.agent_id,
                    "processing_time": 1.2,
                    "ai_generated": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based basic cost estimation: {e}")
            
            # Fallback calculation if AI fails
            base_costs = {
                "small": {"daily_rate": 500, "overhead": 0.2},
                "medium": {"daily_rate": 750, "overhead": 0.3},
                "large": {"daily_rate": 1000, "overhead": 0.4}
            }
            
            scope_config = base_costs.get(project_scope, base_costs["medium"])
            daily_rate = scope_config["daily_rate"]
            overhead_rate = scope_config["overhead"]
            
            # Calculate base costs
            labor_cost = daily_rate * duration_days
            overhead_cost = labor_cost * overhead_rate
            
            # Resource costs
            resource_costs_map = {
                "database_access": 200,
                "survey_tools": 150,
                "analysis_software": 300,
                "expert_consultation": 500,
                "data_collection": 400,
                "ai_processing": 150,
                "cloud_compute": 100
            }
            
            additional_costs = sum(resource_costs_map.get(resource, 0) for resource in resources_needed)
            total_cost = labor_cost + overhead_cost + additional_costs
            
            cost_breakdown = {
                "labor": {
                    "daily_rate": daily_rate,
                    "duration_days": duration_days,
                    "total": labor_cost
                },
                "overhead": {
                    "rate": overhead_rate,
                    "total": overhead_cost
                },
                "resources": {
                    "items": resources_needed,
                    "costs": {resource: resource_costs_map.get(resource, 0) for resource in resources_needed},
                    "total": additional_costs
                },
                "summary": {
                    "subtotal": labor_cost + additional_costs,
                    "overhead": overhead_cost,
                    "total": total_cost,
                    "currency": "USD"
                },
                "timeline": {
                    "estimated_duration": duration_days,
                    "cost_per_day": total_cost / duration_days if duration_days > 0 else 0
                },
                "cost_reasoning": f"Fallback calculation used due to AI error: {str(e)}",
                "market_assumptions": ["Standard industry rates applied"],
                "confidence_level": 0.6
            }
            
            return {
                "status": "completed",
                "result": {
                    "project_scope": project_scope,
                    "cost_breakdown": cost_breakdown,
                    "estimation_method": "fallback_basic",
                    "recommendations": [
                        "Consider phased approach to reduce upfront costs",
                        "Review resource requirements for optimization",
                        "Include 10-15% contingency buffer",
                        "Monitor actual costs vs estimates during execution",
                        "Re-run estimation when AI service is available"
                    ],
                    "agent_id": self.agent_id,
                    "processing_time": 1.2,
                    "ai_generated": False
                }
            }
    
    async def _chain_of_thought(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform chain of thought reasoning using AI via MCP"""
        problem = payload.get("problem", "")
        context = payload.get("context", "")
        
        if not problem:
            raise ValueError("Problem statement is required for chain of thought reasoning")
        
        # Create chain of thought prompt for AI
        prompt = f"""
        Please perform step-by-step chain of thought reasoning for the following problem:
        
        Problem: {problem}
        Context: {context}
        
        Break down your reasoning into clear, logical steps:
        1. Problem identification and understanding
        2. Context analysis and relevant factors
        3. Sub-problem decomposition
        4. Solution approach identification
        5. Feasibility evaluation
        6. Final recommendation and confidence assessment
        
        Format your response as a JSON object with this exact structure:
        {{
            "problem": "{problem}",
            "reasoning_chain": [
                "Step 1: Problem identification and understanding",
                "Step 2: Context analysis",
                "Step 3: Breaking down into sub-problems",
                "Step 4: Identifying potential solutions",
                "Step 5: Evaluating solution feasibility",
                "Step 6: Selecting optimal approach"
            ],
            "conclusion": "Final recommendation based on reasoning",
            "confidence": 0.8,
            "key_assumptions": ["Assumption 1", "Assumption 2"],
            "potential_risks": ["Risk 1", "Risk 2"]
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for chain of thought: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                reasoning_result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
            return {
                "status": "completed",
                "result": reasoning_result,
                "agent_id": self.agent_id,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based chain of thought: {e}")
            return {
                "success": False,
                "error": f"Failed to perform chain of thought reasoning: {str(e)}",
                "status": "failed", 
                "result": None,
                "agent_id": self.agent_id
            }
    
    async def _summarize_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize provided content using AI via MCP"""
        content = payload.get("content", "")
        summary_length = payload.get("length", "medium")
        
        if not content:
            raise ValueError("Content is required for summarization")
        
        # Define length parameters
        length_config = {
            "short": "2-3 sentences",
            "medium": "1-2 paragraphs", 
            "long": "3-4 detailed paragraphs"
        }
        
        target_length = length_config.get(summary_length, "1-2 paragraphs")
        
        # Create summarization prompt for AI
        prompt = f"""
        Please create a comprehensive summary of the following content:
        
        Content: {content}
        
        Summary length: {target_length}
        
        Provide:
        1. A concise summary at the requested length
        2. Key points extracted from the content (3-5 main points)
        3. Important details that should not be overlooked
        4. Overall assessment of the content's value and relevance
        
        Format your response as a JSON object with this exact structure:
        {{
            "original_length": {len(content)},
            "summary": "Comprehensive summary of the content",
            "key_points": ["Main point 1", "Main point 2", "Main point 3"],
            "important_details": ["Detail 1", "Detail 2"],
            "content_assessment": "Assessment of content value and relevance",
            "summary_length": "{summary_length}"
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for content summarization: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                summary_result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
            return {
                "status": "completed",
                "result": summary_result,
                "agent_id": self.agent_id,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based content summary: {e}")
            return {
                "success": False,
                "error": f"Failed to summarize content: {str(e)}",
                "status": "failed",
                "result": None,
                "agent_id": self.agent_id
            }
    
    async def _extract_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from data using AI via MCP"""
        data = payload.get("data", {})
        
        if not data:
            raise ValueError("Data is required for insight extraction")
        
        # Create insight extraction prompt for AI
        prompt = f"""
        Please analyze the following data and extract meaningful insights:
        
        Data: {json.dumps(data, indent=2)}
        
        Provide comprehensive analysis including:
        1. Key insights derived from the data
        2. Important patterns and trends identified
        3. Actionable recommendations based on the insights
        4. Potential implications and consequences
        5. Areas requiring further investigation
        
        Format your response as a JSON object with this exact structure:
        {{
            "insights": ["Insight 1", "Insight 2", "Insight 3"],
            "patterns": ["Pattern A", "Pattern B", "Pattern C"],
            "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"],
            "implications": ["Implication 1", "Implication 2"],
            "further_investigation": ["Area 1", "Area 2"],
            "confidence_level": 0.8,
            "data_quality_assessment": "Assessment of data quality and reliability"
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for insight extraction: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                insights_result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
            return {
                "status": "completed",
                "result": insights_result,
                "agent_id": self.agent_id,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based insights: {e}")
            return {
                "success": False,
                "error": f"Failed to extract insights: {str(e)}",
                "status": "failed",
                "result": None,
                "agent_id": self.agent_id
            }
    
    async def _compare_sources(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple sources using AI via MCP"""
        sources = payload.get("sources", [])
        
        if not sources or len(sources) < 2:
            raise ValueError("At least 2 sources are required for comparison")
        
        # Create source comparison prompt for AI
        prompt = f"""
        Please compare and analyze the following sources:
        
        Sources to compare:
        {json.dumps(sources, indent=2)}
        
        Provide a comprehensive comparison including:
        1. Overview of all sources being compared
        2. Key similarities between sources
        3. Important differences and contradictions
        4. Credibility assessment of each source
        5. Synthesis of information across sources
        6. Recommendations for which sources are most reliable
        
        Format your response as a JSON object with this exact structure:
        {{
            "sources_count": {len(sources)},
            "comparison_overview": "Overall assessment of the source comparison",
            "similarities": ["Common theme 1", "Common theme 2", "Common theme 3"],
            "differences": ["Difference 1", "Difference 2", "Difference 3"],
            "credibility_ranking": ["Most credible source", "Second most credible", "Third most credible"],
            "synthesis": "Integrated understanding from all sources",
            "recommendations": ["Recommendation 1", "Recommendation 2"],
            "conflicting_information": ["Conflict 1", "Conflict 2"],
            "confidence_score": 0.85
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for source comparison: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                comparison_result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
            return {
                "status": "completed",
                "result": comparison_result,
                "agent_id": self.agent_id,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based source comparison: {e}")
            return {
                "success": False,
                "error": f"Failed to compare sources: {str(e)}",
                "status": "failed",
                "result": None,
                "agent_id": self.agent_id
            }
    
    async def _evaluate_credibility(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate source credibility using AI via MCP"""
        source = payload.get("source", {})
        
        if not source:
            raise ValueError("Source information is required for credibility evaluation")
        
        # Create credibility evaluation prompt for AI
        prompt = f"""
        Please evaluate the credibility of the following source:
        
        Source: {json.dumps(source, indent=2)}
        
        Assess credibility based on:
        1. Author credentials and expertise
        2. Publication venue and reputation
        3. Peer review status
        4. Recency and currency of information
        5. Citation patterns and references
        6. Methodology and evidence quality
        7. Potential biases or conflicts of interest
        
        Format your response as a JSON object with this exact structure:
        {{
            "credibility_score": 0.85,
            "credibility_level": "High/Medium/Low",
            "factors": ["Peer reviewed", "Recent publication", "Authoritative source", "Strong methodology"],
            "concerns": ["Limited sample size", "Potential bias"],
            "strengths": ["Strong methodology", "Multiple data sources", "Expert author"],
            "overall_assessment": "Detailed assessment of overall credibility",
            "recommendation": "Should this source be trusted for research purposes?",
            "verification_needed": ["Aspect 1 to verify", "Aspect 2 to verify"],
            "comparative_assessment": "How does this compare to similar sources?"
        }}
        """
        
        try:
            ai_response = await self._get_ai_response(prompt)
            logger.info(f"Received AI response for credibility evaluation: {len(ai_response)} characters")
            
            # Parse the AI response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                credibility_result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
            
            return {
                "status": "completed",
                "result": credibility_result,
                "agent_id": self.agent_id,
                "ai_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating AI-based credibility evaluation: {e}")
            return {
                "success": False,
                "error": f"Failed to evaluate credibility: {str(e)}",
                "status": "failed",
                "result": None,
                "agent_id": self.agent_id
            }
    
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
            "capabilities": self.capabilities
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Planning Agent Service")
        self.should_run = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
        
        self.is_connected = False

# Global service instance
planning_service = PlanningAgentService()

# FastAPI endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    health_data = planning_service.get_health_status()
    return HealthResponse(**health_data)

@app.get("/capabilities")
async def get_capabilities():
    """Get agent capabilities"""
    return {"capabilities": planning_service.capabilities}

# REMOVED: /task endpoint that bypassed MCP server
# All task execution must go through MCP protocol - direct API access forbidden

async def run_mcp_client():
    """Run the MCP client in background"""
    while planning_service.should_run:
        try:
            await planning_service.connect_to_mcp_server()
            await planning_service.listen_for_tasks()
        except Exception as e:
            logger.error(f"MCP client error: {e}")
            if planning_service.should_run:
                logger.info("Attempting to reconnect in 10 seconds...")
                await asyncio.sleep(10)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(planning_service.shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

async def start_service():
    """Start the Planning Agent Service"""
    logger.info("Starting Planning Agent Service")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Start MCP client in background
    mcp_task = asyncio.create_task(run_mcp_client())
    
    # Start FastAPI server
    config = uvicorn.Config(
        app=app,
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    finally:
        # Cleanup
        mcp_task.cancel()
        await planning_service.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(start_service())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
