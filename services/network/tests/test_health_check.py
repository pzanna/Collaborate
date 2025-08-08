"""
Unit tests for network health check module.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.health_check import HealthCheck
from src.models import HealthStatus


class TestHealthCheck:
    """Test cases for HealthCheck class."""
    
    @pytest.mark.asyncio
    async def test_health_check_initialization(self, test_config):
        """Test health check initialization."""
        health_check = HealthCheck(test_config)
        
        assert health_check.config == test_config
        assert health_check.request_count == 0
        assert health_check.last_check_time is None
        assert len(health_check.check_history) == 0
    
    @pytest.mark.asyncio
    async def test_basic_health_check(self, test_config):
        """Test basic health check functionality."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.Process') as mock_process:
            
            # Mock system resources
            mock_memory.return_value = MagicMock(percent=50.0, available=8000000000)
            mock_cpu.return_value = 25.0
            mock_disk.return_value = MagicMock(used=1000000000, total=2000000000, free=1000000000)
            
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
            mock_process_instance.cpu_percent.return_value = 10.0
            mock_process.return_value = mock_process_instance
            
            status = await health_check.check_health()
            
            assert isinstance(status, HealthStatus)
            assert status.status == "healthy"
            assert status.service == test_config.service.name
            assert status.version == test_config.service.version
            assert "uptime" in status.checks
            assert "memory" in status.checks
            assert "cpu" in status.checks
            assert "disk" in status.checks
    
    @pytest.mark.asyncio
    async def test_uptime_check(self, test_config):
        """Test uptime check functionality."""
        health_check = HealthCheck(test_config)
        
        # Wait a bit to ensure uptime > 0
        await asyncio.sleep(0.1)
        
        uptime_result = await health_check._check_uptime()
        
        assert uptime_result["status"] == "healthy"
        assert uptime_result["uptime_seconds"] > 0
        assert "uptime_human" in uptime_result
    
    @pytest.mark.asyncio
    async def test_memory_check_healthy(self, test_config):
        """Test memory check with healthy status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.Process') as mock_process:
            
            mock_memory.return_value = MagicMock(percent=50.0, available=8000000000)
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
            mock_process.return_value = mock_process_instance
            
            memory_result = await health_check._check_memory()
            
            assert memory_result["status"] == "healthy"
            assert memory_result["system_memory_percent"] == 50.0
            assert memory_result["system_memory_available"] == 8000000000
    
    @pytest.mark.asyncio
    async def test_memory_check_degraded(self, test_config):
        """Test memory check with degraded status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.Process') as mock_process:
            
            mock_memory.return_value = MagicMock(percent=80.0, available=1000000000)
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
            mock_process.return_value = mock_process_instance
            
            memory_result = await health_check._check_memory()
            
            assert memory_result["status"] == "degraded"
            assert memory_result["system_memory_percent"] == 80.0
    
    @pytest.mark.asyncio
    async def test_memory_check_unhealthy(self, test_config):
        """Test memory check with unhealthy status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.Process') as mock_process:
            
            mock_memory.return_value = MagicMock(percent=95.0, available=100000000)
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
            mock_process.return_value = mock_process_instance
            
            memory_result = await health_check._check_memory()
            
            assert memory_result["status"] == "unhealthy"
            assert memory_result["system_memory_percent"] == 95.0
    
    @pytest.mark.asyncio
    async def test_cpu_check_healthy(self, test_config):
        """Test CPU check with healthy status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.Process') as mock_process, \
             patch('psutil.cpu_count') as mock_cpu_count:
            
            mock_cpu.return_value = 25.0
            mock_process_instance = MagicMock()
            mock_process_instance.cpu_percent.return_value = 10.0
            mock_process.return_value = mock_process_instance
            mock_cpu_count.return_value = 4
            
            cpu_result = await health_check._check_cpu()
            
            assert cpu_result["status"] == "healthy"
            assert cpu_result["system_cpu_percent"] == 25.0
            assert cpu_result["process_cpu_percent"] == 10.0
            assert cpu_result["cpu_count"] == 4
    
    @pytest.mark.asyncio
    async def test_cpu_check_degraded(self, test_config):
        """Test CPU check with degraded status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.Process') as mock_process, \
             patch('psutil.cpu_count') as mock_cpu_count:
            
            mock_cpu.return_value = 80.0
            mock_process_instance = MagicMock()
            mock_process_instance.cpu_percent.return_value = 70.0
            mock_process.return_value = mock_process_instance
            mock_cpu_count.return_value = 4
            
            cpu_result = await health_check._check_cpu()
            
            assert cpu_result["status"] == "degraded"
            assert cpu_result["system_cpu_percent"] == 80.0
    
    @pytest.mark.asyncio
    async def test_cpu_check_unhealthy(self, test_config):
        """Test CPU check with unhealthy status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.Process') as mock_process, \
             patch('psutil.cpu_count') as mock_cpu_count:
            
            mock_cpu.return_value = 95.0
            mock_process_instance = MagicMock()
            mock_process_instance.cpu_percent.return_value = 90.0
            mock_process.return_value = mock_process_instance
            mock_cpu_count.return_value = 4
            
            cpu_result = await health_check._check_cpu()
            
            assert cpu_result["status"] == "unhealthy"
            assert cpu_result["system_cpu_percent"] == 95.0
    
    @pytest.mark.asyncio
    async def test_disk_check_healthy(self, test_config):
        """Test disk check with healthy status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk.return_value = MagicMock(
                used=500000000,
                total=1000000000,
                free=500000000
            )
            
            disk_result = await health_check._check_disk()
            
            assert disk_result["status"] == "healthy"
            assert disk_result["disk_usage_percent"] == 50.0
            assert disk_result["disk_free"] == 500000000
            assert disk_result["disk_total"] == 1000000000
    
    @pytest.mark.asyncio
    async def test_disk_check_degraded(self, test_config):
        """Test disk check with degraded status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk.return_value = MagicMock(
                used=900000000,
                total=1000000000,
                free=100000000
            )
            
            disk_result = await health_check._check_disk()
            
            assert disk_result["status"] == "degraded"
            assert disk_result["disk_usage_percent"] == 90.0
    
    @pytest.mark.asyncio
    async def test_disk_check_unhealthy(self, test_config):
        """Test disk check with unhealthy status."""
        health_check = HealthCheck(test_config)
        
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk.return_value = MagicMock(
                used=980000000,
                total=1000000000,
                free=20000000
            )
            
            disk_result = await health_check._check_disk()
            
            assert disk_result["status"] == "unhealthy"
            assert disk_result["disk_usage_percent"] == 98.0
    
    @pytest.mark.asyncio
    async def test_database_check_healthy(self, test_config):
        """Test database check with healthy status."""
        health_check = HealthCheck(test_config)
        
        # Mock successful database connection
        db_result = await health_check._check_database()
        
        assert db_result["status"] == "healthy"
        assert "message" in db_result
    
    @pytest.mark.asyncio
    async def test_mcp_server_check_healthy(self, test_config):
        """Test MCP server check with healthy status."""
        health_check = HealthCheck(test_config)
        
        # Mock successful MCP connection
        mcp_result = await health_check._check_mcp_server()
        
        assert mcp_result["status"] == "healthy"
        assert "message" in mcp_result
        assert mcp_result["server_url"] == test_config.mcp.server_url
    
    @pytest.mark.asyncio
    async def test_service_specific_check(self, test_config):
        """Test service-specific health checks."""
        health_check = HealthCheck(test_config)
        
        service_result = await health_check._check_service_specific()
        
        assert service_result["status"] == "healthy"
        assert "checks" in service_result
        assert "message" in service_result
    
    @pytest.mark.asyncio
    async def test_overall_status_determination(self, test_config):
        """Test overall status determination logic."""
        health_check = HealthCheck(test_config)
        
        # All healthy
        checks = {
            "check1": {"status": "healthy"},
            "check2": {"status": "healthy"}
        }
        status = health_check._determine_overall_status(checks)
        assert status == "healthy"
        
        # One degraded
        checks = {
            "check1": {"status": "healthy"},
            "check2": {"status": "degraded"}
        }
        status = health_check._determine_overall_status(checks)
        assert status == "degraded"
        
        # One unhealthy
        checks = {
            "check1": {"status": "healthy"},
            "check2": {"status": "unhealthy"}
        }
        status = health_check._determine_overall_status(checks)
        assert status == "unhealthy"
        
        # Mixed unhealthy and degraded (unhealthy takes precedence)
        checks = {
            "check1": {"status": "degraded"},
            "check2": {"status": "unhealthy"}
        }
        status = health_check._determine_overall_status(checks)
        assert status == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, test_config):
        """Test metrics collection."""
        health_check = HealthCheck(test_config)
        
        # Increment request count
        health_check.increment_request_count()
        health_check.increment_request_count()
        health_check.increment_request_count()
        
        metrics = await health_check._collect_metrics()
        
        assert metrics["request_count"] == 3
        assert "uptime" in metrics
        assert "requests_per_second" in metrics
    
    def test_uptime_formatting(self, test_config):
        """Test uptime formatting."""
        health_check = HealthCheck(test_config)
        
        # Test different uptime values
        assert health_check._format_uptime(30) == "30s"
        assert health_check._format_uptime(90) == "1m 30s"
        assert health_check._format_uptime(3661) == "1h 1m 1s"
        assert health_check._format_uptime(90061) == "1d 1h 1m 1s"
    
    def test_request_count_increment(self, test_config):
        """Test request count increment."""
        health_check = HealthCheck(test_config)
        
        assert health_check.request_count == 0
        
        health_check.increment_request_count()
        assert health_check.request_count == 1
        
        health_check.increment_request_count()
        assert health_check.request_count == 2
    
    @pytest.mark.asyncio
    async def test_check_history(self, test_config):
        """Test health check history management."""
        health_check = HealthCheck(test_config)
        
        # Mock system resources for consistent results
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.Process') as mock_process:
            
            mock_memory.return_value = MagicMock(percent=50.0, available=8000000000)
            mock_cpu.return_value = 25.0
            mock_disk.return_value = MagicMock(used=1000000000, total=2000000000, free=1000000000)
            
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=100000000, vms=200000000)
            mock_process_instance.cpu_percent.return_value = 10.0
            mock_process.return_value = mock_process_instance
            
            # Perform multiple health checks
            for i in range(3):
                await health_check.check_health()
            
            history = health_check.get_check_history()
            assert len(history) == 3
            
            # Each history entry should have required fields
            for entry in history:
                assert "timestamp" in entry
                assert "status" in entry
                assert "checks" in entry
    
    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, test_config):
        """Test health check exception handling."""
        health_check = HealthCheck(test_config)
        
        # Mock psutil to raise exceptions
        with patch('psutil.virtual_memory', side_effect=Exception("System error")):
            status = await health_check.check_health()
            
            assert status.status == "unhealthy"
            assert "error" in status.checks
    
    @pytest.mark.asyncio
    async def test_individual_check_exception_handling(self, test_config):
        """Test individual check exception handling."""
        health_check = HealthCheck(test_config)
        
        # Test memory check exception
        with patch('psutil.virtual_memory', side_effect=Exception("Memory error")):
            memory_result = await health_check._check_memory()
            assert memory_result["status"] == "unhealthy"
            assert "error" in memory_result
        
        # Test CPU check exception
        with patch('psutil.cpu_percent', side_effect=Exception("CPU error")):
            cpu_result = await health_check._check_cpu()
            assert cpu_result["status"] == "unhealthy"
            assert "error" in cpu_result
        
        # Test disk check exception
        with patch('psutil.disk_usage', side_effect=Exception("Disk error")):
            disk_result = await health_check._check_disk()
            assert disk_result["status"] == "unhealthy"
            assert "error" in disk_result


