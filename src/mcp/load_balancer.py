"""
Enhanced Load Balancer for MCP Server

Provides advanced load balancing strategies, health monitoring,
and performance optimization for agent request routing.

Part of Architecture.md Phase 2: Enhanced MCP Server Capabilities
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import logging

from .protocols import ResearchAction, AgentResponse
from .registry import AgentRegistry, AgentInstance


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    ADAPTIVE = "adaptive"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    agent_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    consecutive_failures: int = 0
    health_score: float = 1.0
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 1.0 - self.success_rate


@dataclass
class CircuitBreaker:
    """Circuit breaker for agent failure handling."""
    agent_id: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    
    state: str = "closed"  # closed, open, half_open
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0
    
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        if self.state == "half_open":
            self.state = "closed"
            self.half_open_calls = 0
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self.state = "open"
        elif self.state == "half_open":
            self.state = "open"
            self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if calls can be executed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if (self.last_failure_time and 
                (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout):
                self.state = "half_open"
                self.half_open_calls = 0
                return True
            return False
        elif self.state == "half_open":
            return self.half_open_calls < self.half_open_max_calls
        return False
    
    def execute(self) -> bool:
        """Try to execute a call."""
        if self.can_execute():
            if self.state == "half_open":
                self.half_open_calls += 1
            return True
        return False


class EnhancedLoadBalancer:
    """
    Enhanced load balancer with multiple strategies and circuit breakers.
    
    Implements Architecture.md Phase 2 requirements:
    - Load balancing for agent requests
    - Agent health monitoring and failover
    - Performance metrics and monitoring
    - Circuit breaker patterns
    """
    
    def __init__(
        self,
        agent_registry: AgentRegistry,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ADAPTIVE,
        health_check_interval: int = 30,
        circuit_breaker_enabled: bool = True
    ):
        self.agent_registry = agent_registry
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.circuit_breaker_enabled = circuit_breaker_enabled
        
        # Performance tracking
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Load balancing state
        self.round_robin_index: Dict[str, int] = defaultdict(int)
        self.request_counts: Dict[str, int] = defaultdict(int)
        
        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the load balancer."""
        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Enhanced load balancer started")
    
    async def stop(self):
        """Stop the load balancer."""
        self._is_running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Enhanced load balancer stopped")
    
    async def select_agent(self, capability: str, task: ResearchAction) -> Optional[str]:
        """
        Select the best agent for a task based on the configured strategy.
        
        Args:
            capability: Required capability
            task: The task to be executed
            
        Returns:
            Selected agent ID or None if no suitable agent available
        """
        available_agents = await self.agent_registry.get_available_agents(capability)
        
        if not available_agents:
            self.logger.warning(f"No available agents for capability: {capability}")
            return None
        
        # Filter out agents with open circuit breakers
        if self.circuit_breaker_enabled:
            filtered_agents = []
            for agent_id in available_agents:
                circuit_breaker = self._get_circuit_breaker(agent_id)
                if circuit_breaker.execute():
                    filtered_agents.append(agent_id)
            available_agents = filtered_agents
        
        if not available_agents:
            self.logger.warning(f"All agents for capability {capability} have open circuit breakers")
            return None
        
        # Apply load balancing strategy
        selected_agent = await self._apply_strategy(capability, available_agents, task)
        
        if selected_agent:
            self.logger.debug(f"Selected agent {selected_agent} for capability {capability} using {self.strategy.value}")
        
        return selected_agent
    
    async def record_request_start(self, agent_id: str, task_id: str):
        """Record the start of a request."""
        metrics = self._get_agent_metrics(agent_id)
        metrics.total_requests += 1
        metrics.last_request_time = datetime.now()
        
        # Store start time for response time calculation
        setattr(metrics, f"_start_time_{task_id}", time.time())
    
    async def record_request_success(self, agent_id: str, task_id: str, response: AgentResponse):
        """Record a successful request."""
        metrics = self._get_agent_metrics(agent_id)
        metrics.successful_requests += 1
        metrics.consecutive_failures = 0
        
        # Calculate response time
        start_time = getattr(metrics, f"_start_time_{task_id}", None)
        if start_time:
            response_time = time.time() - start_time
            metrics.total_response_time += response_time
            metrics.response_times.append(response_time)
            delattr(metrics, f"_start_time_{task_id}")
        
        # Update circuit breaker
        if self.circuit_breaker_enabled:
            circuit_breaker = self._get_circuit_breaker(agent_id)
            circuit_breaker.record_success()
        
        # Update health score
        await self._update_health_score(agent_id)
        
        self.logger.debug(f"Recorded success for agent {agent_id}, task {task_id}")
    
    async def record_request_failure(self, agent_id: str, task_id: str, error: Exception):
        """Record a failed request."""
        metrics = self._get_agent_metrics(agent_id)
        metrics.failed_requests += 1
        metrics.consecutive_failures += 1
        
        # Clean up start time
        if hasattr(metrics, f"_start_time_{task_id}"):
            delattr(metrics, f"_start_time_{task_id}")
        
        # Update circuit breaker
        if self.circuit_breaker_enabled:
            circuit_breaker = self._get_circuit_breaker(agent_id)
            circuit_breaker.record_failure()
        
        # Update health score
        await self._update_health_score(agent_id)
        
        self.logger.warning(f"Recorded failure for agent {agent_id}, task {task_id}: {error}")
    
    async def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent."""
        return self.agent_metrics.get(agent_id)
    
    async def get_all_metrics(self) -> Dict[str, AgentMetrics]:
        """Get metrics for all agents."""
        return self.agent_metrics.copy()
    
    async def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get overall load balancer statistics."""
        total_requests = sum(m.total_requests for m in self.agent_metrics.values())
        total_successes = sum(m.successful_requests for m in self.agent_metrics.values())
        total_failures = sum(m.failed_requests for m in self.agent_metrics.values())
        
        circuit_breaker_states = {
            agent_id: cb.state 
            for agent_id, cb in self.circuit_breakers.items()
        }
        
        return {
            "strategy": self.strategy.value,
            "total_requests": total_requests,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": total_successes / total_requests if total_requests > 0 else 1.0,
            "active_agents": len(self.agent_metrics),
            "circuit_breaker_states": circuit_breaker_states,
            "health_check_enabled": self._is_running
        }
    
    # Private methods
    
    async def _apply_strategy(self, capability: str, agents: List[str], task: ResearchAction) -> Optional[str]:
        """Apply the configured load balancing strategy."""
        if not agents:
            return None
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return await self._round_robin_select(capability, agents)
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_select(agents)
        elif self.strategy == LoadBalanceStrategy.LEAST_RESPONSE_TIME:
            return await self._least_response_time_select(agents)
        elif self.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_select(capability, agents)
        elif self.strategy == LoadBalanceStrategy.ADAPTIVE:
            return await self._adaptive_select(agents, task)
        else:
            # Default to round robin
            return await self._round_robin_select(capability, agents)
    
    async def _round_robin_select(self, capability: str, agents: List[str]) -> str:
        """Round robin selection."""
        index = self.round_robin_index[capability] % len(agents)
        self.round_robin_index[capability] = (index + 1) % len(agents)
        return agents[index]
    
    async def _least_connections_select(self, agents: List[str]) -> str:
        """Select agent with least active connections."""
        agent_loads = []
        for agent_id in agents:
            agent_info = await self.agent_registry.get_agent_info(agent_id)
            if agent_info:
                agent_loads.append((agent_id, len(agent_info.current_tasks)))
        
        # Sort by current load
        agent_loads.sort(key=lambda x: x[1])
        return agent_loads[0][0] if agent_loads else agents[0]
    
    async def _least_response_time_select(self, agents: List[str]) -> str:
        """Select agent with lowest average response time."""
        agent_times = []
        for agent_id in agents:
            metrics = self._get_agent_metrics(agent_id)
            agent_times.append((agent_id, metrics.average_response_time))
        
        # Sort by response time
        agent_times.sort(key=lambda x: x[1])
        return agent_times[0][0] if agent_times else agents[0]
    
    async def _weighted_round_robin_select(self, capability: str, agents: List[str]) -> str:
        """Weighted round robin based on agent health scores."""
        # Simple implementation: repeat agents based on health score
        weighted_agents = []
        for agent_id in agents:
            metrics = self._get_agent_metrics(agent_id)
            weight = max(1, int(metrics.health_score * 10))  # 1-10 weight
            weighted_agents.extend([agent_id] * weight)
        
        if weighted_agents:
            index = self.round_robin_index[f"weighted_{capability}"] % len(weighted_agents)
            self.round_robin_index[f"weighted_{capability}"] = (index + 1) % len(weighted_agents)
            return weighted_agents[index]
        
        return agents[0]
    
    async def _adaptive_select(self, agents: List[str], task: ResearchAction) -> str:
        """Adaptive selection combining multiple factors."""
        scored_agents = []
        
        for agent_id in agents:
            agent_info = await self.agent_registry.get_agent_info(agent_id)
            metrics = self._get_agent_metrics(agent_id)
            
            if not agent_info:
                continue
            
            # Calculate composite score (lower is better)
            load_factor = agent_info.load_factor  # 0.0 to 1.0
            response_time_factor = min(1.0, metrics.average_response_time / 10.0)  # normalize to 0-1
            failure_rate = metrics.failure_rate
            health_factor = 1.0 - metrics.health_score
            
            # Weighted composite score
            composite_score = (
                0.3 * load_factor +           # Current load
                0.3 * response_time_factor +  # Performance
                0.2 * failure_rate +          # Reliability  
                0.2 * health_factor           # Health
            )
            
            scored_agents.append((agent_id, composite_score))
        
        # Sort by score (lower is better)
        scored_agents.sort(key=lambda x: x[1])
        return scored_agents[0][0] if scored_agents else agents[0]
    
    def _get_agent_metrics(self, agent_id: str) -> AgentMetrics:
        """Get or create agent metrics."""
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
        return self.agent_metrics[agent_id]
    
    def _get_circuit_breaker(self, agent_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for agent."""
        if agent_id not in self.circuit_breakers:
            self.circuit_breakers[agent_id] = CircuitBreaker(agent_id=agent_id)
        return self.circuit_breakers[agent_id]
    
    async def _update_health_score(self, agent_id: str):
        """Update agent health score based on recent performance."""
        metrics = self._get_agent_metrics(agent_id)
        
        # Base health score on success rate and consecutive failures
        success_rate = metrics.success_rate
        failure_penalty = min(0.5, metrics.consecutive_failures * 0.1)
        
        # Consider response time (penalize slow agents)
        response_time_penalty = min(0.3, metrics.average_response_time / 30.0)
        
        health_score = success_rate - failure_penalty - response_time_penalty
        metrics.health_score = max(0.0, min(1.0, health_score))
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while self._is_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    async def _perform_health_checks(self):
        """Perform health checks on all agents."""
        all_agents = await self.agent_registry.get_all_agents()
        
        for agent_id, agent_info in all_agents.items():
            # Check heartbeat timeout
            time_since_heartbeat = datetime.now() - agent_info.last_heartbeat
            if time_since_heartbeat.seconds > self.health_check_interval * 2:
                # Mark as unhealthy
                await self.agent_registry.set_agent_status(agent_id, "unhealthy")
                self.logger.warning(f"Agent {agent_id} marked unhealthy due to missed heartbeat")
            
            # Update health scores
            await self._update_health_score(agent_id)
        
        self.logger.debug("Health check completed for all agents")
