"""
Screening & PRISMA Agent Service for Eunice Research Platform.

This module provides a containerized Screening & PRISMA Agent that handles:
- Systematic review screening
- PRISMA compliance validation
- Literature record filtering
- Inclusion/exclusion criteria application
- PRISMA flowchart generation

ARCHITECTURE COMPLIANCE:
- ONLY exposes health check API endpoint (/health)
- ALL business operations via MCP protocol exclusively
- NO direct HTTP/REST endpoints for business logic
"""

import asyncio
import json
import logging
import uuid
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, Union

import uvicorn
import websockets
from fastapi import FastAPI
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the standardized health check service
sys.path.append(str(Path(__file__).parent.parent))
from health_check_service import create_health_check_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Criteria:
    """Inclusion/exclusion criteria data model."""
    
    def __init__(self, name: str, description: str, type: Literal["include", "exclude"]):
        self.name = name
        self.description = description
        self.type = type


class ScreeningDecision:
    """Screening decision data model."""
    
    def __init__(self, record_id: str, stage: Literal["title_abstract", "full_text"], 
                 decision: Literal["include", "exclude", "unsure"], reason: str, 
                 confidence: float, timestamp: Optional[datetime] = None):
        self.record_id = record_id
        self.stage = stage
        self.decision = decision
        self.reason = reason
        self.confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
        self.timestamp = timestamp or datetime.now()


class PRISMASession:
    """PRISMA session data model."""
    
    def __init__(self, session_id: str, lit_review_id: str, criteria: List[Criteria]):
        self.session_id = session_id
        self.lit_review_id = lit_review_id
        self.criteria = criteria
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.decisions: List[ScreeningDecision] = []


class PRISMAFlowchartData:
    """PRISMA flowchart data model."""
    
    def __init__(self):
        self.total_records = 0
        self.records_screened = 0
        self.records_excluded = 0
        self.full_text_assessed = 0
        self.full_text_excluded = 0
        self.studies_included = 0
        self.exclusion_reasons: Dict[str, int] = {}


