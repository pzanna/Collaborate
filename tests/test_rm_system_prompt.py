"""
Unit tests for RM System Prompt with Parallelism (Phase 2)

Tests for parallelism suggestion logic and prompt validation.
"""

import pytest
from src.mcp.rm_system_prompt import (
    get_enhanced_rm_prompt,
    validate_parallelism_value,
    suggest_parallelism
)


class TestRMSystemPrompt:
    """Test the enhanced RM system prompt functionality"""
    
    def test_get_enhanced_rm_prompt(self):
        """Test that enhanced prompt is returned and contains parallelism content"""
        prompt = get_enhanced_rm_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 1000  # Should be substantial
        assert "parallelism" in prompt.lower()
        assert "parallel" in prompt.lower()
        assert "Message Control Protocol" in prompt
        assert "Research Manager AI" in prompt
    
    def test_prompt_contains_parallelism_guidelines(self):
        """Test that prompt contains specific parallelism guidelines"""
        prompt = get_enhanced_rm_prompt()
        
        # Check for key parallelism concepts
        assert "Parallelism Guidelines" in prompt
        assert "When to Use Parallelism" in prompt
        assert "When NOT to Use Parallelism" in prompt
        assert "Parallelism Values:" in prompt
        assert "Task Complexity Analysis" in prompt
        
        # Check for specific parallelism scenarios
        assert "Large Search Operations" in prompt
        assert "Bulk Analysis Tasks" in prompt
        assert "Independent Computations" in prompt
        assert "Multi-Source Data Collection" in prompt
    
    def test_prompt_contains_examples(self):
        """Test that prompt contains parallelism examples"""
        prompt = get_enhanced_rm_prompt()
        
        # Check for example scenarios
        assert "Literature Review" in prompt
        assert "Data Analysis" in prompt
        assert "Sequential Summary" in prompt
        
        # Check for JSON examples
        assert '"parallelism": 4' in prompt
        assert '"parallelism": 3' in prompt
        assert '"parallelism": 1' in prompt
    
    def test_prompt_contains_decision_framework(self):
        """Test that prompt contains decision framework"""
        prompt = get_enhanced_rm_prompt()
        
        assert "Parallelism Decision Framework" in prompt
        assert "IF task involves multiple independent items" in prompt
        assert "SET parallelism =" in prompt


class TestParallelismValidation:
    """Test parallelism value validation"""
    
    def test_validate_parallelism_value_valid_range(self):
        """Test validation of valid parallelism values"""
        assert validate_parallelism_value(1) == 1
        assert validate_parallelism_value(5) == 5
        assert validate_parallelism_value(10) == 10
    
    def test_validate_parallelism_value_below_minimum(self):
        """Test validation of values below minimum"""
        assert validate_parallelism_value(0) == 1
        assert validate_parallelism_value(-1) == 1
        assert validate_parallelism_value(-10) == 1
    
    def test_validate_parallelism_value_above_maximum(self):
        """Test validation of values above maximum"""
        assert validate_parallelism_value(11) == 10
        assert validate_parallelism_value(20) == 10
        assert validate_parallelism_value(100) == 10
    
    def test_validate_parallelism_value_edge_cases(self):
        """Test edge cases for parallelism validation"""
        assert validate_parallelism_value(1) == 1  # Minimum valid
        assert validate_parallelism_value(10) == 10  # Maximum valid


