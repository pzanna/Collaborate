"""
Database Optimization Module
===========================

Database performance optimization for systematic review automation.

This module provides:
- Query optimization and analysis
- Connection pooling
- Index management
- Database performance monitoring

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Query performance statistics"""

    query: str
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime
    table_scans: int = 0
    index_usage: List[str] = field(default_factory=list)


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""

    total_queries: int = 0
    average_query_time_ms: float = 0.0
    slow_queries: int = 0
    connection_pool_size: int = 0
    active_connections: int = 0
    cache_hit_ratio: float = 0.0


class ConnectionPool:
    """Simple database connection pool"""

    def __init__(self, database_path: str, max_connections: int = 10):
        """
        Initialize connection pool

        Args:
            database_path: Path to SQLite database
            max_connections: Maximum number of connections
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self._pool = []
        self._used_connections = set()
        self._lock = threading.Lock()
        self.metrics = DatabaseMetrics()

        # Initialize pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize connection pool"""
        for _ in range(self.max_connections):
            conn = sqlite3.connect(
                self.database_path, check_same_thread=False, timeout=30.0
            )
            conn.row_factory = sqlite3.Row
            self._pool.append(conn)

        self.metrics.connection_pool_size = len(self._pool)
        logger.info(
            f"Database connection pool initialized with {len(self._pool)} connections"
        )

    @contextmanager
    def get_connection(self):
        """Get connection from pool (context manager)"""
        conn = None
        try:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                    self._used_connections.add(conn)
                    self.metrics.active_connections = len(self._used_connections)
                else:
                    # Create temporary connection if pool exhausted
                    conn = sqlite3.connect(
                        self.database_path, check_same_thread=False, timeout=30.0
                    )
                    conn.row_factory = sqlite3.Row
                    logger.warning(
                        "Connection pool exhausted, creating temporary connection"
                    )

            yield conn

        finally:
            if conn:
                with self._lock:
                    if conn in self._used_connections:
                        self._used_connections.remove(conn)
                        self._pool.append(conn)
                        self.metrics.active_connections = len(self._used_connections)
                    else:
                        # Close temporary connection
                        conn.close()

    def close_all(self):
        """Close all connections in pool"""
        with self._lock:
            for conn in self._pool + list(self._used_connections):
                conn.close()
            self._pool.clear()
            self._used_connections.clear()
            self.metrics.connection_pool_size = 0
            self.metrics.active_connections = 0


