"""
API Gateway for Eunice Research Platform

Provides a unified REST API interface that routes requests to appropriate services
via the MCP (Message Control Protocol) server, following microservices architecture.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from old_src.mcp.client import MCPClient
from old_src.mcp.protocols import ResearchAction
from old_src.queue.manager import queue_manager
from old_src.config.config_manager import ConfigManager
from old_src.utils.error_handler import EuniceError, format_error_for_user

logger = logging.getLogger(__name__)


# =============================================================================
# API MODELS
# =============================================================================

class APIRequest(BaseModel):
    """Base API request model with common fields."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIResponse(BaseModel):
    """Base API response model with common fields."""
    success: bool
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: Optional[List[str]] = None


class ResearchRequest(APIRequest):
    """Research task request model."""
    agent_type: str = Field(..., description="Type of agent to handle the request")
    action: str = Field(..., description="Specific action to perform")
    payload: Dict[str, Any] = Field(..., description="Request payload")
    priority: str = Field(default="normal", description="Task priority")
    timeout: Optional[int] = Field(default=300, description="Task timeout in seconds")


class LiteratureSearchRequest(APIRequest):
    """Literature search request model."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, description="Maximum number of results")
    include_abstracts: bool = Field(default=True, description="Include paper abstracts")
    date_range: Optional[Dict[str, str]] = Field(default=None, description="Date range filter")


class DataAnalysisRequest(APIRequest):
    """Data analysis request model."""
    dataset: Union[str, Dict[str, Any]] = Field(..., description="Dataset path or data")
    analysis_type: str = Field(..., description="Type of analysis to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Analysis parameters")


class TaskStatusResponse(APIResponse):
    """Task status response model."""
    task_id: str
    status: str
    progress: Optional[float] = None
    stage: Optional[str] = None
    estimated_completion: Optional[datetime] = None


# =============================================================================
# API GATEWAY CLASS
# =============================================================================

class APIGateway:
    """
    API Gateway that provides unified REST interface and routes requests
    to appropriate agents via the MCP server.
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.mcp_client: Optional[MCPClient] = None
        self.app = FastAPI(
            title="Eunice Research Platform API",
            description="Unified API gateway for the Eunice research system",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        # Request tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize the API Gateway and connect to MCP server."""
        try:
            # Get MCP configuration
            mcp_config = self.config_manager.get_mcp_config()
            
            # Initialize MCP client
            self.mcp_client = MCPClient(
                host=mcp_config.get('host', '127.0.0.1'),
                port=mcp_config.get('port', 9000)
            )
            
            # Connect to MCP server
            if await self.mcp_client.connect():
                logger.info("API Gateway connected to MCP server")
                return True
            else:
                logger.error("Failed to connect to MCP server")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing API Gateway: {e}")
            return False
    
    async def shutdown(self):
        """Cleanup resources on shutdown."""
        if self.mcp_client:
            await self.mcp_client.disconnect()
            
    def _setup_routes(self):
        """Setup all API routes."""
        
        # Health check endpoint
        @self.app.get("/health", response_model=Dict[str, Any])
        async def health_check():
            """Check the health of the API Gateway and connected services."""
            return await self._health_check()
        
        # Literature search endpoints
        @self.app.post("/api/v2/literature/search", response_model=APIResponse)
        async def search_literature(request: LiteratureSearchRequest):
            """Search academic literature."""
            return await self._handle_literature_search(request)
        
        # Research task endpoints
        @self.app.post("/api/v2/research/task", response_model=APIResponse)
        async def submit_research_task(request: ResearchRequest):
            """Submit a research task for processing."""
            return await self._handle_research_task(request)
        
        @self.app.get("/api/v2/research/task/{task_id}/status", response_model=TaskStatusResponse)
        async def get_task_status(task_id: str):
            """Get the status of a research task."""
            return await self._get_task_status(task_id)
        
        @self.app.delete("/api/v2/research/task/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel a research task."""
            return await self._cancel_task(task_id)
        
        # Data analysis endpoints
        @self.app.post("/api/v2/analysis/data", response_model=APIResponse)
        async def analyze_data(request: DataAnalysisRequest):
            """Perform data analysis."""
            return await self._handle_data_analysis(request)
        
        # Agent management endpoints
        @self.app.get("/api/v2/agents/status", response_model=Dict[str, Any])
        async def get_agents_status():
            """Get status of all registered agents."""
            return await self._get_agents_status()
        
        @self.app.get("/api/v2/agents/capabilities", response_model=Dict[str, List[str]])
        async def get_agent_capabilities():
            """Get capabilities of all registered agents."""
            return await self._get_agent_capabilities()
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check MCP connection
        if self.mcp_client and self.mcp_client.is_connected:
            health_status["services"]["mcp_server"] = {"status": "connected"}
        else:
            health_status["services"]["mcp_server"] = {"status": "disconnected"}
            health_status["status"] = "degraded"
        
        return health_status
    
    async def _handle_literature_search(self, request: LiteratureSearchRequest) -> APIResponse:
        """Route literature search request to Literature Agent."""
        try:
            # Prepare task for Literature Agent
            task_data = {
                "task_id": request.request_id,
                "context_id": str(uuid.uuid4()),
                "agent_type": "literature",
                "action": "search_literature",
                "payload": {
                    "query": request.query,
                    "max_results": request.max_results,
                    "include_abstracts": request.include_abstracts,
                    "date_range": request.date_range
                },
                "priority": "normal",
                "timeout": 300
            }
            
            # Send to MCP server
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Create ResearchAction and submit
            from old_src.mcp.protocols import ResearchAction
            research_action = ResearchAction(
                task_id=task_data["task_id"],
                context_id=task_data["context_id"],
                agent_type=task_data["agent_type"],
                action=task_data["action"],
                payload=task_data["payload"],
                priority=task_data["priority"]
            )
            
            # Submit task and wait for response
            response = await self._submit_and_wait_for_task(research_action)
            
            return APIResponse(
                success=response.get("success", False),
                request_id=request.request_id,
                data=response.get("result"),
                error=response.get("error")
            )
            
        except Exception as e:
            logger.error(f"Error handling literature search: {e}")
            return APIResponse(
                success=False,
                request_id=request.request_id,
                error=str(e)
            )
    
    async def _handle_research_task(self, request: ResearchRequest) -> APIResponse:
        """Route research task to appropriate agent."""
        try:
            # Prepare task data
            task_data = {
                "task_id": request.request_id,
                "context_id": str(uuid.uuid4()),
                "agent_type": request.agent_type,
                "action": request.action,
                "payload": request.payload,
                "priority": request.priority,
                "timeout": request.timeout or 300
            }
            
            # Submit task asynchronously (don't wait for completion)
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Create ResearchAction and send it
            from old_src.mcp.protocols import ResearchAction
            research_action = ResearchAction(
                task_id=task_data["task_id"],
                context_id=task_data["context_id"],
                agent_type=task_data["agent_type"],
                action=task_data["action"],
                payload=task_data["payload"],
                priority=task_data["priority"]
            )
            
            await self.mcp_client.send_task(research_action)
            
            # Track the request
            self.active_requests[request.request_id] = {
                "status": "submitted",
                "submitted_at": datetime.utcnow(),
                "agent_type": request.agent_type,
                "action": request.action
            }
            
            return APIResponse(
                success=True,
                request_id=request.request_id,
                data={"task_id": request.request_id, "status": "submitted"}
            )
            
        except Exception as e:
            logger.error(f"Error handling research task: {e}")
            return APIResponse(
                success=False,
                request_id=request.request_id,
                error=str(e)
            )
    
    async def _handle_data_analysis(self, request: DataAnalysisRequest) -> APIResponse:
        """Route data analysis request to Executor Agent."""
        try:
            # Prepare task for Executor Agent
            # Create ResearchAction
            from old_src.mcp.protocols import ResearchAction
            research_action = ResearchAction(
                task_id=request.request_id,
                context_id=str(uuid.uuid4()),
                agent_type="executor",
                action="analyze_data",
                payload={
                    "dataset": request.dataset,
                    "analysis_type": request.analysis_type,
                    "parameters": request.parameters
                },
                priority="normal"
            )
            
            # Submit task and wait for response
            response = await self._submit_and_wait_for_task(research_action)
            
            return APIResponse(
                success=response.get("success", False),
                request_id=request.request_id,
                data=response.get("result"),
                error=response.get("error")
            )
            
        except Exception as e:
            logger.error(f"Error handling data analysis: {e}")
            return APIResponse(
                success=False,
                request_id=request.request_id,
                error=str(e)
            )
    
    async def _get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Get status of a specific task."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Request task status from MCP server
            status_response = await self.mcp_client.get_task_status(task_id)
            
            # Check local tracking
            local_status = self.active_requests.get(task_id, {})
            
            # Handle None response
            if status_response is None:
                status_response = {"status": "unknown"}
            
            # Safe type conversion for progress
            progress_val = status_response.get("progress")
            if isinstance(progress_val, (int, float)):
                progress = float(progress_val)
            else:
                progress = None
            
            return TaskStatusResponse(
                success=True,
                request_id=task_id,
                task_id=task_id,
                status=status_response.get("status", "unknown"),
                progress=progress,
                stage=status_response.get("stage"),
                data=status_response
            )
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return TaskStatusResponse(
                success=False,
                request_id=task_id,
                task_id=task_id,
                status="error",
                error=str(e)
            )
    
    async def _cancel_task(self, task_id: str) -> APIResponse:
        """Cancel a specific task."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Send cancellation request to MCP server
            await self.mcp_client.cancel_task(task_id)
            
            # Update local tracking
            if task_id in self.active_requests:
                self.active_requests[task_id]["status"] = "cancelled"
            
            return APIResponse(
                success=True,
                request_id=str(uuid.uuid4()),
                data={"task_id": task_id, "status": "cancelled"}
            )
            
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return APIResponse(
                success=False,
                request_id=str(uuid.uuid4()),
                error=str(e)
            )
    
    async def _get_agents_status(self) -> Dict[str, Any]:
        """Get status of all registered agents."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Request agent status from MCP server
            agents_status = await self.mcp_client.get_server_stats()
            
            # Handle None response
            if agents_status is None:
                agents_status = {}
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "agents": agents_status.get("agents", {}),
                "load_balancer": agents_status.get("load_balancer", {}),
                "server": agents_status.get("server", {})
            }
            
        except Exception as e:
            logger.error(f"Error getting agents status: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_agent_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all registered agents."""
        try:
            if not self.mcp_client or not self.mcp_client.is_connected:
                raise HTTPException(status_code=503, detail="MCP server not available")
            
            # Get capabilities from MCP server via stats
            stats = await self.mcp_client.get_server_stats()
            
            # Handle None response
            if stats is None:
                stats = {}
                
            agents = stats.get("agents", {})
            
            capabilities = {}
            agent_details = agents.get("agent_details", {})
            
            for agent_id, details in agent_details.items():
                agent_type = details.get("agent_type", "unknown")
                agent_caps = details.get("capabilities", [])
                
                if agent_type not in capabilities:
                    capabilities[agent_type] = []
                
                # Merge capabilities
                for cap in agent_caps:
                    if cap not in capabilities[agent_type]:
                        capabilities[agent_type].append(cap)
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Error getting agent capabilities: {e}")
            return {}
    
    async def _submit_and_wait_for_task(self, research_action: ResearchAction, timeout: int = 300) -> Dict[str, Any]:
        """Submit a task and wait for its completion."""
        task_id = research_action.task_id
        
        # Null check for MCP client
        if not self.mcp_client:
            return {
                "success": False,
                "error": "MCP client not available",
                "status": "error"
            }
        
        try:
            # Submit the task
            await self.mcp_client.send_task(research_action)
            
            # Wait for completion with timeout
            start_time = datetime.utcnow()
            
            while (datetime.utcnow() - start_time).total_seconds() < timeout:
                # Check task status
                status_response = await self.mcp_client.get_task_status(task_id)
                
                # Handle None response
                if status_response is None:
                    status_response = {}
                    
                status = status_response.get("status", "unknown")
                
                if status == "completed":
                    return {
                        "success": True,
                        "result": status_response.get("result"),
                        "status": status
                    }
                elif status == "failed":
                    return {
                        "success": False,
                        "error": status_response.get("error", "Task failed"),
                        "status": status
                    }
                
                # Wait before next check
                await asyncio.sleep(1)
            
            # Timeout reached
            if self.mcp_client:
                await self.mcp_client.cancel_task(task_id)
            return {
                "success": False,
                "error": f"Task timed out after {timeout} seconds",
                "status": "timeout"
            }
            
        except Exception as e:
            logger.error(f"Error in submit_and_wait_for_task: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "error"
            }


# =============================================================================
# FACTORY FUNCTION & FASTAPI APP
# =============================================================================

def create_api_gateway(config_manager: ConfigManager) -> APIGateway:
    """Factory function to create and configure API Gateway."""
    return APIGateway(config_manager)


# FastAPI app setup
def create_app(config_manager: Optional[ConfigManager] = None) -> FastAPI:
    """Create FastAPI application with API Gateway routes."""
    
    # Import here to avoid circular imports
    from old_src.config.config_manager import ConfigManager as CM
    
    if config_manager is None:
        config_manager = CM()
    
    # Create FastAPI app
    app = FastAPI(
        title="Eunice Research API Gateway",
        description="Unified API Gateway for Research Management Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Create gateway instance
    gateway = APIGateway(config_manager)
    
    # Add routes
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "api-gateway"}
    
    @app.get("/status")
    async def get_status():
        """Get API Gateway and system status"""
        return await gateway._get_agents_status()
    
    @app.post("/literature/search")
    async def literature_search(request: LiteratureSearchRequest):
        """Search academic literature"""
        return await gateway._handle_literature_search(request)
    
    @app.post("/research/tasks")
    async def submit_research_task(request: ResearchRequest):
        """Submit research task"""
        return await gateway._handle_research_task(request)
    
    @app.post("/data/analysis")
    async def analyze_data(request: DataAnalysisRequest):
        """Analyze research data"""
        return await gateway._handle_data_analysis(request)
    
    @app.get("/tasks/{task_id}/status")
    async def get_task_status(task_id: str):
        """Get task status"""
        return await gateway._get_task_status(task_id)
    
    @app.delete("/tasks/{task_id}")
    async def cancel_task(task_id: str):
        """Cancel a task"""
        return await gateway._cancel_task(task_id)
    
    # === QUEUE-BASED ENDPOINTS ===
    
    @app.post("/queue/literature/search")
    async def queue_literature_search(request: LiteratureSearchRequest):
        """Submit literature search to task queue"""
        try:
            # Convert date_range to filters if provided
            filters = {}
            if request.date_range:
                filters['date_range'] = request.date_range
                
            job_id = queue_manager.submit_literature_search(
                query=request.query,
                search_type="academic",  # Default search type
                max_results=request.max_results,
                filters=filters,
                priority=getattr(request, 'priority', 'normal')
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "request_id": request.request_id,
                "status": "queued",
                "message": "Literature search submitted to queue",
                "estimated_completion": "2-10 minutes"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")
    
    @app.post("/queue/research/planning")
    async def queue_research_planning(request: ResearchRequest):
        """Submit research planning to task queue"""
        try:
            job_id = queue_manager.submit_research_planning(
                research_question=request.payload.get('research_question', ''),
                context=request.payload.get('context', ''),
                requirements=request.payload.get('requirements'),
                priority=request.priority
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "request_id": request.request_id,
                "status": "queued",
                "message": "Research planning submitted to queue",
                "estimated_completion": "5-15 minutes"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")
    
    @app.post("/queue/data/analysis")
    async def queue_data_analysis(request: DataAnalysisRequest):
        """Submit data analysis to task queue"""
        try:
            # Convert dataset to string if it's a dict
            dataset_str = request.dataset if isinstance(request.dataset, str) else json.dumps(request.dataset)
            
            job_id = queue_manager.submit_data_analysis(
                dataset=dataset_str,
                analysis_type=request.analysis_type,
                parameters=request.parameters,
                priority=getattr(request, 'priority', 'normal')
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "request_id": request.request_id,
                "status": "queued",
                "message": "Data analysis submitted to queue",
                "estimated_completion": "10-30 minutes"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")
    
    @app.get("/queue/jobs/{job_id}")
    async def get_queue_job_status(job_id: str):
        """Get status of a queued job"""
        try:
            status = queue_manager.get_job_status(job_id)
            return {
                "success": True,
                "job": status
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")
    
    @app.get("/queue/jobs/{job_id}/result")
    async def get_queue_job_result(job_id: str):
        """Get result of a completed queued job"""
        try:
            result = queue_manager.get_job_result(job_id)
            status = queue_manager.get_job_status(job_id)
            
            return {
                "success": True,
                "job_id": job_id,
                "status": status.get('status', 'unknown'),
                "result": result
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get job result: {str(e)}")
    
    @app.delete("/queue/jobs/{job_id}")
    async def cancel_queue_job(job_id: str):
        """Cancel a queued job"""
        try:
            cancelled = queue_manager.cancel_job(job_id)
            return {
                "success": cancelled,
                "job_id": job_id,
                "message": "Job cancelled" if cancelled else "Job could not be cancelled"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")
    
    @app.get("/queue/statistics")
    async def get_queue_statistics():
        """Get queue system statistics"""
        try:
            stats = queue_manager.get_queue_statistics()
            return {
                "success": True,
                "statistics": stats
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
    
    @app.get("/queue/jobs")
    async def get_recent_jobs(limit: int = Query(50, ge=1, le=200)):
        """Get recent jobs across all queues"""
        try:
            jobs = queue_manager.get_recent_jobs(limit=limit)
            return {
                "success": True,
                "jobs": jobs,
                "count": len(jobs)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get recent jobs: {str(e)}")
    
    return app


# Global app instance for uvicorn
app = create_app()
