"""
Agent Registry for MCP Server

Manages agent registration, capabilities, and availability tracking.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .protocols import AgentRegistration, AgentType

logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """Represents a registered agent instance"""
    registration: AgentRegistration
    current_tasks: Set[str] = field(default_factory=set)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    is_healthy: bool = True
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for new tasks"""
        return (
            self.is_healthy and
            len(self.current_tasks) < self.registration.max_concurrent and
            self.registration.status == "available"
        )
    
    @property
    def load_factor(self) -> float:
        """Calculate current load factor (0.0 to 1.0)"""
        if self.registration.max_concurrent == 0:
            return 1.0
        return len(self.current_tasks) / self.registration.max_concurrent


class AgentRegistry:
    """Registry for managing agent instances and capabilities"""
    
    def __init__(self, heartbeat_timeout: int = 30):
        self.agents: Dict[str, AgentInstance] = {}
        self.capabilities: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        self.heartbeat_timeout = heartbeat_timeout
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def register_agent(self, registration: AgentRegistration) -> bool:
        """Register a new agent instance"""
        async with self._lock:
            agent_id = registration.agent_id
            
            # Check if agent already exists
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} already registered, updating registration")
            
            # Create agent instance
            agent_instance = AgentInstance(registration=registration)
            self.agents[agent_id] = agent_instance
            
            # Update capabilities mapping
            for capability in registration.capabilities:
                if capability not in self.capabilities:
                    self.capabilities[capability] = set()
                self.capabilities[capability].add(agent_id)
            
            logger.info(f"Registered agent {agent_id} of type {registration.agent_type}")
            return True
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent instance"""
        async with self._lock:
            if agent_id not in self.agents:
                logger.warning(f"Agent {agent_id} not found for unregistration")
                return False
            
            agent_instance = self.agents[agent_id]
            
            # Remove from capabilities mapping
            for capability in agent_instance.registration.capabilities:
                if capability in self.capabilities:
                    self.capabilities[capability].discard(agent_id)
                    if not self.capabilities[capability]:
                        del self.capabilities[capability]
            
            # Remove agent
            del self.agents[agent_id]
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
    
    async def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            self.agents[agent_id].last_heartbeat = datetime.now()
            self.agents[agent_id].is_healthy = True
            return True
    
    async def assign_task(self, agent_id: str, task_id: str) -> bool:
        """Assign a task to an agent"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent_instance = self.agents[agent_id]
            if not agent_instance.is_available:
                return False
            
            agent_instance.current_tasks.add(task_id)
            logger.debug(f"Assigned task {task_id} to agent {agent_id}")
            return True
    
    async def complete_task(self, agent_id: str, task_id: str) -> bool:
        """Mark a task as completed for an agent"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent_instance = self.agents[agent_id]
            agent_instance.current_tasks.discard(task_id)
            logger.debug(f"Completed task {task_id} for agent {agent_id}")
            return True
    
    async def get_available_agents(self, capability: str) -> List[str]:
        """Get list of available agents for a specific capability"""
        async with self._lock:
            if capability not in self.capabilities:
                return []
            
            available_agents = []
            for agent_id in self.capabilities[capability]:
                if agent_id in self.agents and self.agents[agent_id].is_available:
                    available_agents.append(agent_id)
            
            # Sort by load factor (least loaded first)
            available_agents.sort(
                key=lambda aid: self.agents[aid].load_factor
            )
            
            return available_agents
    
    async def get_agent_info(self, agent_id: str) -> Optional[AgentInstance]:
        """Get information about a specific agent"""
        async with self._lock:
            return self.agents.get(agent_id)
    
    async def get_all_agents(self) -> Dict[str, AgentInstance]:
        """Get all registered agents"""
        async with self._lock:
            return self.agents.copy()
    
    async def get_capabilities(self) -> Dict[str, Set[str]]:
        """Get all available capabilities"""
        async with self._lock:
            return self.capabilities.copy()
    
    async def set_agent_status(self, agent_id: str, status: str) -> bool:
        """Set agent status (available, busy, maintenance)"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            self.agents[agent_id].registration.status = status
            logger.info(f"Set agent {agent_id} status to {status}")
            return True
    
    async def start_cleanup_task(self):
        """Start background task to cleanup unhealthy agents"""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_unhealthy_agents())
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_unhealthy_agents(self):
        """Background task to cleanup unhealthy agents"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_timeout)
                
                current_time = datetime.now()
                unhealthy_agents = []
                
                async with self._lock:
                    for agent_id, agent_instance in self.agents.items():
                        time_since_heartbeat = current_time - agent_instance.last_heartbeat
                        if time_since_heartbeat > timedelta(seconds=self.heartbeat_timeout):
                            agent_instance.is_healthy = False
                            unhealthy_agents.append(agent_id)
                
                # Log unhealthy agents
                if unhealthy_agents:
                    logger.warning(f"Marked agents as unhealthy: {unhealthy_agents}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in agent cleanup task: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        async with self._lock:
            total_agents = len(self.agents)
            healthy_agents = sum(1 for a in self.agents.values() if a.is_healthy)
            available_agents = sum(1 for a in self.agents.values() if a.is_available)
            total_tasks = sum(len(a.current_tasks) for a in self.agents.values())
            
            agent_types = {}
            for agent in self.agents.values():
                agent_type = agent.registration.agent_type
                if agent_type not in agent_types:
                    agent_types[agent_type] = 0
                agent_types[agent_type] += 1
            
            return {
                'total_agents': total_agents,
                'healthy_agents': healthy_agents,
                'available_agents': available_agents,
                'total_active_tasks': total_tasks,
                'agent_types': agent_types,
                'capabilities': list(self.capabilities.keys())
            }