class TestParallelismSuggestion:
    """Test parallelism suggestion logic"""
    
    def test_suggest_parallelism_search_tasks(self):
        """Test parallelism suggestions for search tasks"""
        # Search tasks should have higher parallelism
        assert suggest_parallelism("search papers", 5) > 1
        assert suggest_parallelism("retrieve documents", 10) > 1
        assert suggest_parallelism("collect data from APIs", 8) > 1
        assert suggest_parallelism("gather information", 6) > 1
        assert suggest_parallelism("fetch results", 4) > 1
    
    def test_suggest_parallelism_analysis_tasks(self):
        """Test parallelism suggestions for analysis tasks"""
        # Analysis tasks with multiple items should have parallelism
        assert suggest_parallelism("analyze data chunks", 6) > 1
        assert suggest_parallelism("process documents", 8) > 1
        assert suggest_parallelism("compute statistics", 4) > 1
        assert suggest_parallelism("calculate metrics", 10) > 1
    
    def test_suggest_parallelism_sequential_tasks(self):
        """Test parallelism suggestions for sequential tasks"""
        # Sequential tasks should have parallelism = 1
        assert suggest_parallelism("synthesize results", 5) == 1
        assert suggest_parallelism("summarize findings", 10) == 1
        assert suggest_parallelism("conclude analysis", 3) == 1
        assert suggest_parallelism("integrate data", 8) == 1
        assert suggest_parallelism("combine outputs", 4) == 1
        assert suggest_parallelism("merge results", 6) == 1
        assert suggest_parallelism("finalize report", 2) == 1
    
    def test_suggest_parallelism_single_item(self):
        """Test parallelism suggestions for single item tasks"""
        # Single item tasks should have parallelism = 1
        assert suggest_parallelism("search papers", 1) == 1
        assert suggest_parallelism("analyze document", 1) == 1
        assert suggest_parallelism("process file", 1) == 1
    
    def test_suggest_parallelism_small_counts(self):
        """Test parallelism suggestions for small item counts"""
        # Small item counts should have limited parallelism
        assert suggest_parallelism("search papers", 2) <= 2
        assert suggest_parallelism("analyze files", 3) <= 3
        assert suggest_parallelism("process data", 2) <= 2
    
    def test_suggest_parallelism_medium_counts(self):
        """Test parallelism suggestions for medium item counts"""
        # Medium item counts should have moderate parallelism
        result = suggest_parallelism("search databases", 5)
        assert 1 <= result <= 3
        
        result = suggest_parallelism("analyze documents", 6)
        assert 1 <= result <= 3
    
    def test_suggest_parallelism_large_counts(self):
        """Test parallelism suggestions for large item counts"""
        # Large item counts should have higher parallelism
        result = suggest_parallelism("retrieve papers", 15)
        assert 1 <= result <= 6
        
        result = suggest_parallelism("process files", 20)
        assert 1 <= result <= 6
        
        result = suggest_parallelism("collect data", 50)
        assert 1 <= result <= 6
    
    def test_suggest_parallelism_no_keywords(self):
        """Test parallelism suggestions for tasks without keywords"""
        # Tasks without specific keywords should default to 1
        assert suggest_parallelism("do something", 5) == 1
        assert suggest_parallelism("handle request", 10) == 1
        assert suggest_parallelism("execute task", 3) == 1
    
    def test_suggest_parallelism_mixed_keywords(self):
        """Test parallelism suggestions for tasks with mixed keywords"""
        # Tasks with both parallel and sequential keywords
        # Sequential should take precedence
        assert suggest_parallelism("search and summarize", 5) == 1
        assert suggest_parallelism("retrieve and synthesize", 8) == 1
        assert suggest_parallelism("collect and integrate", 4) == 1
    
    def test_suggest_parallelism_bounds(self):
        """Test that suggested parallelism stays within bounds"""
        # Test various scenarios to ensure bounds are respected
        for item_count in [1, 5, 10, 20, 50, 100]:
            for task_type in ["search", "analyze", "process", "retrieve"]:
                task_desc = f"{task_type} items"
                result = suggest_parallelism(task_desc, item_count)
                assert 1 <= result <= 6, f"Failed for {task_desc} with {item_count} items"


class TestParallelismExamples:
    """Test specific parallelism examples from the prompt"""
    
    def test_literature_review_example(self):
        """Test parallelism for literature review scenario"""
        task_desc = "search papers neural networks deep learning transformer"
        parallelism = suggest_parallelism(task_desc, 4)
        assert parallelism >= 2  # Should suggest parallel execution
    
    def test_data_analysis_example(self):
        """Test parallelism for data analysis scenario"""
        task_desc = "analyze data chunks trend analysis"
        parallelism = suggest_parallelism(task_desc, 3)
        assert parallelism >= 2  # Should suggest parallel execution
    
    def test_sequential_summary_example(self):
        """Test parallelism for sequential summary scenario"""
        task_desc = "synthesize findings from previous tasks"
        parallelism = suggest_parallelism(task_desc, 5)
        assert parallelism == 1  # Should not suggest parallel execution
    
    def test_api_collection_example(self):
        """Test parallelism for API data collection"""
        task_desc = "collect stock data from multiple financial APIs"
        parallelism = suggest_parallelism(task_desc, 8)
        assert parallelism >= 3  # Should suggest high parallelism
    
    def test_simulation_example(self):
        """Test parallelism for simulation tasks"""
        task_desc = "run simulations with different parameters compute results"
        parallelism = suggest_parallelism(task_desc, 6)
        assert parallelism >= 2  # Should suggest parallel execution


class TestIntegration:
    """Integration tests for RM prompt functionality"""
    
    def test_complete_workflow(self):
        """Test complete workflow from prompt to parallelism suggestion"""
        # Get the enhanced prompt
        prompt = get_enhanced_rm_prompt()
        assert "parallelism" in prompt.lower()
        
        # Test various task scenarios
        scenarios = [
            ("search academic papers on AI", 10, 2),  # Should be parallel
            ("analyze customer reviews sentiment", 20, 2),  # Should be parallel  
            ("synthesize all research findings", 5, 1),  # Should be sequential
            ("retrieve data from APIs", 8, 2),  # Should be parallel
        ]
        
        for task_desc, item_count, min_expected in scenarios:
            suggested = suggest_parallelism(task_desc, item_count)
            validated = validate_parallelism_value(suggested)
            
            assert suggested >= min_expected
            assert 1 <= validated <= 10
    
    def test_prompt_length_and_structure(self):
        """Test that prompt has appropriate length and structure"""
        prompt = get_enhanced_rm_prompt()
        
        # Should be comprehensive but not excessive
        assert 5000 <= len(prompt) <= 15000
        
        # Should have proper structure markers
        structure_markers = [
            "## 🔧 System Overview:",
            "## 📨 Message Protocol",
            "## 🚀 Parallelism Guidelines:",
            "## 📊 Example Parallelism Scenarios:",
            "## 🔄 Task Flow with Parallelism:",
            "## 🎯 Parallelism Decision Framework:",
            "## 📋 Important Instructions:",
            "## 🚫 Restrictions:"
        ]
        
        for marker in structure_markers:
            assert marker in prompt, f"Missing structure marker: {marker}"


if __name__ == "__main__":
    pytest.main([__file__])