class ScreeningService:
    """
    Screening & PRISMA Agent Service for systematic review screening.
    
    Handles literature screening, PRISMA compliance, and decision tracking
    via MCP protocol.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Screening Agent Service."""
        self.config = config
        self.agent_id = "screening_agent"
        self.agent_type = "screening"
        
        # Service configuration
        self.service_host = config.get("service_host", "0.0.0.0")
        self.service_port = config.get("service_port", 8004)
        self.mcp_server_url = config.get("mcp_server_url", "ws://mcp-server:9000")
        
        # MCP connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.mcp_connected = False
        self.should_run = True
        
        # Screening data storage
        self.sessions: Dict[str, PRISMASession] = {}
        self.screening_decisions: Dict[str, List[ScreeningDecision]] = {}
        self.flowchart_data: Dict[str, PRISMAFlowchartData] = {}
        
        # Task processing queue
        self.task_queue = asyncio.Queue()
        
        # Start time for uptime tracking
        self.start_time = datetime.now()
        
        # Capabilities
        self.capabilities = [
            "screen_literature",
            "apply_criteria",
            "generate_prisma_flowchart",
            "validate_prisma_compliance",
            "track_screening_decisions",
            "manage_screening_sessions"
        ]
        
        logger.info(f"Screening Agent Service initialized on port {self.service_port}")
    
    async def start(self):
        """Start the Screening Agent Service."""
        try:
            # Connect to MCP server
            await self._connect_to_mcp_server()
            
            # Start task processing
            asyncio.create_task(self._process_task_queue())
            
            # Listen for MCP messages
            await self._listen_for_tasks()
            
            logger.info("Screening Agent Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Screening Agent Service: {e}")
            raise
    
    async def stop(self):
        """Stop the Screening Agent Service."""
        try:
            self.should_run = False
            
            # Close MCP connection
            if self.websocket:
                await self.websocket.close()
            
            logger.info("Screening Agent Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Screening Agent Service: {e}")
    
    async def _connect_to_mcp_server(self):
        """Connect to MCP server."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MCP server at {self.mcp_server_url} (attempt {attempt + 1})")
                
                self.websocket = await websockets.connect(
                    self.mcp_server_url,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                # Register with MCP server
                await self._register_with_mcp_server()
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    raise
    
    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        if not self.websocket:
            raise Exception("WebSocket connection not available")
            
        registration_message = {
            "jsonrpc": "2.0",
            "method": "agent/register",
            "params": {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "capabilities": self.capabilities,
                "service_info": {
                    "host": self.service_host,
                    "port": self.service_port,
                    "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
                }
            },
            "id": f"register_{self.agent_id}"
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(self.capabilities)} capabilities")
    
    async def _listen_for_tasks(self):
        """Listen for tasks from MCP server."""
        try:
            if not self.websocket:
                logger.error("Cannot listen for tasks: no websocket connection")
                return
                
            logger.info("Starting to listen for tasks from MCP server")
            
            async for message in self.websocket:
                if not self.should_run:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.task_queue.put(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse MCP message: {e}")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")
                    
        except ConnectionClosed:
            logger.warning("MCP server connection closed")
            self.mcp_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in message listener: {e}")
            self.mcp_connected = False
    
    async def _process_task_queue(self):
        """Process tasks from the MCP queue."""
        while self.should_run:
            try:
                # Get task from queue
                task_data = await self.task_queue.get()
                
                # Process the task
                result = await self._process_screening_task(task_data)
                
                # Send result back to MCP server
                if self.websocket and self.mcp_connected:
                    response = {
                        "jsonrpc": "2.0",
                        "id": task_data.get("id"),
                        "result": result
                    }
                    await self.websocket.send(json.dumps(response))
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(1)
    
    async def _process_screening_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a screening-related task."""
        try:
            method = task_data.get("method", "")
            params = task_data.get("params", {})
            
            # Route to appropriate handler
            if method == "task/execute":
                task_type = params.get("task_type", "")
                data = params.get("data", {})
                
                if task_type == "screen_literature":
                    return await self._handle_screen_literature(data)
                elif task_type == "apply_criteria":
                    return await self._handle_apply_criteria(data)
                elif task_type == "generate_prisma_flowchart":
                    return await self._handle_generate_prisma_flowchart(data)
                elif task_type == "validate_prisma_compliance":
                    return await self._handle_validate_prisma_compliance(data)
                elif task_type == "track_screening_decisions":
                    return await self._handle_track_screening_decisions(data)
                elif task_type == "manage_screening_sessions":
                    return await self._handle_manage_screening_sessions(data)
                else:
                    return {
                        "status": "failed",
                        "error": f"Unknown task type: {task_type}",
                        "timestamp": datetime.now().isoformat()
                    }
            elif method == "agent/ping":
                return {"status": "alive", "timestamp": datetime.now().isoformat()}
            elif method == "agent/status":
                return await self._get_agent_status()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown method: {method}",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error processing screening task: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_screen_literature(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle literature screening request."""
        try:
            records = data.get("records", [])
            criteria = data.get("criteria", [])
            stage = data.get("stage", "title_abstract")
            session_id = data.get("session_id")
            
            if not records:
                return {
                    "status": "failed",
                    "error": "Records are required for screening",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Perform screening
            screening_results = await self._screen_records(records, criteria, stage)
            
            # Store decisions if session ID provided
            if session_id:
                if session_id not in self.screening_decisions:
                    self.screening_decisions[session_id] = []
                self.screening_decisions[session_id].extend(screening_results)
            
            return {
                "status": "completed",
                "session_id": session_id,
                "stage": stage,
                "screening_results": [self._decision_to_dict(decision) for decision in screening_results],
                "total_screened": len(screening_results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to screen literature: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_apply_criteria(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle criteria application request."""
        try:
            record = data.get("record", {})
            criteria = data.get("criteria", [])
            
            if not record:
                return {
                    "status": "failed",
                    "error": "Record is required for criteria application",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Apply criteria to record
            decision = await self._apply_criteria_to_record(record, criteria)
            
            return {
                "status": "completed",
                "record_id": record.get("id", "unknown"),
                "decision": self._decision_to_dict(decision),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to apply criteria: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_generate_prisma_flowchart(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PRISMA flowchart generation request."""
        try:
            session_id = data.get("session_id", "")
            
            if not session_id:
                return {
                    "status": "failed",
                    "error": "Session ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Generate flowchart data
            flowchart_data = await self._generate_flowchart_data(session_id)
            
            return {
                "status": "completed",
                "session_id": session_id,
                "flowchart_data": self._flowchart_to_dict(flowchart_data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate PRISMA flowchart: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_validate_prisma_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PRISMA compliance validation request."""
        try:
            session_id = data.get("session_id", "")
            
            if not session_id:
                return {
                    "status": "failed",
                    "error": "Session ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Validate compliance
            compliance_result = await self._validate_compliance(session_id)
            
            return {
                "status": "completed",
                "session_id": session_id,
                "compliance_result": compliance_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to validate PRISMA compliance: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_track_screening_decisions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screening decision tracking request."""
        try:
            session_id = data.get("session_id", "")
            
            if not session_id:
                return {
                    "status": "failed",
                    "error": "Session ID is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Get screening decisions
            decisions = self.screening_decisions.get(session_id, [])
            
            # Calculate statistics
            total_decisions = len(decisions)
            include_count = sum(1 for d in decisions if d.decision == "include")
            exclude_count = sum(1 for d in decisions if d.decision == "exclude")
            unsure_count = sum(1 for d in decisions if d.decision == "unsure")
            
            return {
                "status": "completed",
                "session_id": session_id,
                "total_decisions": total_decisions,
                "include_count": include_count,
                "exclude_count": exclude_count,
                "unsure_count": unsure_count,
                "decisions": [self._decision_to_dict(d) for d in decisions],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track screening decisions: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_manage_screening_sessions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screening session management request."""
        try:
            operation = data.get("operation", "")
            
            if operation == "create":
                return await self._create_screening_session(data)
            elif operation == "get":
                return await self._get_screening_session(data)
            elif operation == "update":
                return await self._update_screening_session(data)
            elif operation == "delete":
                return await self._delete_screening_session(data)
            elif operation == "list":
                return await self._list_screening_sessions()
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown operation: {operation}",
                    "available_operations": ["create", "get", "update", "delete", "list"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to manage screening sessions: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _screen_records(self, records: List[Dict[str, Any]], criteria: List[Dict[str, Any]], 
                            stage: str) -> List[ScreeningDecision]:
        """Screen a list of records against criteria."""
        decisions = []
        
        for record in records:
            decision = await self._apply_criteria_to_record(record, criteria, stage)
            decisions.append(decision)
        
        return decisions
    
    async def _apply_criteria_to_record(self, record: Dict[str, Any], criteria: List[Dict[str, Any]], 
                                      stage: str = "title_abstract") -> ScreeningDecision:
        """Apply screening criteria to a single record."""
        record_id = record.get("id", str(uuid.uuid4()))
        
        # Validate stage
        valid_stage: Literal["title_abstract", "full_text"] = "title_abstract" if stage == "title_abstract" else "full_text"
        
        # Simple criteria matching logic
        include_score = 0
        exclude_score = 0
        reasons = []
        
        title = record.get("title", "").lower()
        abstract = record.get("abstract", "").lower()
        content = f"{title} {abstract}"
        
        for criterion in criteria:
            criterion_type = criterion.get("type", "include")
            criterion_keywords = criterion.get("keywords", [])
            criterion_name = criterion.get("name", "")
            
            # Check if any keywords match
            matches = any(keyword.lower() in content for keyword in criterion_keywords)
            
            if matches:
                if criterion_type == "include":
                    include_score += 1
                    reasons.append(f"Matches inclusion criterion: {criterion_name}")
                else:
                    exclude_score += 1
                    reasons.append(f"Matches exclusion criterion: {criterion_name}")
        
        # Make decision based on scores
        if exclude_score > 0:
            decision: Literal["include", "exclude", "unsure"] = "exclude"
            confidence = min(0.8, exclude_score / len(criteria))
        elif include_score > 0:
            decision = "include"
            confidence = min(0.8, include_score / len(criteria))
        else:
            decision = "unsure"
            confidence = 0.3
        
        reason = "; ".join(reasons) if reasons else "No matching criteria found"
        
        return ScreeningDecision(
            record_id=record_id,
            stage=valid_stage,
            decision=decision,
            reason=reason,
            confidence=confidence
        )
    
    async def _generate_flowchart_data(self, session_id: str) -> PRISMAFlowchartData:
        """Generate PRISMA flowchart data for a session."""
        flowchart = PRISMAFlowchartData()
        
        decisions = self.screening_decisions.get(session_id, [])
        
        # Calculate flowchart statistics
        flowchart.total_records = len(decisions)
        flowchart.records_screened = len([d for d in decisions if d.stage == "title_abstract"])
        flowchart.records_excluded = len([d for d in decisions if d.decision == "exclude" and d.stage == "title_abstract"])
        flowchart.full_text_assessed = len([d for d in decisions if d.stage == "full_text"])
        flowchart.full_text_excluded = len([d for d in decisions if d.decision == "exclude" and d.stage == "full_text"])
        flowchart.studies_included = len([d for d in decisions if d.decision == "include"])
        
        # Count exclusion reasons
        exclusion_reasons = {}
        for decision in decisions:
            if decision.decision == "exclude":
                reason = decision.reason
                exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
        
        flowchart.exclusion_reasons = exclusion_reasons
        
        # Store for future reference
        self.flowchart_data[session_id] = flowchart
        
        return flowchart
    
    async def _validate_compliance(self, session_id: str) -> Dict[str, Any]:
        """Validate PRISMA compliance for a session."""
        session = self.sessions.get(session_id)
        decisions = self.screening_decisions.get(session_id, [])
        
        compliance_issues = []
        compliance_score = 1.0
        
        # Check for basic requirements
        if not session:
            compliance_issues.append("Session not found")
            compliance_score = 0.0
        elif not session.criteria:
            compliance_issues.append("No screening criteria defined")
            compliance_score -= 0.3
        
        if not decisions:
            compliance_issues.append("No screening decisions recorded")
            compliance_score -= 0.5
        else:
            # Check for stage coverage
            title_abstract_decisions = [d for d in decisions if d.stage == "title_abstract"]
            full_text_decisions = [d for d in decisions if d.stage == "full_text"]
            
            if not title_abstract_decisions:
                compliance_issues.append("Missing title/abstract screening stage")
                compliance_score -= 0.2
            
            if not full_text_decisions:
                compliance_issues.append("Missing full-text screening stage")
                compliance_score -= 0.2
        
        compliance_score = max(0.0, compliance_score)
        
        return {
            "compliant": len(compliance_issues) == 0,
            "compliance_score": compliance_score,
            "issues": compliance_issues,
            "total_decisions": len(decisions)
        }
    
    async def _create_screening_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new screening session."""
        session_id = data.get("session_id", str(uuid.uuid4()))
        lit_review_id = data.get("lit_review_id", "")
        criteria_data = data.get("criteria", [])
        
        # Convert criteria data to Criteria objects
        criteria = []
        for c in criteria_data:
            criteria.append(Criteria(
                name=c.get("name", ""),
                description=c.get("description", ""),
                type=c.get("type", "include")
            ))
        
        # Create session
        session = PRISMASession(session_id, lit_review_id, criteria)
        self.sessions[session_id] = session
        
        return {
            "created": True,
            "session_id": session_id,
            "lit_review_id": lit_review_id,
            "criteria_count": len(criteria)
        }
    
    async def _get_screening_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a screening session."""
        session_id = data.get("session_id", "")
        session = self.sessions.get(session_id)
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        return {
            "session_id": session.session_id,
            "lit_review_id": session.lit_review_id,
            "criteria": [{"name": c.name, "description": c.description, "type": c.type} for c in session.criteria],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
    
    async def _update_screening_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a screening session."""
        session_id = data.get("session_id", "")
        session = self.sessions.get(session_id)
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        # Update criteria if provided
        if "criteria" in data:
            criteria_data = data["criteria"]
            criteria = []
            for c in criteria_data:
                criteria.append(Criteria(
                    name=c.get("name", ""),
                    description=c.get("description", ""),
                    type=c.get("type", "include")
                ))
            session.criteria = criteria
        
        session.updated_at = datetime.now()
        
        return {"updated": True, "session_id": session_id}
    
    async def _delete_screening_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a screening session."""
        session_id = data.get("session_id", "")
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            # Also clean up related data
            if session_id in self.screening_decisions:
                del self.screening_decisions[session_id]
            if session_id in self.flowchart_data:
                del self.flowchart_data[session_id]
            return {"deleted": True, "session_id": session_id}
        
        return {"error": f"Session {session_id} not found"}
    
    async def _list_screening_sessions(self) -> Dict[str, Any]:
        """List all screening sessions."""
        sessions = []
        for session_id, session in self.sessions.items():
            sessions.append({
                "session_id": session.session_id,
                "lit_review_id": session.lit_review_id,
                "criteria_count": len(session.criteria),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            })
        
        return {
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
    
    def _decision_to_dict(self, decision: ScreeningDecision) -> Dict[str, Any]:
        """Convert ScreeningDecision to dictionary."""
        return {
            "record_id": decision.record_id,
            "stage": decision.stage,
            "decision": decision.decision,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "timestamp": decision.timestamp.isoformat()
        }
    
    def _flowchart_to_dict(self, flowchart: PRISMAFlowchartData) -> Dict[str, Any]:
        """Convert PRISMAFlowchartData to dictionary."""
        return {
            "total_records": flowchart.total_records,
            "records_screened": flowchart.records_screened,
            "records_excluded": flowchart.records_excluded,
            "full_text_assessed": flowchart.full_text_assessed,
            "full_text_excluded": flowchart.full_text_excluded,
            "studies_included": flowchart.studies_included,
            "exclusion_reasons": flowchart.exclusion_reasons
        }
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": "ready" if self.mcp_connected else "disconnected",
            "capabilities": self.capabilities,
            "mcp_connected": self.mcp_connected,
            "active_sessions": len(self.sessions),
            "total_decisions": sum(len(decisions) for decisions in self.screening_decisions.values()),
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
screening_service: Optional[ScreeningService] = None


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP connection status for health check."""
    if screening_service:
        return {
            "connected": screening_service.mcp_connected,
            "last_heartbeat": datetime.now().isoformat()
        }
    return {"connected": False, "last_heartbeat": "never"}


def get_additional_metadata() -> Dict[str, Any]:
    """Get additional metadata for health check."""
    if screening_service:
        return {
            "capabilities": screening_service.capabilities,
            "active_sessions": len(screening_service.sessions),
            "total_decisions": sum(len(decisions) for decisions in screening_service.screening_decisions.values()),
            "agent_id": screening_service.agent_id
        }
    return {}


# Create health check only FastAPI application
app = create_health_check_app(
    agent_type="screening",
    agent_id="screening-agent",
    version="1.0.0",
    get_mcp_status=get_mcp_status,
    get_additional_metadata=get_additional_metadata
)


async def main():
    """Main entry point for the screening agent service."""
    global screening_service
    
    try:
        # Load configuration
        config_path = Path("/app/config/config.json")
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {
                "service_host": "0.0.0.0",
                "service_port": 8004,
                "mcp_server_url": "ws://mcp-server:9000"
            }
        
        # Initialize service
        screening_service = ScreeningService(config)
        
        # Start FastAPI health check server in background
        config_uvicorn = uvicorn.Config(
            app,
            host=config["service_host"],
            port=config["service_port"],
            log_level="info"
        )
        server = uvicorn.Server(config_uvicorn)
        
        logger.info("🚨 ARCHITECTURE COMPLIANCE: Screening Agent")
        logger.info("✅ ONLY health check API exposed")
        logger.info("✅ All business operations via MCP protocol exclusively")
        
        # Start server and MCP service concurrently
        await asyncio.gather(
            server.serve(),
            screening_service.start()
        )
        
    except KeyboardInterrupt:
        logger.info("Screening agent shutdown requested")
    except Exception as e:
        logger.error(f"Screening agent failed: {e}")
        sys.exit(1)
    finally:
        if screening_service:
            await screening_service.stop()


if __name__ == "__main__":
    asyncio.run(main())
