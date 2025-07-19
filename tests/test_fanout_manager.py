"""
Unit tests for Task Fan-out Manager (Phase 2)

Tests for parallel task dispatch, result aggregation, and fan-out strategies.
"""

import pytest
import asyncio
from src.mcp.fanout_manager import TaskFanoutManager, FanoutStrategy, FanoutTask
from src.mcp.protocols import ResearchAction


class TestTaskFanoutManager:
    """Test the task fanout manager"""
    
    @pytest.fixture
    async def fanout_manager(self):
        """Create a fanout manager for testing"""
        return TaskFanoutManager()
    
    @pytest.fixture
    def search_task(self):
        """Create a search task suitable for fan-out"""
        return ResearchAction(
            task_id="search-parallel",
            context_id="context-1",
            agent_type="Retriever",
            action="search",
            payload={
                "queries": ["AI research", "machine learning", "neural networks", "deep learning"],
                "max_results": 10
            },
            parallelism=2
        )
    
    @pytest.fixture
    def analysis_task(self):
        """Create an analysis task suitable for fan-out"""
        return ResearchAction(
            task_id="analyze-parallel",
            context_id="context-1",
            agent_type="Reasoner",
            action="analyze",
            payload={
                "data_chunks": ["chunk1", "chunk2", "chunk3", "chunk4"],
                "analysis_type": "sentiment"
            },
            parallelism=2
        )
    
    @pytest.mark.asyncio
    async def test_create_fanout_task_round_robin(self, fanout_manager, search_task):
        """Test creating fanout task with round-robin strategy"""
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=2,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        assert len(subtasks) == 2
        assert all(st.task_id.startswith("search-parallel_sub_") for st in subtasks)
        assert all(st.parent_task_id == "search-parallel" for st in subtasks)
        assert all(st.agent_type == "Retriever" for st in subtasks)
        assert all(st.action == "search" for st in subtasks)
        
        # Check that queries were split
        task1_queries = subtasks[0].payload.get('queries', [])
        task2_queries = subtasks[1].payload.get('queries', [])
        assert len(task1_queries) == 2
        assert len(task2_queries) == 2
        assert set(task1_queries + task2_queries) == set(search_task.payload['queries'])
    
    @pytest.mark.asyncio
    async def test_create_fanout_task_broadcast(self, fanout_manager, search_task):
        """Test creating fanout task with broadcast strategy"""
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=3,
            strategy=FanoutStrategy.BROADCAST
        )
        
        assert len(subtasks) == 3
        
        # All subtasks should have the same payload in broadcast mode
        for subtask in subtasks:
            assert subtask.payload['queries'] == search_task.payload['queries']
            assert subtask.payload['max_results'] == search_task.payload['max_results']
    
    @pytest.mark.asyncio
    async def test_complete_subtask_success(self, fanout_manager, search_task):
        """Test completing subtasks successfully"""
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=2,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        # Complete first subtask
        result1 = {
            'results': [{'title': 'AI Paper 1', 'relevance': 0.9}],
            'sources': ['source1.com'],
            'relevance_score': 0.9
        }
        
        aggregated = await fanout_manager.complete_subtask(
            subtasks[0].task_id, 
            result1,
            success=True
        )
        
        # Should not have aggregated result yet (only 1 of 2 completed)
        assert aggregated is None
        
        # Complete second subtask
        result2 = {
            'results': [{'title': 'AI Paper 2', 'relevance': 0.8}],
            'sources': ['source2.com'],
            'relevance_score': 0.8
        }
        
        aggregated = await fanout_manager.complete_subtask(
            subtasks[1].task_id,
            result2,
            success=True
        )
        
        # Should now have aggregated result
        assert aggregated is not None
        assert aggregated['action'] == 'search'
        assert len(aggregated['results']) == 2
        assert aggregated['total_results'] == 2
        assert set(aggregated['sources']) == {'source1.com', 'source2.com'}
        assert aggregated['success_rate'] == 1.0
    
    @pytest.mark.asyncio
    async def test_partial_failure_aggregation(self, fanout_manager, search_task):
        """Test aggregation when some subtasks fail"""
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=3,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        # Complete first subtask successfully
        result1 = {'results': [{'title': 'AI Paper 1'}], 'sources': ['source1.com']}
        await fanout_manager.complete_subtask(subtasks[0].task_id, result1, success=True)
        
        # Fail second subtask
        await fanout_manager.complete_subtask(subtasks[1].task_id, {}, success=False)
        
        # Complete third subtask successfully
        result3 = {'results': [{'title': 'AI Paper 3'}], 'sources': ['source3.com']}
        aggregated = await fanout_manager.complete_subtask(subtasks[2].task_id, result3, success=True)
        
        # Should have aggregated result with partial success
        assert aggregated is not None
        assert aggregated['success_rate'] == 2/3  # 2 successful out of 3
        assert len(aggregated['results']) == 2  # Only successful results
        assert aggregated['subtask_count'] == 2  # Only successful subtasks counted in results
    
    @pytest.mark.asyncio
    async def test_analysis_task_aggregation(self, fanout_manager, analysis_task):
        """Test aggregation for analysis tasks"""
        subtasks = await fanout_manager.create_fanout_task(
            analysis_task,
            parallelism=2,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        # Complete analysis subtasks
        result1 = {
            'insights': ['Insight 1', 'Insight 2'],
            'confidence': 0.85,
            'conclusion': 'Positive sentiment'
        }
        
        result2 = {
            'insights': ['Insight 3'],
            'confidence': 0.75,
            'conclusion': 'Mixed sentiment'
        }
        
        await fanout_manager.complete_subtask(subtasks[0].task_id, result1, success=True)
        aggregated = await fanout_manager.complete_subtask(subtasks[1].task_id, result2, success=True)
        
        assert aggregated is not None
        assert aggregated['action'] == 'analyze'
        assert len(aggregated['insights']) == 3
        assert aggregated['average_confidence'] == 0.8  # (0.85 + 0.75) / 2
        assert len(aggregated['conclusions']) == 2
    
    @pytest.mark.asyncio
    async def test_custom_task_splitter(self, fanout_manager):
        """Test fanout with custom task splitter"""
        async def custom_splitter(research_action, parallelism):
            """Custom splitter that creates location-based search tasks"""
            locations = ['USA', 'Europe', 'Asia']
            subtasks = []
            
            for i, location in enumerate(locations[:parallelism]):
                subtask_id = f"{research_action.task_id}_location_{location}"
                payload = research_action.payload.copy()
                payload['location'] = location
                
                subtask = ResearchAction(
                    task_id=subtask_id,
                    context_id=research_action.context_id,
                    agent_type=research_action.agent_type,
                    action=research_action.action,
                    payload=payload,
                    parent_task_id=research_action.task_id
                )
                subtasks.append(subtask)
            
            return subtasks
        
        search_task = ResearchAction(
            task_id="location-search",
            context_id="context-1",
            agent_type="Retriever",
            action="search",
            payload={"query": "technology trends"},
            parallelism=3
        )
        
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=3,
            custom_splitter=custom_splitter
        )
        
        assert len(subtasks) == 3
        locations = [st.payload['location'] for st in subtasks]
        assert set(locations) == {'USA', 'Europe', 'Asia'}
        assert all('location_' in st.task_id for st in subtasks)
    
    @pytest.mark.asyncio
    async def test_custom_aggregator(self, fanout_manager):
        """Test fanout with custom aggregation function"""
        async def custom_aggregator(fanout_task):
            """Custom aggregator that calculates weighted average"""
            total_weight = 0
            weighted_sum = 0
            
            for subtask_id, result in fanout_task.partial_results.items():
                weight = result.get('weight', 1)
                value = result.get('value', 0)
                total_weight += weight
                weighted_sum += weight * value
            
            return {
                'weighted_average': weighted_sum / max(total_weight, 1),
                'total_weight': total_weight,
                'custom_aggregation': True
            }
        
        task = ResearchAction(
            task_id="weighted-task",
            context_id="context-1",
            agent_type="Calculator",
            action="calculate",
            payload={},
            parallelism=2
        )
        
        subtasks = await fanout_manager.create_fanout_task(
            task,
            parallelism=2,
            custom_aggregator=custom_aggregator
        )
        
        # Complete subtasks with weighted results
        await fanout_manager.complete_subtask(
            subtasks[0].task_id,
            {'weight': 3, 'value': 10},
            success=True
        )
        
        aggregated = await fanout_manager.complete_subtask(
            subtasks[1].task_id,
            {'weight': 2, 'value': 15},
            success=True
        )
        
        assert aggregated is not None
        assert aggregated['custom_aggregation'] is True
        assert aggregated['total_weight'] == 5
        # (3*10 + 2*15) / 5 = 60/5 = 12
        assert aggregated['weighted_average'] == 12.0
    
    @pytest.mark.asyncio
    async def test_fanout_task_info(self, fanout_manager, search_task):
        """Test getting fanout task information"""
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=2,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        # Get task info
        info = await fanout_manager.get_fanout_task_info("search-parallel")
        
        assert info is not None
        assert info['parent_task_id'] == "search-parallel"
        assert info['parallelism'] == 2
        assert info['strategy'] == 'round_robin'
        assert info['total_subtasks'] == 2
        assert info['completed_subtasks'] == 0
        assert info['is_complete'] is False
        assert info['success_rate'] == 0.0
        
        # Complete one subtask and check updated info
        await fanout_manager.complete_subtask(subtasks[0].task_id, {'test': 'result'}, success=True)
        
        updated_info = await fanout_manager.get_fanout_task_info("search-parallel")
        assert updated_info['completed_subtasks'] == 1
        assert updated_info['success_rate'] == 0.5
        assert updated_info['is_complete'] is False
    
    @pytest.mark.asyncio
    async def test_cancel_fanout_task(self, fanout_manager, search_task):
        """Test cancelling a fanout task"""
        subtasks = await fanout_manager.create_fanout_task(
            search_task,
            parallelism=3,
            strategy=FanoutStrategy.ROUND_ROBIN
        )
        
        subtask_ids = [st.task_id for st in subtasks]
        
        # Cancel the fanout task
        cancelled = await fanout_manager.cancel_fanout_task("search-parallel")
        
        assert set(cancelled) == set(subtask_ids)
        
        # Task should no longer exist
        info = await fanout_manager.get_fanout_task_info("search-parallel")
        assert info is None
        
        # Completing cancelled subtasks should fail
        result = await fanout_manager.complete_subtask(subtasks[0].task_id, {}, success=True)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fanout_manager_stats(self, fanout_manager, search_task, analysis_task):
        """Test fanout manager statistics"""
        # Create multiple fanout tasks
        await fanout_manager.create_fanout_task(search_task, parallelism=2)
        await fanout_manager.create_fanout_task(analysis_task, parallelism=3)
        
        stats = await fanout_manager.get_stats()
        
        assert stats['total_fanout_tasks'] == 2
        assert stats['total_subtasks'] == 5  # 2 + 3
        assert stats['active_subtasks'] == 5
        assert stats['completed_fanout_tasks'] == 0
        assert stats['average_parallelism'] == 2.5  # (2 + 3) / 2
        assert 'strategy_distribution' in stats


