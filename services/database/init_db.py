#!/usr/bin/env python3
"""
Database Initialization Script for Eunice Research Platform

This script creates the database schema and tables required by both
the database service and API Gateway. It ensures schema compatibility
across all services in the microservices architecture.

Tables Created:
- projects: Research projects
- research_topics: Topics within projects  
- research_plans: Plans for research topics
- tasks: Individual tasks within research plans (used by API Gateway)
- research_tasks: Alternative name for tasks table (used by database service)

The script is idempotent - it can be run multiple times safely.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Optional

import asyncpg
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/eunice")
DATABASE_HOST = os.getenv("DATABASE_HOST", "postgres")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "5432"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "eunice")
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")


async def wait_for_database(max_retries: int = 30, retry_delay: int = 2) -> bool:
    """
    Wait for database to become available.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between attempts in seconds
        
    Returns:
        True if database is available, False otherwise
    """
    logger.info(f"Waiting for database at {DATABASE_HOST}:{DATABASE_PORT}...")
    
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(
                host=DATABASE_HOST,
                port=DATABASE_PORT,
                user=DATABASE_USER,
                password=DATABASE_PASSWORD,
                database=DATABASE_NAME,
                timeout=5
            )
            await conn.close()
            logger.info(f"Database connection successful after {attempt + 1} attempts")
            return True
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                return False
    
    return False


async def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server (not to specific database)
        conn = psycopg2.connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            database="postgres"  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (DATABASE_NAME,)
            )
            
            if not cursor.fetchone():
                logger.info(f"Creating database '{DATABASE_NAME}'...")
                cursor.execute(f'CREATE DATABASE "{DATABASE_NAME}"')
                logger.info(f"Database '{DATABASE_NAME}' created successfully")
            else:
                logger.info(f"Database '{DATABASE_NAME}' already exists")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise


async def initialize_schema():
    """Initialize the database schema with all required tables."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        logger.info("Initializing database schema...")
        
        # Check if force reset is requested (useful for development)
        force_reset = os.getenv("FORCE_DB_RESET", "false").lower() == "true"
        
        if force_reset:
            logger.warning("FORCE_DB_RESET=true - Dropping and recreating all tables!")
            # Drop existing tables if they exist (for clean initialization)
            logger.info("Dropping existing tables...")
            await conn.execute("DROP TABLE IF EXISTS tasks CASCADE")
            await conn.execute("DROP TABLE IF EXISTS research_tasks CASCADE")
            await conn.execute("DROP TABLE IF EXISTS research_plans CASCADE")
            await conn.execute("DROP TABLE IF EXISTS research_topics CASCADE")
            await conn.execute("DROP TABLE IF EXISTS projects CASCADE")
            logger.info("Creating new database tables...")
        else:
            # Check if tables already exist to avoid data loss
            tables_exist = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'projects'
                )
            """)
            
            if tables_exist:
                logger.info("Database tables already exist - skipping initialization to preserve data")
                await conn.close()
                return
                
            logger.info("Creating new database tables...")
        
        # Create projects table
        logger.info("Creating projects table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create research_topics table
        logger.info("Creating research_topics table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS research_topics (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create research_plans table
        logger.info("Creating research_plans table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS research_plans (
                id VARCHAR(36) PRIMARY KEY,
                topic_id VARCHAR(36) REFERENCES research_topics(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                plan_type VARCHAR(50) DEFAULT 'comprehensive',
                status VARCHAR(50) DEFAULT 'draft',
                plan_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estimated_cost DECIMAL(10,2) DEFAULT 0.0,
                actual_cost DECIMAL(10,2) DEFAULT 0.0,
                metadata JSONB DEFAULT '{}',
                plan_structure JSONB DEFAULT '{}'
            )
        """)
        
        # Create tasks table (used by API Gateway)
        logger.info("Creating tasks table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(36) PRIMARY KEY,
                plan_id VARCHAR(36) REFERENCES research_plans(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                task_type VARCHAR(50) DEFAULT 'research',
                task_order INTEGER DEFAULT 1,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create research_tasks table (alias for tasks, used by database service)
        logger.info("Creating research_tasks table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS research_tasks (
                id VARCHAR(36) PRIMARY KEY,
                plan_id VARCHAR(36) REFERENCES research_plans(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                task_type VARCHAR(50) DEFAULT 'research',
                task_order INTEGER DEFAULT 1,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create literature_records table for bibliographic data
        logger.info("Creating literature_records table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS literature_records (
                id VARCHAR(36) PRIMARY KEY,
                title TEXT,
                authors JSONB DEFAULT '[]',
                project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE,
                doi VARCHAR(255),
                pmid VARCHAR(255),
                arxiv_id VARCHAR(255),
                year INTEGER,
                journal TEXT,
                abstract TEXT,
                url TEXT,
                citation_count INTEGER DEFAULT 0,
                source VARCHAR(50),
                publication_type VARCHAR(50),
                mesh_terms JSONB DEFAULT '[]',
                categories JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create search_term_optimizations table for AI-optimized search terms
        logger.info("Creating search_term_optimizations table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS search_term_optimizations (
                id VARCHAR(36) PRIMARY KEY,
                source_type VARCHAR(50) NOT NULL,  -- 'plan', 'task'
                source_id VARCHAR(36) NOT NULL,     -- plan_id or task_id
                original_query TEXT NOT NULL,
                optimized_terms JSONB NOT NULL,     -- Array of optimized search terms
                optimization_context JSONB DEFAULT '{}',  -- AI optimization metadata
                target_databases JSONB DEFAULT '[]',      -- Target databases for search
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,               -- Optional expiration for cached terms
                metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create indexes for better performance (only if they don't exist)
        logger.info("Creating database indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_research_topics_project_id ON research_topics(project_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_research_plans_topic_id ON research_plans(topic_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_plan_id ON tasks(plan_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_research_tasks_plan_id ON research_tasks(plan_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_literature_records_project_id ON literature_records(project_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_literature_records_doi ON literature_records(doi)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_literature_records_pmid ON literature_records(pmid)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_literature_records_source ON literature_records(source)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_term_optimizations_source ON search_term_optimizations(source_type, source_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_term_optimizations_created ON search_term_optimizations(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_research_topics_status ON research_topics(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_research_plans_status ON research_plans(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status)")
        
        # Create simplified sync triggers between tasks and research_tasks
        logger.info("Creating simplified sync triggers...")
        
        # Function to sync from tasks to research_tasks (one-way)
        await conn.execute("""
            CREATE OR REPLACE FUNCTION sync_tasks_to_research_tasks()
            RETURNS TRIGGER AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    INSERT INTO research_tasks (id, plan_id, name, description, task_type, task_order, status, created_at, updated_at, metadata)
                    VALUES (NEW.id, NEW.plan_id, NEW.name, NEW.description, NEW.task_type, NEW.task_order, NEW.status, NEW.created_at, NEW.updated_at, NEW.metadata)
                    ON CONFLICT (id) DO UPDATE SET
                        plan_id = NEW.plan_id,
                        name = NEW.name,
                        description = NEW.description,
                        task_type = NEW.task_type,
                        task_order = NEW.task_order,
                        status = NEW.status,
                        updated_at = NEW.updated_at,
                        metadata = NEW.metadata;
                    RETURN NEW;
                ELSIF TG_OP = 'UPDATE' THEN
                    UPDATE research_tasks SET
                        plan_id = NEW.plan_id,
                        name = NEW.name,
                        description = NEW.description,
                        task_type = NEW.task_type,
                        task_order = NEW.task_order,
                        status = NEW.status,
                        updated_at = NEW.updated_at,
                        metadata = NEW.metadata
                    WHERE id = NEW.id;
                    RETURN NEW;
                ELSIF TG_OP = 'DELETE' THEN
                    DELETE FROM research_tasks WHERE id = OLD.id;
                    RETURN OLD;
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create trigger only from tasks to research_tasks (to avoid circular reference)
        await conn.execute("""
            DROP TRIGGER IF EXISTS tasks_sync_trigger ON tasks;
            CREATE TRIGGER tasks_sync_trigger
                AFTER INSERT OR UPDATE OR DELETE ON tasks
                FOR EACH ROW EXECUTE FUNCTION sync_tasks_to_research_tasks();
        """)
        
        await conn.close()
        logger.info("Database schema initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise


async def create_sample_data():
    """Create sample data for testing purposes."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        logger.info("Creating sample data...")
        
        import uuid
        from datetime import datetime
        
        # Sample projects
        projects = [
            {
                "id": str(uuid.uuid4()),
                "name": "AI in Healthcare Research",
                "description": "Investigating applications of artificial intelligence in medical diagnosis and treatment",
                "status": "active",
                "metadata": {"priority": "high", "department": "medical_ai", "budget": 150000}
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Climate Change Impact Study", 
                "description": "Analyzing the effects of climate change on biodiversity in temperate forests",
                "status": "active",
                "metadata": {"priority": "medium", "department": "environmental", "budget": 85000}
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Neuroplasticity and Learning",
                "description": "Examining how brain plasticity affects learning capabilities across different age groups",
                "status": "active",
                "metadata": {"priority": "high", "department": "neuroscience", "budget": 120000}
            }
        ]
        
        # Insert sample projects
        # Insert sample projects
        now = datetime.utcnow()
        for project in projects:
            await conn.execute("""
                INSERT INTO projects (id, name, description, status, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, 
                project["id"],
                project["name"], 
                project["description"],
                project["status"],
                now,
                now,
                json.dumps(project["metadata"])  # Convert dict to JSON string
            )        # Sample research topics
        for project in projects:
            topic_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO research_topics (id, project_id, name, description, status, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                topic_id,
                project["id"],
                f"Research Topic for {project['name']}",
                f"Detailed investigation within {project['name']}",
                "active",
                now,
                now,
                json.dumps({})  # Convert dict to JSON string
            )
            
            # Sample research plan for each topic
            plan_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO research_plans (id, topic_id, name, description, plan_type, status, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                plan_id,
                topic_id,
                f"Research Plan for {project['name']}",
                f"Comprehensive research plan for {project['name']}",
                "comprehensive",
                "active", 
                now,
                now,
                json.dumps({})  # Convert dict to JSON string
            )
            
            # Sample tasks for each plan
            for i in range(3):
                task_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO tasks (id, plan_id, name, description, task_type, task_order, status, created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    task_id,
                    plan_id,
                    f"Task {i+1} for {project['name']}",
                    f"Detailed task {i+1} within research plan",
                    "research",
                    i + 1,
                    "pending",
                    now,
                    now,
                    json.dumps({})  # Convert dict to JSON string
                )
        
        await conn.close()
        logger.info("Sample data created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        raise


async def run_migrations():
    """Run database migrations to update existing schemas."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        logger.info("Running database migrations...")
        
        # Check if plan_structure column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='research_plans' AND column_name='plan_structure'
            )
        """)
        
        if not column_exists:
            logger.info("Adding plan_structure column to research_plans table...")
            await conn.execute("""
                ALTER TABLE research_plans 
                ADD COLUMN plan_structure JSONB DEFAULT NULL
            """)
            logger.info("Successfully added plan_structure column")
        else:
            logger.info("plan_structure column already exists")
        
        await conn.close()
        logger.info("Database migrations completed successfully!")
        
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


async def verify_schema():
    """Verify that all required tables exist and have the correct structure."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        logger.info("Verifying database schema...")
        
        # Check if all required tables exist
        required_tables = ['projects', 'research_topics', 'research_plans', 'tasks', 'research_tasks', 'literature_records', 'search_term_optimizations']
        
        for table in required_tables:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            """, table)
            
            if result:
                logger.info(f"✅ Table '{table}' exists")
            else:
                logger.error(f"❌ Table '{table}' is missing")
                raise Exception(f"Required table '{table}' is missing")
        
        # Verify foreign key relationships
        logger.info("Verifying foreign key relationships...")
        
        # Check that research_topics references projects
        fk_result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'research_topics'
                AND kcu.column_name = 'project_id'
            )
        """)
        
        if fk_result:
            logger.info("✅ Foreign key research_topics.project_id -> projects.id exists")
        else:
            logger.error("❌ Foreign key research_topics.project_id -> projects.id is missing")
        
        # Verify indexes exist
        logger.info("Verifying indexes...")
        indexes = await conn.fetch("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('projects', 'research_topics', 'research_plans', 'tasks', 'research_tasks')
            AND indexname LIKE 'idx_%'
        """)
        
        index_count = len(indexes)
        logger.info(f"✅ Found {index_count} custom indexes")
        
        # Test sample query on each table
        logger.info("Testing sample queries...")
        
        project_count = await conn.fetchval("SELECT COUNT(*) FROM projects")
        logger.info(f"✅ Projects table has {project_count} records")
        
        topic_count = await conn.fetchval("SELECT COUNT(*) FROM research_topics")
        logger.info(f"✅ Research topics table has {topic_count} records")
        
        plan_count = await conn.fetchval("SELECT COUNT(*) FROM research_plans")
        logger.info(f"✅ Research plans table has {plan_count} records")
        
        task_count = await conn.fetchval("SELECT COUNT(*) FROM tasks")
        logger.info(f"✅ Tasks table has {task_count} records")
        
        research_task_count = await conn.fetchval("SELECT COUNT(*) FROM research_tasks")
        logger.info(f"✅ Research tasks table has {research_task_count} records")
        
        literature_count = await conn.fetchval("SELECT COUNT(*) FROM literature_records")
        logger.info(f"✅ Literature records table has {literature_count} records")
        
        search_term_count = await conn.fetchval("SELECT COUNT(*) FROM search_term_optimizations")
        logger.info(f"✅ Search term optimizations table has {search_term_count} records")
        
        await conn.close()
        logger.info("Schema verification completed successfully!")
        
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        raise


async def main():
    """Main initialization function."""
    try:
        logger.info("Starting database initialization...")
        
        # Wait for database to be available
        if not await wait_for_database():
            logger.error("Database is not available. Exiting.")
            sys.exit(1)
        
        # Create database if it doesn't exist
        await create_database_if_not_exists()
        
        # Initialize schema
        await initialize_schema()
        
        # Run migrations
        await run_migrations()
        
        # Create sample data if requested and database is empty
        if os.getenv("CREATE_SAMPLE_DATA", "false").lower() == "true":
            conn = await asyncpg.connect(DATABASE_URL)
            project_count = await conn.fetchval("SELECT COUNT(*) FROM projects")
            await conn.close()
            
            if project_count == 0:
                logger.info("Creating sample data for empty database...")
                await create_sample_data()
            else:
                logger.info(f"Database already has {project_count} projects - skipping sample data creation")
        
        # Verify schema
        await verify_schema()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