class QueryOptimizer:
    """Query optimization and analysis"""

    def __init__(self, connection_pool: ConnectionPool):
        """
        Initialize query optimizer

        Args:
            connection_pool: Database connection pool
        """
        self.connection_pool = connection_pool
        self.query_stats: List[QueryStats] = []
        self.slow_query_threshold_ms = 1000.0  # 1 second

    async def execute_query(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute optimized query with performance tracking

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query results
        """
        start_time = time.time()

        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Execute query
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Fetch results
                results = [dict(row) for row in cursor.fetchall()]

                # Calculate metrics
                execution_time_ms = (time.time() - start_time) * 1000
                rows_affected = len(results)

                # Record statistics
                stats = QueryStats(
                    query=query,
                    execution_time_ms=execution_time_ms,
                    rows_affected=rows_affected,
                    timestamp=datetime.now(timezone.utc),
                )

                self.query_stats.append(stats)

                # Update metrics
                metrics = self.connection_pool.metrics
                metrics.total_queries += 1
                metrics.average_query_time_ms = (
                    metrics.average_query_time_ms + execution_time_ms
                ) / 2

                if execution_time_ms > self.slow_query_threshold_ms:
                    metrics.slow_queries += 1
                    logger.warning(
                        f"Slow query detected: {execution_time_ms:.2f}ms - {query[:100]}..."
                    )

                return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query performance characteristics

        Args:
            query: SQL query to analyze

        Returns:
            Query analysis results
        """
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Get query plan
                cursor.execute(f"EXPLAIN QUERY PLAN {query}")
                query_plan = cursor.fetchall()

                # Analyze plan
                analysis = {
                    "query": query,
                    "plan": [dict(row) for row in query_plan],
                    "has_table_scan": any("SCAN" in str(row) for row in query_plan),
                    "uses_index": any("INDEX" in str(row) for row in query_plan),
                    "complexity_score": len(query_plan),
                }

                # Add recommendations
                recommendations = []
                if analysis["has_table_scan"]:
                    recommendations.append(
                        "Consider adding indexes to avoid table scans"
                    )

                if not analysis["uses_index"] and "WHERE" in query.upper():
                    recommendations.append("Add indexes on WHERE clause columns")

                if analysis["complexity_score"] > 5:
                    recommendations.append("Consider simplifying complex query")

                analysis["recommendations"] = recommendations

                return analysis

        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {"error": str(e)}

    def get_slow_queries(self, limit: int = 10) -> List[QueryStats]:
        """Get slowest queries"""
        sorted_queries = sorted(
            self.query_stats, key=lambda q: q.execution_time_ms, reverse=True
        )
        return sorted_queries[:limit]

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        if not self.query_stats:
            return {}

        execution_times = [q.execution_time_ms for q in self.query_stats]

        return {
            "total_queries": len(self.query_stats),
            "average_time_ms": sum(execution_times) / len(execution_times),
            "min_time_ms": min(execution_times),
            "max_time_ms": max(execution_times),
            "slow_queries": len(
                [
                    q
                    for q in self.query_stats
                    if q.execution_time_ms > self.slow_query_threshold_ms
                ]
            ),
            "recent_queries": len(
                [
                    q
                    for q in self.query_stats
                    if (datetime.now(timezone.utc) - q.timestamp).seconds < 300
                ]
            ),
        }


class IndexManager:
    """Database index management"""

    def __init__(self, connection_pool: ConnectionPool):
        """
        Initialize index manager

        Args:
            connection_pool: Database connection pool
        """
        self.connection_pool = connection_pool

    async def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze index usage and effectiveness"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Get all indexes
                cursor.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
                )
                indexes = cursor.fetchall()

                analysis = {
                    "total_indexes": len(indexes),
                    "indexes": [],
                    "recommendations": [],
                }

                for index in indexes:
                    index_info = {
                        "name": index["name"],
                        "sql": index["sql"],
                        "estimated_size": "unknown",  # SQLite doesn't provide easy size info
                    }
                    analysis["indexes"].append(index_info)

                # Add general recommendations
                if len(indexes) == 0:
                    analysis["recommendations"].append(
                        "No indexes found - consider adding indexes on frequently queried columns"
                    )
                elif len(indexes) > 20:
                    analysis["recommendations"].append(
                        "Large number of indexes - review for unused indexes"
                    )

                return analysis

        except Exception as e:
            logger.error(f"Index analysis failed: {e}")
            return {"error": str(e)}

    async def suggest_indexes(self, table_name: str, columns: List[str]) -> List[str]:
        """
        Suggest indexes for table columns

        Args:
            table_name: Target table name
            columns: Columns to consider for indexing

        Returns:
            List of suggested index creation statements
        """
        suggestions = []

        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Check existing indexes
                cursor.execute(f"PRAGMA index_list({table_name})")
                existing_indexes = cursor.fetchall()
                existing_columns = set()

                for index in existing_indexes:
                    cursor.execute(f"PRAGMA index_info({index['name']})")
                    index_columns = cursor.fetchall()
                    for col in index_columns:
                        existing_columns.add(col["name"])

                # Suggest new indexes
                for column in columns:
                    if column not in existing_columns:
                        index_name = f"idx_{table_name}_{column}"
                        index_sql = (
                            f"CREATE INDEX {index_name} ON {table_name} ({column})"
                        )
                        suggestions.append(index_sql)

                # Suggest composite indexes for common combinations
                if len(columns) >= 2:
                    common_combinations = [
                        ("title", "year"),
                        ("author", "year"),
                        ("status", "created_at"),
                    ]

                    for combo in common_combinations:
                        if all(col in columns for col in combo):
                            index_name = f"idx_{table_name}_{'_'.join(combo)}"
                            index_sql = f"CREATE INDEX {index_name} ON {table_name} ({', '.join(combo)})"
                            suggestions.append(index_sql)

                return suggestions

        except Exception as e:
            logger.error(f"Index suggestion failed: {e}")
            return []

    async def create_index(self, index_sql: str) -> bool:
        """
        Create database index

        Args:
            index_sql: Index creation SQL statement

        Returns:
            True if successful
        """
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(index_sql)
                conn.commit()
                logger.info(f"Index created successfully: {index_sql}")
                return True

        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return False


