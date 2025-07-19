"""
Unit tests for Agent Capability Registration (Phase 1)

Tests for agent capability registration, querying, and management.
"""

import pytest
import asyncio
from src.mcp.registry import AgentRegistry
from src.mcp.protocols import AgentRegistration, RegisterCapabilities


class TestAgentCapabilityRegistration:
    """Test agent capability registration functionality"""
    
    @pytest.fixture
    async def registry(self):
        """Create an agent registry for testing"""
        registry = AgentRegistry(heartbeat_timeout=30)
        await registry.start_cleanup_task()
        yield registry
        await registry.stop_cleanup_task()
    
    @pytest.fixture
    def sample_registration(self):
        """Create a sample agent registration"""
        return AgentRegistration(
            agent_id="retriever-001",
            agent_type="Retriever",
            capabilities=["search", "summarize", "extract"],
            max_concurrent=3,
            timeout=60
        )
    
    @pytest.fixture
    def sample_register_capabilities(self):
        """Create a sample RegisterCapabilities request"""
        return RegisterCapabilities(
            agent_id="executor-001",
            agent_type="Executor",
            capabilities=["execute", "validate", "format"],
            max_concurrent=2,
            timeout=120
        )
    
    @pytest.mark.asyncio
    async def test_register_agent(self, registry, sample_registration):
        """Test basic agent registration"""
        success = await registry.register_agent(sample_registration)
        assert success is True
        
        # Check agent is registered
        agent_info = await registry.get_agent_info("retriever-001")
        assert agent_info is not None
        assert agent_info.registration.agent_type == "Retriever"
        assert "search" in agent_info.registration.capabilities
    
    @pytest.mark.asyncio
    async def test_register_capabilities_rpc(self, registry, sample_register_capabilities):
        """Test RegisterCapabilities RPC method"""
        success = await registry.register_capabilities(sample_register_capabilities)
        assert success is True
        
        # Check agent is registered
        agent_info = await registry.get_agent_info("executor-001")
        assert agent_info is not None
        assert agent_info.registration.agent_type == "Executor"
        assert "execute" in agent_info.registration.capabilities
        assert agent_info.registration.max_concurrent == 2
        assert agent_info.registration.timeout == 120
    
    @pytest.mark.asyncio
    async def test_capability_mapping(self, registry, sample_registration):
        """Test that capabilities are correctly mapped to agents"""
        await registry.register_agent(sample_registration)
        
        # Check capability mapping
        capabilities = await registry.get_capabilities()
        assert "search" in capabilities
        assert "summarize" in capabilities
        assert "extract" in capabilities
        
        assert "retriever-001" in capabilities["search"]
        assert "retriever-001" in capabilities["summarize"]
        assert "retriever-001" in capabilities["extract"]
    
    @pytest.mark.asyncio
    async def test_get_available_agents_by_capability(self, registry, sample_registration):
        """Test getting available agents for a specific capability"""
        await registry.register_agent(sample_registration)
        
        # Get agents for search capability
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 1
        assert "retriever-001" in search_agents
        
        # Get agents for non-existent capability
        nonexistent_agents = await registry.get_available_agents("nonexistent")
        assert len(nonexistent_agents) == 0
    
    @pytest.mark.asyncio
    async def test_query_specific_capability(self, registry, sample_registration):
        """Test querying information about a specific capability"""
        await registry.register_agent(sample_registration)
        
        # Query search capability
        result = await registry.query_capabilities("search")
        
        assert result["capability"] == "search"
        assert result["total_agents"] == 1
        assert result["available_agents"] == 1
        assert len(result["agents"]) == 1
        
        agent_info = result["agents"][0]
        assert agent_info["agent_id"] == "retriever-001"
        assert agent_info["agent_type"] == "Retriever"
        assert agent_info["is_available"] is True
        assert agent_info["current_tasks"] == 0
    
    @pytest.mark.asyncio
    async def test_query_all_capabilities(self, registry, sample_registration, sample_register_capabilities):
        """Test querying all capabilities"""
        await registry.register_agent(sample_registration)
        await registry.register_capabilities(sample_register_capabilities)
        
        # Query all capabilities
        result = await registry.query_capabilities()
        
        assert "capabilities" in result
        assert result["total_registered_agents"] == 2
        assert result["total_capabilities"] >= 6  # 3 from each agent
        
        capabilities = result["capabilities"]
        assert "search" in capabilities
        assert "execute" in capabilities
        
        # Check capability counts
        assert capabilities["search"]["total_agents"] == 1
        assert capabilities["search"]["available_agents"] == 1
    
    @pytest.mark.asyncio
    async def test_agent_availability_with_tasks(self, registry, sample_registration):
        """Test agent availability when tasks are assigned"""
        await registry.register_agent(sample_registration)
        
        # Initially available
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 1
        
        # Assign tasks up to max_concurrent
        for i in range(3):  # max_concurrent = 3
            success = await registry.assign_task("retriever-001", f"task-{i}")
            assert success is True
        
        # Should still be available but at capacity
        agent_info = await registry.get_agent_info("retriever-001")
        assert len(agent_info.current_tasks) == 3
        assert agent_info.load_factor == 1.0
        assert agent_info.is_available is False
        
        # Should not appear in available agents
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 0
        
        # Complete a task
        await registry.complete_task("retriever-001", "task-0")
        
        # Should be available again
        agent_info = await registry.get_agent_info("retriever-001")
        assert len(agent_info.current_tasks) == 2
        assert agent_info.is_available is True
        
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 1
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, registry, sample_registration):
        """Test agent unregistration removes capabilities"""
        await registry.register_agent(sample_registration)
        
        # Verify agent is registered
        agent_info = await registry.get_agent_info("retriever-001")
        assert agent_info is not None
        
        # Verify capabilities exist
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 1
        
        # Unregister agent
        success = await registry.unregister_agent("retriever-001")
        assert success is True
        
        # Verify agent is gone
        agent_info = await registry.get_agent_info("retriever-001")
        assert agent_info is None
        
        # Verify capabilities are cleaned up
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 0
        
        capabilities = await registry.get_capabilities()
        assert "search" not in capabilities
    
    @pytest.mark.asyncio
    async def test_multiple_agents_same_capability(self, registry):
        """Test multiple agents with the same capability"""
        # Register two agents with search capability
        reg1 = AgentRegistration(
            agent_id="retriever-001",
            agent_type="Retriever",
            capabilities=["search"],
            max_concurrent=1,
            timeout=60
        )
        
        reg2 = AgentRegistration(
            agent_id="retriever-002",
            agent_type="Retriever",
            capabilities=["search"],
            max_concurrent=2,
            timeout=60
        )
        
        await registry.register_agent(reg1)
        await registry.register_agent(reg2)
        
        # Both should be available for search
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 2
        assert "retriever-001" in search_agents
        assert "retriever-002" in search_agents
        
        # Assign task to first agent to make it unavailable
        await registry.assign_task("retriever-001", "task-1")
        
        # Only second agent should be available
        search_agents = await registry.get_available_agents("search")
        assert len(search_agents) == 1
        assert "retriever-002" in search_agents
        
        # Query capability should show both agents but only one available
        result = await registry.query_capabilities("search")
        assert result["total_agents"] == 2
        assert result["available_agents"] == 1
    
    @pytest.mark.asyncio
    async def test_agent_load_balancing(self, registry):
        """Test that agents are sorted by load factor"""
        # Register agents with different capacities
        reg1 = AgentRegistration(
            agent_id="agent-001",
            agent_type="Worker",
            capabilities=["work"],
            max_concurrent=4,
            timeout=60
        )
        
        reg2 = AgentRegistration(
            agent_id="agent-002", 
            agent_type="Worker",
            capabilities=["work"],
            max_concurrent=2,
            timeout=60
        )
        
        await registry.register_agent(reg1)
        await registry.register_agent(reg2)
        
        # Assign tasks to create different load factors
        await registry.assign_task("agent-001", "task-1")  # 1/4 = 0.25
        await registry.assign_task("agent-002", "task-2")  # 1/2 = 0.5
        
        # Get available agents (should be sorted by load factor)
        work_agents = await registry.get_available_agents("work")
        assert work_agents[0] == "agent-001"  # Lower load factor first
        assert work_agents[1] == "agent-002"


if __name__ == "__main__":
    pytest.main([__file__])
