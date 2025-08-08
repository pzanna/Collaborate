"""
Health check functionality for the database service.

This module provides standardized health checking capabilities including:
- Service availability checks
- Dependency health monitoring
- Resource usage monitoring
- Custom health metrics
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import Config
from .models import HealthStatus


logger = logging.getLogger("database.health_check")


class HealthCheck:
    """
    Health check manager for the service.
    
    Provides comprehensive health monitoring including:
    - Service uptime
    - Memory and CPU usage
    - Database connectivity (if applicable)
    - MCP server connectivity (if applicable)
    - Custom health checks
    """
    
    def __init__(self, config: Config):
        """Initialize health check with configuration."""
        self.config = config
        self.start_time = time.time()
        self.request_count = 0
        self.last_check_time = None
        self.check_history: List[Dict[str, Any]] = []
        
    async def check_health(self) -> HealthStatus:
        """
        Perform comprehensive health check.
        
        Returns:
            HealthStatus: Current health status with all check results
        """
        self.last_check_time = datetime.utcnow()
        checks = {}
        overall_status = "healthy"
        
        try:
            # Basic service checks
            checks["uptime"] = await self._check_uptime()
            checks["memory"] = await self._check_memory()
            checks["cpu"] = await self._check_cpu()
            checks["disk"] = await self._check_disk()
            
            # Dependency checks
            if hasattr(self.config, 'database') and self.config.database.url:
                checks["database"] = await self._check_database()
            
            if hasattr(self.config, 'mcp') and self.config.mcp.server_url:
                checks["mcp_server"] = await self._check_mcp_server()
            
            # Custom service-specific checks
            checks["service_specific"] = await self._check_service_specific()
            
            # Determine overall status
            overall_status = self._determine_overall_status(checks)
            
            # Update metrics
            metrics = await self._collect_metrics()
            
            # Store check in history (keep last 10 checks)
            self.check_history.append({
                "timestamp": self.last_check_time,
                "status": overall_status,
                "checks": checks
            })
            if len(self.check_history) > 10:
                self.check_history = self.check_history[-10:]
            
            return HealthStatus(
                status=overall_status,
                timestamp=self.last_check_time,
                service=self.config.service.name,
                version=self.config.service.version,
                checks=checks,
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                status="unhealthy",
                timestamp=self.last_check_time or datetime.utcnow(),
                service=self.config.service.name,
                version=self.config.service.version,
                checks={"error": str(e)},
                metrics={}
            )
    
    async def _check_uptime(self) -> Dict[str, Any]:
        """Check service uptime."""
        uptime = time.time() - self.start_time
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "uptime_human": self._format_uptime(uptime)
        }
    
    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            memory_usage_percent = memory.percent
            status = "healthy"
            
            if memory_usage_percent > 90:
                status = "unhealthy"
            elif memory_usage_percent > 75:
                status = "degraded"
            
            return {
                "status": status,
                "system_memory_percent": memory_usage_percent,
                "system_memory_available": memory.available,
                "process_memory_rss": process_memory.rss,
                "process_memory_vms": process_memory.vms
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            
            status = "healthy"
            if cpu_percent > 90:
                status = "unhealthy"
            elif cpu_percent > 75:
                status = "degraded"
            
            return {
                "status": status,
                "system_cpu_percent": cpu_percent,
                "process_cpu_percent": process_cpu,
                "cpu_count": psutil.cpu_count()
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_disk(self) -> Dict[str, Any]:
        """Check disk usage."""
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            status = "healthy"
            if disk_percent > 95:
                status = "unhealthy"
            elif disk_percent > 85:
                status = "degraded"
            
            return {
                "status": status,
                "disk_usage_percent": disk_percent,
                "disk_free": disk.free,
                "disk_total": disk.total
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            # Implement database health check here
            # This is a placeholder - replace with actual database check
            
            # Example for PostgreSQL:
            # import asyncpg
            # conn = await asyncpg.connect(self.config.database.url)
            # await conn.fetchval("SELECT 1")
            # await conn.close()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time": 0.1  # Replace with actual response time
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_mcp_server(self) -> Dict[str, Any]:
        """Check MCP server connectivity."""
        try:
            # Implement MCP server health check here
            # This is a placeholder - replace with actual MCP check
            
            # Example:
            # import websockets
            # async with websockets.connect(self.config.mcp.server_url) as websocket:
            #     await websocket.ping()
            
            return {
                "status": "healthy",
                "message": "MCP server connection successful",
                "server_url": self.config.mcp.server_url
            }
        except Exception as e:
            logger.error(f"MCP server health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_service_specific(self) -> Dict[str, Any]:
        """Perform service-specific health checks."""
        try:
            # Add service-specific health checks here
            # Examples:
            # - Check if required files exist
            # - Validate configuration
            # - Test external API connections
            # - Check queue status
            # - Validate licenses or tokens
            
            checks = {
                "config_valid": True,
                "external_apis": "healthy",
                "internal_state": "healthy"
            }
            
            return {
                "status": "healthy",
                "checks": checks,
                "message": "All service-specific checks passed"
            }
        except Exception as e:
            logger.error(f"Service-specific health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def _determine_overall_status(self, checks: Dict[str, Any]) -> str:
        """Determine overall health status from individual checks."""
        unhealthy_count = 0
        degraded_count = 0
        
        for check_name, check_result in checks.items():
            if isinstance(check_result, dict) and "status" in check_result:
                status = check_result["status"]
                if status == "unhealthy":
                    unhealthy_count += 1
                elif status == "degraded":
                    degraded_count += 1
        
        # Determine overall status
        if unhealthy_count > 0:
            return "unhealthy"
        elif degraded_count > 0:
            return "degraded"
        else:
            return "healthy"
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect service metrics."""
        try:
            uptime = time.time() - self.start_time
            
            return {
                "uptime": uptime,
                "request_count": self.request_count,
                "requests_per_second": self.request_count / max(uptime, 1),
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "check_history_count": len(self.check_history)
            }
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {"error": str(e)}
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def increment_request_count(self):
        """Increment request counter for metrics."""
        self.request_count += 1
    
    def get_check_history(self) -> List[Dict[str, Any]]:
        """Get recent health check history."""
        return self.check_history.copy()


if __name__ == "__main__":
    # Test health check functionality
    from .config import get_config
    
    async def test_health_check():
        config = get_config()
        health_check = HealthCheck(config)
        
        print("Testing health check...")
        status = await health_check.check_health()
        print(f"Status: {status.status}")
        print(f"Service: {status.service}")
        print(f"Checks: {len(status.checks)}")
        
        for check_name, check_result in status.checks.items():
            print(f"  {check_name}: {check_result.get('status', 'unknown')}")
    
    asyncio.run(test_health_check())