class DatabaseOptimizer:
    """
    Main database optimization coordinator
    """

    def __init__(self, database_path: str, max_connections: int = 10):
        """
        Initialize database optimizer

        Args:
            database_path: Path to database file
            max_connections: Maximum connections in pool
        """
        self.database_path = database_path
        self.connection_pool = ConnectionPool(database_path, max_connections)
        self.query_optimizer = QueryOptimizer(self.connection_pool)
        self.index_manager = IndexManager(self.connection_pool)

        logger.info(f"Database optimizer initialized for {database_path}")

    async def optimize_database(self) -> Dict[str, Any]:
        """
        Run comprehensive database optimization

        Returns:
            Optimization results and recommendations
        """
        optimization_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_path": self.database_path,
            "optimizations_applied": [],
            "recommendations": [],
            "performance_metrics": {},
        }

        try:
            # Analyze current state
            logger.info("Analyzing database performance...")

            # Get query statistics
            query_stats = self.query_optimizer.get_query_statistics()
            optimization_results["performance_metrics"]["queries"] = query_stats

            # Analyze indexes
            index_analysis = await self.index_manager.analyze_index_usage()
            optimization_results["performance_metrics"]["indexes"] = index_analysis

            # Get connection pool metrics
            pool_metrics = {
                "pool_size": self.connection_pool.metrics.connection_pool_size,
                "active_connections": self.connection_pool.metrics.active_connections,
                "total_queries": self.connection_pool.metrics.total_queries,
                "average_query_time_ms": self.connection_pool.metrics.average_query_time_ms,
                "slow_queries": self.connection_pool.metrics.slow_queries,
            }
            optimization_results["performance_metrics"][
                "connection_pool"
            ] = pool_metrics

            # Run VACUUM to reclaim space
            await self._vacuum_database()
            optimization_results["optimizations_applied"].append(
                "VACUUM - database defragmentation"
            )

            # Update statistics
            await self._update_statistics()
            optimization_results["optimizations_applied"].append(
                "Updated table statistics"
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(
                query_stats, index_analysis
            )
            optimization_results["recommendations"] = recommendations

            logger.info("Database optimization completed")
            return optimization_results

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            optimization_results["error"] = str(e)
            return optimization_results

    async def _vacuum_database(self):
        """Run VACUUM to optimize database file"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("VACUUM")
                logger.info("Database VACUUM completed")
        except Exception as e:
            logger.error(f"VACUUM failed: {e}")

    async def _update_statistics(self):
        """Update database statistics"""
        try:
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("ANALYZE")
                logger.info("Database statistics updated")
        except Exception as e:
            logger.error(f"Statistics update failed: {e}")

    def _generate_recommendations(
        self, query_stats: Dict[str, Any], index_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []

        # Query - based recommendations
        if query_stats.get("slow_queries", 0) > 0:
            recommendations.append(
                f"Optimize {query_stats['slow_queries']} slow queries"
            )

        if query_stats.get("average_time_ms", 0) > 100:
            recommendations.append(
                "Consider adding indexes to improve average query time"
            )

        # Index - based recommendations
        if index_analysis.get("total_indexes", 0) == 0:
            recommendations.append("Add indexes on frequently queried columns")

        # Connection pool recommendations
        if (
            self.connection_pool.metrics.active_connections
            == self.connection_pool.max_connections
        ):
            recommendations.append("Consider increasing connection pool size")

        # General recommendations
        recommendations.append("Run VACUUM regularly to maintain optimal file size")
        recommendations.append("Monitor query performance and add indexes as needed")

        return recommendations

    async def execute_optimized_query(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute query with optimization"""
        return await self.query_optimizer.execute_query(query, params)

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        return {
            "connection_pool": {
                "pool_size": self.connection_pool.metrics.connection_pool_size,
                "active_connections": self.connection_pool.metrics.active_connections,
                "utilization": (
                    (
                        self.connection_pool.metrics.active_connections
                        / self.connection_pool.metrics.connection_pool_size
                    )
                    if self.connection_pool.metrics.connection_pool_size > 0
                    else 0
                ),
            },
            "query_performance": self.query_optimizer.get_query_statistics(),
            "slow_queries": [
                {
                    "query": q.query[:100] + "..." if len(q.query) > 100 else q.query,
                    "time_ms": q.execution_time_ms,
                    "timestamp": q.timestamp.isoformat(),
                }
                for q in self.query_optimizer.get_slow_queries(5)
            ],
        }

    def close(self):
        """Close database optimizer and clean up resources"""
        self.connection_pool.close_all()
        logger.info("Database optimizer closed")


# Example usage and testing functions
async def demo_database_optimizer():
    """Demonstrate database optimization capabilities"""
    print("🗄️  Database Optimizer Demo")
    print("=" * 35)

    # Initialize optimizer
    db_path = ":memory:"  # Use in - memory database for demo
    optimizer = DatabaseOptimizer(db_path, max_connections=5)

    # Create sample table and data
    print("📝 Setting up sample database...")
    await optimizer.execute_optimized_query(
        """
        CREATE TABLE studies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT,
            year INTEGER,
            abstract TEXT,
            status TEXT DEFAULT 'pending'
        )
    """
    )

    # Insert sample data
    for i in range(100):
        await optimizer.execute_optimized_query(
            "INSERT INTO studies (title, author, year, abstract, status) VALUES (?, ?, ?, ?, ?)",
            (
                f"Study {i}",
                f"Author {i % 10}",
                2020 + (i % 5),
                f"Abstract for study {i}",
                "completed" if i % 3 == 0 else "pending",
            ),
        )

    print("   Created table with 100 sample studies")

    # Run some queries to generate statistics
    print("\n📊 Running sample queries...")

    await optimizer.execute_optimized_query("SELECT * FROM studies WHERE year = 2023")
    await optimizer.execute_optimized_query(
        "SELECT * FROM studies WHERE author LIKE 'Author 5%'"
    )
    await optimizer.execute_optimized_query(
        "SELECT COUNT(*) FROM studies GROUP BY status"
    )

    # Analyze query performance
    query_stats = optimizer.query_optimizer.get_query_statistics()
    print(f"   Executed {query_stats.get('total_queries', 0)} queries")
    print(f"   Average query time: {query_stats.get('average_time_ms', 0):.2f}ms")

    # Run optimization
    print("\n🚀 Running database optimization...")
    optimization_results = await optimizer.optimize_database()

    print("   Optimizations applied:")
    for opt in optimization_results["optimizations_applied"]:
        print(f"     • {opt}")

    print("   Recommendations:")
    for rec in optimization_results["recommendations"][:3]:
        print(f"     • {rec}")

    # Generate performance report
    report = optimizer.get_performance_report()
    print("\n📋 Performance Report:")
    print(
        f"   Connection pool utilization: {report['connection_pool']['utilization']:.1%}"
    )
    print(
        f"   Total queries executed: {report['query_performance'].get('total_queries', 0)}"
    )
    print(
        f"   Average query time: {report['query_performance'].get('average_time_ms', 0):.2f}ms"
    )

    # Cleanup
    optimizer.close()

    return optimizer


if __name__ == "__main__":
    asyncio.run(demo_database_optimizer())