class TestFanoutTask:
    """Test the FanoutTask dataclass"""
    
    def test_fanout_task_creation(self):
        """Test FanoutTask creation and properties"""
        task = FanoutTask(
            parent_task_id="parent-123",
            parallelism=3,
            strategy=FanoutStrategy.BROADCAST
        )
        
        assert task.parent_task_id == "parent-123"
        assert task.parallelism == 3
        assert task.strategy == FanoutStrategy.BROADCAST
        assert task.completed_subtasks == 0
        assert task.failed_subtasks == 0
        assert task.is_complete is True  # No subtasks yet
        assert task.success_rate == 0.0
    
    def test_fanout_task_with_subtasks(self):
        """Test FanoutTask with subtasks"""
        task = FanoutTask(
            parent_task_id="parent-123",
            subtask_ids=["sub1", "sub2", "sub3"],
            parallelism=3
        )
        
        assert task.is_complete is False  # Has subtasks but none completed
        assert task.success_rate == 0.0
        
        # Complete some subtasks
        task.completed_subtasks = 2
        task.failed_subtasks = 1
        
        assert task.is_complete is True  # All subtasks accounted for
        assert task.success_rate == 2/3  # 2 out of 3 successful
    
    def test_fanout_task_serialization(self):
        """Test FanoutTask to_dict serialization"""
        original_action = ResearchAction(
            task_id="original",
            context_id="ctx",
            agent_type="Agent",
            action="test",
            payload={}
        )
        
        task = FanoutTask(
            parent_task_id="parent-123",
            subtask_ids=["sub1", "sub2"],
            original_action=original_action,
            parallelism=2,
            strategy=FanoutStrategy.LOAD_BALANCED,
            completed_subtasks=1,
            failed_subtasks=0
        )
        
        data = task.to_dict()
        
        assert data['parent_task_id'] == "parent-123"
        assert data['subtask_ids'] == ["sub1", "sub2"]
        assert data['parallelism'] == 2
        assert data['strategy'] == 'load_balanced'
        assert data['completed_subtasks'] == 1
        assert data['failed_subtasks'] == 0
        assert data['total_subtasks'] == 2
        assert data['is_complete'] is False
        assert data['success_rate'] == 0.5


if __name__ == "__main__":
    pytest.main([__file__])