# Integration tests
class TestHealthCheckIntegration:
    """Integration tests for health check functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_health_check_cycle(self, test_config):
        """Test complete health check cycle."""
        health_check = HealthCheck(test_config)
        
        # Mock all system dependencies
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.Process') as mock_process, \
             patch('psutil.cpu_count') as mock_cpu_count:
            
            # Set up healthy system state
            mock_memory.return_value = MagicMock(percent=45.0, available=8000000000)
            mock_cpu.return_value = 20.0
            mock_disk.return_value = MagicMock(used=400000000, total=1000000000, free=600000000)
            mock_cpu_count.return_value = 8
            
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=50000000, vms=100000000)
            mock_process_instance.cpu_percent.return_value = 5.0
            mock_process.return_value = mock_process_instance
            
            # Perform health check
            status = await health_check.check_health()
            
            # Verify comprehensive status
            assert status.status == "healthy"
            assert status.service == test_config.service.name
            assert status.version == test_config.service.version
            assert isinstance(status.timestamp, datetime)
            
            # Verify all checks are present
            expected_checks = ["uptime", "memory", "cpu", "disk", "service_specific"]
            for check_name in expected_checks:
                assert check_name in status.checks
                assert status.checks[check_name]["status"] == "healthy"
            
            # Verify metrics
            assert "uptime" in status.metrics
            assert "request_count" in status.metrics
            assert "requests_per_second" in status.metrics
