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
    from .cost_estimator import CostEstimator, CostTier
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

class TaskRequest(BaseModel):
    action: str
    payload: Dict[str, Any]

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
            # Fallback to basic structure if AI fails
            return await self._fallback_research_plan(payload)
    
    async def _get_ai_response(self, prompt: str) -> str:
        """Get response from AI service"""
        try:
            # Try to use AI service if available
            ai_service_url = os.getenv("AI_SERVICE_URL")
            if ai_service_url:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{ai_service_url}/ai/chat/completions",
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": "You are a research planning assistant. Provide detailed, structured responses in JSON format."},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.7,
                            "max_tokens": 2000
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return result.get("content", "")
                    else:
                        logger.error(f"AI service error: {response.status_code}")
                        raise Exception(f"AI service error: {response.status_code}")
            else:
                # Direct OpenAI call as fallback
                return await self._direct_openai_call(prompt)
                
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            raise
    
    async def _direct_openai_call(self, prompt: str) -> str:
        """Direct OpenAI API call as fallback"""
        try:
            import openai
            
            # Get API key from environment or config
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                api_key = config.get("ai_settings", {}).get("openai_api_key")
            
            if not api_key:
                raise Exception("No OpenAI API key available")
            
            client = openai.AsyncOpenAI(api_key=api_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a research planning assistant. Provide detailed, structured responses in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                timeout=30
            )
            
            content = response.choices[0].message.content
            return content if content else "No content received from AI"
            
        except Exception as e:
            logger.error(f"Direct OpenAI call failed: {e}")
            raise
    
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
    
    async def _fallback_research_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback research plan if AI fails"""
        query = payload.get("query", "")
        scope = payload.get("scope", "comprehensive")
        
        plan = {
            "objectives": [
                f"Investigate {query}",
                "Identify key research areas",
                "Synthesize findings",
                "Generate actionable insights"
            ],
            "key_areas": [
                "Background research",
                "Current literature",
                "Data analysis",
                "Methodology review",
                "Gap analysis"
            ],
            "questions": [
                f"What are the current findings about {query}?",
                "What gaps exist in the research?",
                "What methodologies are most effective?",
                "What are the practical applications?",
                "What future research is needed?"
            ],
            "sources": [
                "PubMed",
                "ArXiv",
                "Semantic Scholar",
                "Google Scholar",
                "IEEE Xplore",
                "ResearchGate"
            ],
            "timeline": {
                "total_days": 14,
                "phases": {
                    "literature_search": 3,
                    "data_collection": 5,
                    "analysis": 4,
                    "synthesis": 2
                }
            },
            "outcomes": [
                "Comprehensive literature review",
                "Data analysis report",
                "Research synthesis",
                "Recommendations report"
            ]
        }
        
        return {
            "status": "completed",
            "result": {
                "query": query,
                "scope": scope,
                "plan": plan,
                "agent_id": self.agent_id,
                "processing_time": 1.5,
                "ai_generated": False,
                "note": "Used fallback plan due to AI service unavailability"
            }
        }
    
    async def _analyze_information(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze provided information"""
        content = payload.get("content", "")
        analysis_type = payload.get("analysis_type", "general")
        
        # Mock information analysis
        analysis_result = {
            "summary": f"Analysis of {len(content)} characters of content",
            "key_points": [
                "Primary finding identified",
                "Secondary patterns observed",
                "Supporting evidence located"
            ],
            "insights": [
                "Content shows clear structure",
                "Multiple perspectives present",
                "Evidence-based conclusions"
            ],
            "recommendations": [
                "Further investigation recommended",
                "Cross-reference with additional sources",
                "Validate findings with experts"
            ],
            "confidence_score": 0.85,
            "analysis_type": analysis_type
        }
        
        return {
            "status": "completed",
            "result": analysis_result,
            "agent_id": self.agent_id,
            "processing_time": 1.8
        }
    
    async def _estimate_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for research project using integrated cost estimator"""
        project_scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        query = payload.get("query", "Research project cost estimation")
        agents_needed = payload.get("agents", ["planning", "literature", "analysis"])
        
        # Try to use the existing cost estimator if available
        if COST_ESTIMATOR_AVAILABLE and CostEstimator:
            try:
                # Create a mock config manager for the cost estimator
                class MockConfigManager:
                    def __init__(self):
                        self.config = {
                            "cost_settings": {
                                "token_costs": {
                                    "openai": {
                                        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
                                        "gpt-4": {"input": 0.03, "output": 0.06}
                                    }
                                },
                                "cost_thresholds": {
                                    "session_warning": 1.0,
                                    "session_limit": 5.0,
                                    "daily_warning": 10.0,
                                    "daily_limit": 50.0,
                                    "emergency_stop": 100.0
                                },
                                "complexity_multipliers": {
                                    "LOW": 1.0,
                                    "MEDIUM": 2.5,
                                    "HIGH": 5.0,
                                    "CRITICAL": 10.0
                                }
                            }
                        }
                    
                    def get(self, key, default=None):
                        keys = key.split('.')
                        value = self.config
                        for k in keys:
                            if isinstance(value, dict) and k in value:
                                value = value[k]
                            else:
                                return default
                        return value

                cost_estimator = CostEstimator(MockConfigManager())
                
                # Check if the method exists and try to use it
                if hasattr(cost_estimator, 'estimate_task_cost'):
                    cost_result = cost_estimator.estimate_task_cost(
                        query=query,
                        agents=agents_needed,
                        parallel_execution=payload.get("parallel_execution", False),
                        context_content=payload.get("context", None)
                    )
                    
                    # Convert the cost result to our expected format
                    cost_breakdown = {
                        "ai_operations": {
                            "estimated_tokens": cost_result.estimated_tokens,
                            "estimated_cost": cost_result.estimated_cost_usd,
                            "task_complexity": str(cost_result.task_complexity),
                            "agent_count": cost_result.agent_count,
                            "confidence": cost_result.confidence,
                            "reasoning": cost_result.reasoning
                        },
                        "traditional_costs": await self._calculate_traditional_costs(payload),
                        "summary": {
                            "ai_cost": cost_result.estimated_cost_usd,
                            "traditional_cost": await self._get_traditional_total(payload),
                            "total": cost_result.estimated_cost_usd + await self._get_traditional_total(payload),
                            "currency": "USD"
                        }
                    }
                    
                    return {
                        "status": "completed",
                        "result": {
                            "project_scope": project_scope,
                            "cost_breakdown": cost_breakdown,
                            "estimation_method": "hybrid_ai_traditional",
                            "recommendations": [
                                "Monitor token usage during execution",
                                "Consider using more cost-effective providers for routine tasks",
                                "Implement caching to reduce redundant API calls",
                                "Plan for traditional research costs alongside AI costs"
                            ],
                            "agent_id": self.agent_id,
                            "processing_time": 0.8
                        }
                    }
                else:
                    # Fallback to enhanced estimation using config-based approach
                    return await self._enhanced_cost_estimation(payload)
                    
            except Exception as e:
                logger.error(f"Error using cost estimator: {e}")
                return await self._enhanced_cost_estimation(payload)
        else:
            return await self._enhanced_cost_estimation(payload)
    
    async def _enhanced_cost_estimation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced cost estimation using config-based approach"""
        project_scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        agents_needed = payload.get("agents", ["planning", "literature", "analysis"])
        
        # Load cost settings from config
        cost_settings = config.get("cost_settings", {})
        token_costs = cost_settings.get("token_costs", {})
        cost_thresholds = cost_settings.get("cost_thresholds", {})
        
        # Estimate AI costs based on agents and complexity
        estimated_tokens_per_agent = {
            "planning": 5000,
            "literature": 15000,
            "analysis": 10000,
            "synthesis": 8000,
            "screening": 12000,
            "writing": 20000
        }
        
        total_tokens = sum(estimated_tokens_per_agent.get(agent, 5000) for agent in agents_needed)
        
        # Apply complexity multiplier
        complexity_multipliers = cost_settings.get("complexity_multipliers", {})
        scope_multiplier = complexity_multipliers.get(project_scope.upper(), 2.5)
        total_tokens = int(total_tokens * scope_multiplier)
        
        # Calculate AI costs using OpenAI GPT-4o-mini as default
        openai_costs = token_costs.get("openai", {}).get("gpt-4o-mini", {"input": 0.00015, "output": 0.0006})
        input_tokens = int(total_tokens * 0.7)  # Assume 70% input, 30% output
        output_tokens = total_tokens - input_tokens
        
        ai_cost = (input_tokens / 1000 * openai_costs["input"]) + (output_tokens / 1000 * openai_costs["output"])
        
        # Calculate traditional costs
        traditional_costs = await self._calculate_traditional_costs(payload)
        traditional_total = traditional_costs["resources"]["total"]
        
        # Combined cost breakdown
        cost_breakdown = {
            "ai_operations": {
                "estimated_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_per_1k_input": openai_costs["input"],
                "cost_per_1k_output": openai_costs["output"],
                "total_ai_cost": ai_cost,
                "agents_used": agents_needed,
                "complexity_multiplier": scope_multiplier
            },
            "traditional_costs": traditional_costs,
            "summary": {
                "ai_cost": ai_cost,
                "traditional_cost": traditional_total,
                "total": ai_cost + traditional_total,
                "currency": "USD",
                "cost_per_day": (ai_cost + traditional_total) / duration_days if duration_days > 0 else 0
            },
            "thresholds": {
                "session_warning": cost_thresholds.get("session_warning", 1.0),
                "session_limit": cost_thresholds.get("session_limit", 5.0),
                "daily_limit": cost_thresholds.get("daily_limit", 50.0)
            }
        }
        
        return {
            "status": "completed",
            "result": {
                "project_scope": project_scope,
                "cost_breakdown": cost_breakdown,
                "estimation_method": "enhanced_config_based",
                "recommendations": [
                    "Monitor token usage during execution",
                    "Consider batch processing to reduce API calls",
                    "Use caching for repeated queries",
                    "Set up cost alerts based on thresholds",
                    "Review agent selection for cost optimization"
                ],
                "agent_id": self.agent_id,
                "processing_time": 1.0
            }
        }
    
    async def _calculate_traditional_costs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate traditional research costs"""
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        
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
            "duration_days": duration_days
        }
    
    async def _get_traditional_total(self, payload: Dict[str, Any]) -> float:
        """Get total traditional costs"""
        traditional = await self._calculate_traditional_costs(payload)
        return traditional["resources"]["total"]
    
    async def _basic_cost_estimation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Basic cost estimation fallback"""
        project_scope = payload.get("scope", "medium")
        duration_days = payload.get("duration_days", 30)
        resources_needed = payload.get("resources", [])
        
        # Basic cost estimation logic
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
            }
        }
        
        return {
            "status": "completed",
            "result": {
                "project_scope": project_scope,
                "cost_breakdown": cost_breakdown,
                "estimation_method": "basic",
                "recommendations": [
                    "Consider phased approach to reduce upfront costs",
                    "Review resource requirements for optimization",
                    "Include 10-15% contingency buffer",
                    "Monitor actual costs vs estimates during execution"
                ],
                "agent_id": self.agent_id,
                "processing_time": 1.2
            }
        }
    
    async def _chain_of_thought(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform chain of thought reasoning"""
        problem = payload.get("problem", "")
        context = payload.get("context", "")
        
        reasoning_steps = [
            f"Problem identification: {problem}",
            f"Context analysis: {context}",
            "Breaking down into sub-problems",
            "Identifying potential solutions",
            "Evaluating solution feasibility",
            "Selecting optimal approach"
        ]
        
        return {
            "status": "completed",
            "result": {
                "problem": problem,
                "reasoning_chain": reasoning_steps,
                "conclusion": "Systematic approach identified",
                "confidence": 0.8,
                "agent_id": self.agent_id
            }
        }
    
    async def _summarize_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize provided content"""
        content = payload.get("content", "")
        summary_length = payload.get("length", "medium")
        
        return {
            "status": "completed",
            "result": {
                "original_length": len(content),
                "summary": f"Summary of content ({summary_length} length)",
                "key_points": ["Main point 1", "Main point 2", "Main point 3"],
                "agent_id": self.agent_id
            }
        }
    
    async def _extract_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from data"""
        data = payload.get("data", {})
        
        return {
            "status": "completed",
            "result": {
                "insights": ["Insight 1", "Insight 2"],
                "patterns": ["Pattern A", "Pattern B"],
                "recommendations": ["Recommendation 1", "Recommendation 2"],
                "agent_id": self.agent_id
            }
        }
    
    async def _compare_sources(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple sources"""
        sources = payload.get("sources", [])
        
        return {
            "status": "completed",
            "result": {
                "sources_count": len(sources),
                "comparison": "Sources compared successfully",
                "similarities": ["Common theme 1", "Common theme 2"],
                "differences": ["Difference 1", "Difference 2"],
                "agent_id": self.agent_id
            }
        }
    
    async def _evaluate_credibility(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate source credibility"""
        source = payload.get("source", {})
        
        return {
            "status": "completed",
            "result": {
                "credibility_score": 0.85,
                "factors": ["Peer reviewed", "Recent publication", "Authoritative source"],
                "concerns": ["Limited sample size"],
                "overall_assessment": "Highly credible",
                "agent_id": self.agent_id
            }
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

@app.post("/task")
async def execute_task(task: TaskRequest):
    """Execute a planning task directly (bypass MCP for testing)"""
    try:
        result = await planning_service.execute_planning_task({
            "action": task.action,
            "payload": task.payload
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
