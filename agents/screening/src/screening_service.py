#!/usr/bin/env python3
"""
Screening & PRISMA Agent Service

Containerized microservice for systematic review screening, PRISMA compliance,
and literature record filtering based on inclusion/exclusion criteria.

Based on the original screening_prisma_agent.py from old_src/agents/screening/
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

import websockets  # type: ignore
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("screening_service")


class Criteria(BaseModel):
    """Inclusion/exclusion criteria data model."""
    name: str = Field(description="Criteria name")
    description: str = Field(description="Criteria description")
    type: Literal["include", "exclude"] = Field(description="Criteria type")


class ScreeningDecision(BaseModel):
    """Screening decision data model."""
    record_id: str = Field(description="Record identifier")
    stage: Literal["title_abstract", "full_text"] = Field(description="Screening stage")
    decision: Literal["include", "exclude", "unsure"] = Field(description="Screening decision")
    reason: str = Field(description="Decision rationale")
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence score")
    timestamp: datetime = Field(default_factory=datetime.now, description="Decision timestamp")


class PRISMASession(BaseModel):
    """PRISMA session data model."""
    session_id: str = Field(description="Session identifier")
    lit_review_id: str = Field(description="Literature review identifier")
    criteria: List[Criteria] = Field(description="Screening criteria")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ScreeningRequest(BaseModel):
    """Request model for screening operations."""
    records: List[Dict[str, Any]] = Field(description="Literature records to screen")
    criteria: List[Dict[str, Any]] = Field(description="Screening criteria")
    stage: Literal["title_abstract", "full_text"] = Field(description="Screening stage")
    session_id: Optional[str] = Field(None, description="PRISMA session ID")


class PRISMAFlowchartData(BaseModel):
    """PRISMA flowchart data model."""
    total_records: int = Field(description="Total records identified")  
    records_screened: int = Field(description="Records screened")
    records_excluded: int = Field(description="Records excluded")
    full_text_assessed: int = Field(description="Full-text articles assessed")
    full_text_excluded: int = Field(description="Full-text articles excluded")
    studies_included: int = Field(description="Studies included in synthesis")
    exclusion_reasons: Dict[str, int] = Field(description="Exclusion reasons with counts")


class TaskRequest(BaseModel):
    """MCP task request model."""
    action: str
    payload: Dict[str, Any]


class ScreeningService:
    """Screening & PRISMA Agent Service."""
    
    def __init__(self):
        """Initialize the screening service."""
        self.agent_id = f"screening-{uuid.uuid4().hex[:8]}"
        self.agent_type = "screening"
        self.service_host = os.getenv("SERVICE_HOST", "0.0.0.0")
        self.service_port = int(os.getenv("SERVICE_PORT", "8004"))
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "ws://mcp-server:9000")
        
        # Service state
        self.websocket = None
        self.mcp_connected = False
        self.start_time = datetime.now()
        
        # Screening data storage
        self.sessions: Dict[str, PRISMASession] = {}
        self.decisions: Dict[str, List[ScreeningDecision]] = {}
        self.prisma_data: Dict[str, PRISMAFlowchartData] = {}
        
        logger.info(f"Screening Service initialized with ID: {self.agent_id}")

    async def start(self):
        """Start the screening service."""
        await self._connect_to_mcp_server()
        logger.info("Screening Service started successfully")

    async def stop(self):
        """Stop the screening service."""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        logger.info("Screening Service stopped")

    async def _connect_to_mcp_server(self):
        """Connect to MCP server with retries."""
        max_retries = 5
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
                
                # Start message handler
                asyncio.create_task(self._handle_mcp_messages())
                
                self.mcp_connected = True
                logger.info("Successfully connected to MCP server")
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to MCP server (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MCP server after all retries")
                    # Continue without MCP connection for direct HTTP access

    async def _register_with_mcp_server(self):
        """Register this agent with the MCP server."""
        capabilities = [
            "screen_records",
            "apply_criteria",
            "create_prisma_session",
            "update_prisma_data",
            "generate_prisma_flowchart",
            "track_screening_decisions",
            "validate_inclusion_exclusion",
            "batch_screening"
        ]
        
        registration_message = {
            "type": "agent_register",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": capabilities,
            "service_info": {
                "host": self.service_host,
                "port": self.service_port,
                "health_endpoint": f"http://{self.service_host}:{self.service_port}/health"
            }
        }
        
        await self.websocket.send(json.dumps(registration_message))
        logger.info(f"Registered with MCP server: {len(capabilities)} capabilities")

    async def _handle_mcp_messages(self):
        """Handle incoming MCP messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "task_request":
                        await self._handle_task_request(data)
                    elif message_type == "registration_confirmed":
                        logger.info("Registration confirmed by MCP server")
                    else:
                        logger.debug(f"Received message type: {message_type}")
                        
                except Exception as e:
                    logger.error(f"Error processing MCP message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("MCP connection closed")
            self.mcp_connected = False
        except Exception as e:
            logger.error(f"MCP message handler error: {e}")

    async def _handle_task_request(self, data: Dict[str, Any]):
        """Handle task request from MCP server."""
        task_id = data.get("task_id")
        task_type = data.get("task_type") 
        task_data = data.get("data", {})
        
        logger.info(f"Received task: {task_type} (ID: {task_id})")
        
        try:
            if task_type == "screen_records":
                result = await self.screen_records(
                    records=task_data.get("records", []),
                    criteria=task_data.get("criteria", []),
                    stage=task_data.get("stage", "title_abstract"),
                    session_id=task_data.get("session_id")
                )
            elif task_type == "create_prisma_session":
                result = await self.create_prisma_session(
                    lit_review_id=task_data.get("lit_review_id"),
                    criteria=task_data.get("criteria", [])
                )
            elif task_type == "generate_prisma_flowchart":
                result = await self.generate_prisma_flowchart(
                    session_id=task_data.get("session_id")
                )
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            # Send result back to MCP server
            await self._send_task_result(task_id, result, "completed")
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self._send_task_result(task_id, None, "failed", str(e))

    async def _send_task_result(self, task_id: str, result: Optional[Dict[str, Any]], status: str, error: Optional[str] = None):
        """Send task result back to MCP server."""
        if not self.websocket or self.websocket.closed:
            return
            
        message = {
            "type": "task_result",
            "task_id": task_id,
            "result": result,
            "status": status,
            "error": error
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send task result: {e}")

    # Core screening functionality
    async def create_prisma_session(self, lit_review_id: str, criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new PRISMA screening session."""
        session_id = f"prisma_{lit_review_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Parse criteria
        parsed_criteria = [Criteria(**c) for c in criteria]
        
        # Create session
        session = PRISMASession(
            session_id=session_id,
            lit_review_id=lit_review_id,
            criteria=parsed_criteria
        )
        
        # Store session
        self.sessions[session_id] = session
        self.decisions[session_id] = []
        self.prisma_data[session_id] = PRISMAFlowchartData(
            total_records=0,
            records_screened=0,
            records_excluded=0,
            full_text_assessed=0,
            full_text_excluded=0,
            studies_included=0,
            exclusion_reasons={}
        )
        
        logger.info(f"Created PRISMA session: {session_id}")
        
        return {
            "session_id": session_id,
            "lit_review_id": lit_review_id,
            "criteria_count": len(parsed_criteria),
            "created_at": session.created_at.isoformat()
        }

    async def screen_records(
        self, 
        records: List[Dict[str, Any]], 
        criteria: List[Dict[str, Any]], 
        stage: str = "title_abstract",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Screen literature records against inclusion/exclusion criteria."""
        
        # Parse criteria
        parsed_criteria = [Criteria(**c) for c in criteria]
        
        screening_results = []
        included_count = 0
        excluded_count = 0
        exclusion_reasons = {}
        
        for record in records:
            record_id = record.get("id", str(uuid.uuid4()))
            title = record.get("title", "")
            abstract = record.get("abstract", "")
            content = f"{title} {abstract}".lower()
            
            # Apply screening criteria
            decision_result = await self._apply_screening_criteria(
                record_id=record_id,
                content=content,
                record=record,
                criteria=parsed_criteria,
                stage=stage
            )
            
            screening_results.append(decision_result)
            
            if decision_result["decision"] == "include":
                included_count += 1
            elif decision_result["decision"] == "exclude":
                excluded_count += 1
                reason = decision_result["reason"]
                exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
            
            # Store decision if session exists
            if session_id and session_id in self.decisions:
                decision = ScreeningDecision(
                    record_id=record_id,
                    stage=stage,
                    decision=decision_result["decision"],
                    reason=decision_result["reason"],
                    confidence=decision_result["confidence"]
                )
                self.decisions[session_id].append(decision)
        
        # Update PRISMA data if session exists
        if session_id and session_id in self.prisma_data:
            prisma_data = self.prisma_data[session_id]
            if stage == "title_abstract":
                prisma_data.records_screened += len(records)
                prisma_data.records_excluded += excluded_count
            elif stage == "full_text":
                prisma_data.full_text_assessed += len(records)
                prisma_data.full_text_excluded += excluded_count
                prisma_data.studies_included += included_count
            
            # Update exclusion reasons
            for reason, count in exclusion_reasons.items():
                prisma_data.exclusion_reasons[reason] = prisma_data.exclusion_reasons.get(reason, 0) + count
        
        logger.info(f"Screened {len(records)} records: {included_count} included, {excluded_count} excluded")
        
        return {
            "total_records": len(records),
            "included": included_count,
            "excluded": excluded_count,
            "unsure": len(records) - included_count - excluded_count,
            "exclusion_reasons": exclusion_reasons,
            "screening_results": screening_results,
            "stage": stage,
            "session_id": session_id
        }

    async def _apply_screening_criteria(
        self,
        record_id: str,
        content: str,
        record: Dict[str, Any],
        criteria: List[Criteria],
        stage: str
    ) -> Dict[str, Any]:
        """Apply screening criteria to a single record."""
        
        # Simple keyword-based screening (can be enhanced with ML models)
        decision = "include"
        reason = "Meets all inclusion criteria"
        confidence = 0.8
        
        # Check exclusion criteria first
        for criterion in criteria:
            if criterion.type == "exclude":
                if await self._check_criterion_match(content, record, criterion):
                    decision = "exclude"
                    reason = f"Excluded: {criterion.description}"
                    confidence = 0.9
                    break
        
        # If not excluded, check inclusion criteria
        if decision == "include":
            inclusion_met = True
            for criterion in criteria:
                if criterion.type == "include":
                    if not await self._check_criterion_match(content, record, criterion):
                        inclusion_met = False
                        decision = "exclude"
                        reason = f"Does not meet inclusion criterion: {criterion.description}"
                        confidence = 0.7
                        break
            
            if not inclusion_met:
                decision = "exclude"
        
        return {
            "record_id": record_id,
            "decision": decision,
            "reason": reason,
            "confidence": confidence,
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        }

    async def _check_criterion_match(
        self, 
        content: str, 
        record: Dict[str, Any], 
        criterion: Criteria
    ) -> bool:
        """Check if a record matches a specific criterion."""
        
        # Simple keyword matching (can be enhanced with NLP/ML)
        criterion_text = criterion.description.lower()
        criterion_keywords = criterion_text.split()
        
        # Check for keyword presence
        matches = sum(1 for keyword in criterion_keywords if keyword in content)
        match_ratio = matches / len(criterion_keywords) if criterion_keywords else 0
        
        # Consider it a match if > 50% of keywords are present
        return match_ratio > 0.5

    async def generate_prisma_flowchart(self, session_id: str) -> Dict[str, Any]:
        """Generate PRISMA flowchart data for a session."""
        if session_id not in self.prisma_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        prisma_data = self.prisma_data[session_id]
        session = self.sessions.get(session_id)
        
        flowchart = {
            "session_id": session_id,
            "lit_review_id": session.lit_review_id if session else None,
            "prisma_data": prisma_data.dict(),
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated PRISMA flowchart for session: {session_id}")
        return flowchart

    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "status": "healthy",
            "agent_type": self.agent_type,
            "mcp_connected": self.mcp_connected,
            "capabilities": [
                "screen_records",
                "apply_criteria", 
                "create_prisma_session",
                "update_prisma_data",
                "generate_prisma_flowchart",
                "track_screening_decisions",
                "validate_inclusion_exclusion",
                "batch_screening"
            ],
            "active_sessions": len(self.sessions),
            "total_decisions": sum(len(decisions) for decisions in self.decisions.values()),
            "uptime_seconds": uptime
        }


# Global service instance
screening_service = ScreeningService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    await screening_service.start()
    yield
    await screening_service.stop()


# FastAPI application
app = FastAPI(
    title="Screening & PRISMA Agent Service",
    description="Microservice for systematic review screening and PRISMA compliance",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return screening_service.get_health_status()


@app.post("/screen")
async def screen_records_endpoint(request: ScreeningRequest):
    """Screen literature records against criteria."""
    return await screening_service.screen_records(
        records=request.records,
        criteria=request.criteria,
        stage=request.stage,
        session_id=request.session_id
    )


@app.post("/prisma/session")
async def create_prisma_session_endpoint(
    lit_review_id: str,
    criteria: List[Dict[str, Any]]
):
    """Create a new PRISMA screening session."""
    return await screening_service.create_prisma_session(lit_review_id, criteria)


@app.get("/prisma/flowchart/{session_id}")
async def get_prisma_flowchart(session_id: str):
    """Get PRISMA flowchart data for a session.""" 
    return await screening_service.generate_prisma_flowchart(session_id)


@app.post("/task")
async def handle_direct_task(request: TaskRequest):
    """Handle direct task requests for testing."""
    task_id = str(uuid.uuid4())
    
    try:
        if request.action == "screen_records":
            result = await screening_service.screen_records(
                records=request.payload.get("records", []),
                criteria=request.payload.get("criteria", []),
                stage=request.payload.get("stage", "title_abstract"),
                session_id=request.payload.get("session_id")
            )
        elif request.action == "create_prisma_session":
            result = await screening_service.create_prisma_session(
                lit_review_id=request.payload.get("lit_review_id"),
                criteria=request.payload.get("criteria", [])
            )
        else:
            raise ValueError(f"Unknown action: {request.action}")
        
        return {
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=screening_service.service_host,
        port=screening_service.service_port,
        log_level="info"
    )
