#!/usr/bin/env python3
"""
Pure Database Service for Eunice Research Platform

This service focuses solely on database management without API endpoints:
- Database schema initialization and management
- Connection health monitoring
- Database maintenance operations

The API Gateway handles all REST API operations using direct database connections.
This follows the single responsibility principle and microservices best practices.
"""

import asyncio
import logging
import os
import sys
import signal
from datetime import datetime
from typing import Any, Dict, Optional

import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import watchfiles with fallback
try:
    from watchfiles import awatch
    WATCHFILES_AVAILABLE = True
except ImportError as e:
    awatch = None  # type: ignore
    WATCHFILES_AVAILABLE = False



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/database-service.log') if os.getenv('LOG_LEVEL') == 'DEBUG' else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
MAINTENANCE_INTERVAL = int(os.getenv("MAINTENANCE_INTERVAL", "3600"))  # 1 hour


class DatabaseService:
    """
    Pure database service focused on database management and health monitoring.
    Does not expose REST API endpoints - that's handled by the API Gateway.
    """
    
    def __init__(self):
        self.db_url = DATABASE_URL
        self.engine: Optional[Any] = None
        self.running = False
        
    async def initialize(self):
        """Initialize database connections and verify schema."""
        try:
            logger.info("Initializing Database Service...")
            
            # Test database connection
            conn = await asyncpg.connect(self.db_url)
            await conn.close()
            logger.info("✅ Database connection established")
            
            # Create SQLAlchemy engine for maintenance operations
            self.engine = create_engine(self.db_url)
            
            # Verify database schema exists
            await self.verify_schema()
            
            logger.info("✅ Database Service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database Service initialization failed: {e}")
            raise
    
    async def verify_schema(self):
        """Verify that all required tables exist."""
        try:
            conn = await asyncpg.connect(self.db_url)
            
            required_tables = ['projects', 'research_topics', 'research_plans', 'tasks', 'research_tasks']
            
            for table in required_tables:
                result = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table)
                
                if result:
                    logger.info(f"✅ Table '{table}' verified")
                else:
                    logger.error(f"❌ Table '{table}' is missing!")
                    raise Exception(f"Required table '{table}' is missing")
            
            await conn.close()
            logger.info("✅ Database schema verification completed")
            
        except Exception as e:
            logger.error(f"❌ Schema verification failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health = {
            "service": "database-service",
            "status": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {
                "database": "unknown"
            },
            "metrics": {}
        }
        
        try:
            # Check PostgreSQL
            conn = await asyncpg.connect(self.db_url)
            
            # Test basic query
            await conn.fetchval("SELECT 1")
            
            # Get connection stats
            pool_stats = await conn.fetchrow("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            
            health["dependencies"]["database"] = "healthy"
            health["metrics"]["database"] = dict(pool_stats) if pool_stats else {}
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health["dependencies"]["database"] = "unhealthy"
            health["metrics"]["database"] = {"error": str(e)}
        
        # Overall status - only require database to be healthy
        database_healthy = health["dependencies"]["database"] == "healthy"
        health["status"] = "healthy" if database_healthy else "unhealthy"
        
        return health
    
    async def maintenance_tasks(self):
        """Perform routine database maintenance."""
        try:
            logger.info("🔧 Running database maintenance tasks...")
            
            if self.engine:
                with self.engine.connect() as conn:
                    # Update table statistics
                    conn.execute(text("ANALYZE"))
                    logger.info("✅ Database statistics updated")
                    
                    # Clean up old data (if needed)
                    # This is where you'd add cleanup logic for old logs, temp data, etc.
                    
                    conn.commit()
            else:
                raise Exception("Database engine not initialized")
            
            logger.info("✅ Database maintenance completed")
            
        except Exception as e:
            logger.error(f"❌ Database maintenance failed: {e}")
    
    async def run_health_monitor(self):
        """Background task for continuous health monitoring."""
        while self.running:
            try:
                health = await self.health_check()
                
                # Log health status
                status = health["status"]
                if status == "healthy":
                    logger.debug(f"🟢 Health check passed - {health['timestamp']}")
                else:
                    logger.warning(f"🟡 Health check failed - {health}")
                
            except Exception as e:
                logger.error(f"❌ Health monitor error: {e}")
            
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
    
    async def run_maintenance_scheduler(self):
        """Background task for scheduled maintenance."""
        while self.running:
            try:
                await asyncio.sleep(MAINTENANCE_INTERVAL)
                await self.maintenance_tasks()
                
            except Exception as e:
                logger.error(f"❌ Maintenance scheduler error: {e}")
    
    async def start(self):
        """Start the database service."""
        try:
            await self.initialize()
            
            self.running = True
            logger.info("🚀 Database Service started")
            
            # Start background tasks
            health_task = asyncio.create_task(self.run_health_monitor())
            maintenance_task = asyncio.create_task(self.run_maintenance_scheduler())
            
            # Wait for shutdown signal
            await self.wait_for_shutdown()
            
            # Cleanup
            self.running = False
            health_task.cancel()
            maintenance_task.cancel()
            
            await asyncio.gather(health_task, maintenance_task, return_exceptions=True)
            
            logger.info("✅ Database Service stopped gracefully")
            
        except Exception as e:
            logger.error(f"❌ Database Service error: {e}")
            raise
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        shutdown_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            shutdown_event.set()
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        await shutdown_event.wait()


async def main():
    """Main entry point for the database service."""
    service = DatabaseService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Database service stopped by user")
    except Exception as e:
        logger.error(f"Failed to start database service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())