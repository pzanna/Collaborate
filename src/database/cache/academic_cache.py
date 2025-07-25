"""
Academic Search Cache for Literature Agent Integration

This module provides caching capabilities for academic search results,
integrating the Literature Agent with database connectors to provide
persistent storage and query optimization.

Author: Eunice AI System
Date: July 2025
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config.config_manager import ConfigManager


class AcademicCacheManager:
    """
    Manages persistent caching of academic search results.

    Provides caching for Literature Agent searches to reduce API calls
    and improve response times for repeated queries.
    """

    def __init__(
        self, config_manager: ConfigManager, cache_db_path: Optional[str] = None
    ):
        """
        Initialize the Academic Cache Manager.

        Args:
            config_manager: Configuration manager instance
            cache_db_path: Path to cache database file
        """
        self.config = config_manager
        self.cache_db_path = cache_db_path or self._get_default_cache_path()
        self.logger = logging.getLogger(__name__)

        # Cache settings
        self.default_cache_duration = timedelta(hours=24)
        self.max_cache_size_mb = 100

        # Initialize database
        self._init_cache_database()

    def _get_default_cache_path(self) -> str:
        """Get default cache database path."""
        # Place cache in project data directory
        cache_dir = Path(__file__).parent.parent.parent / "data"
        cache_dir.mkdir(exist_ok=True)
        return str(cache_dir / "academic_cache.db")

    def _init_cache_database(self) -> None:
        """Initialize SQLite cache database with proper schema."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()

                # Create search cache table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS search_cache (
                        cache_key TEXT PRIMARY KEY,
                        query_text TEXT NOT NULL,
                        search_type TEXT NOT NULL,
                        database_source TEXT,
                        results_json TEXT NOT NULL,
                        result_count INTEGER DEFAULT 0,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        hit_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create academic papers table for individual paper caching
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS academic_papers (
                        paper_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        authors_json TEXT,
                        abstract TEXT,
                        url TEXT,
                        doi TEXT,
                        pmid TEXT,
                        database_source TEXT NOT NULL,
                        publication_date TEXT,
                        citation_count INTEGER DEFAULT 0,
                        keywords_json TEXT,
                        metadata_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_search_cache_expires ON search_cache(expires_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_search_cache_type ON search_cache(search_type)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_papers_doi ON academic_papers(doi)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_papers_pmid ON academic_papers(pmid)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_papers_source ON academic_papers(database_source)"
                )

                conn.commit()
                self.logger.info(
                    f"Academic cache database initialized at {self.cache_db_path}"
                )

        except Exception as e:
            self.logger.error(f"Failed to initialize cache database: {e}")
            raise

    def _generate_cache_key(self, query: str, search_type: str, **kwargs) -> str:
        """
        Generate cache key for search query.

        Args:
            query: Search query text
            search_type: Type of search (semantic_scholar, pubmed, etc.)
            **kwargs: Additional parameters affecting search results

        Returns:
            str: SHA-256 hash as cache key
        """
        # Create consistent cache key from all parameters
        cache_data = {
            "query": query.strip().lower(),
            "search_type": search_type,
            **kwargs,
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()

    async def get_cached_results(
        self, query: str, search_type: str, **kwargs
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached search results if available and not expired.

        Args:
            query: Search query text
            search_type: Type of search
            **kwargs: Additional search parameters

        Returns:
            Optional[List[Dict[str, Any]]]: Cached results if available
        """
        cache_key = self._generate_cache_key(query, search_type, **kwargs)

        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()

                # Query cache with expiration check
                cursor.execute(
                    """
                    SELECT results_json, hit_count, cached_at
                    FROM search_cache
                    WHERE cache_key = ? AND expires_at > CURRENT_TIMESTAMP
                """,
                    (cache_key,),
                )

                result = cursor.fetchone()

                if result:
                    results_json, hit_count, cached_at = result

                    # Update hit count and last accessed
                    cursor.execute(
                        """
                        UPDATE search_cache
                        SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE cache_key = ?
                    """,
                        (cache_key,),
                    )
                    conn.commit()

                    # Parse and return results
                    results = json.loads(results_json)

                    self.logger.info(
                        f"Cache HIT for {search_type} query (hits: {hit_count + 1}): {query[:50]}..."
                    )

                    return results
                else:
                    self.logger.debug(
                        f"Cache MISS for {search_type} query: {query[:50]}..."
                    )
                    return None

        except Exception as e:
            self.logger.error(f"Cache retrieval error: {e}")
            return None

    async def cache_results(
        self,
        query: str,
        search_type: str,
        results: List[Dict[str, Any]],
        cache_duration: Optional[timedelta] = None,
        database_source: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Cache search results.

        Args:
            query: Search query text
            search_type: Type of search
            results: Results to cache
            cache_duration: How long to cache results
            database_source: Source database if applicable
            **kwargs: Additional search parameters
        """
        if not results:
            return  # Don't cache empty results

        cache_key = self._generate_cache_key(query, search_type, **kwargs)
        cache_duration = cache_duration or self.default_cache_duration
        expires_at = datetime.now(timezone.utc) + cache_duration

        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()

                # Insert or replace cache entry
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO search_cache
                    (cache_key, query_text, search_type, database_source, results_json,
                     result_count, expires_at, hit_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                """,
                    (
                        cache_key,
                        query,
                        search_type,
                        database_source,
                        json.dumps(results),
                        len(results),
                        expires_at.isoformat(),
                    ),
                )

                # Also cache individual papers for cross-referencing
                await self._cache_individual_papers(cursor, results, database_source)

                conn.commit()

                self.logger.info(
                    f"Cached {len(results)} results for {search_type} query: {query[:50]}..."
                )

        except Exception as e:
            self.logger.error(f"Cache storage error: {e}")

    async def _cache_individual_papers(
        self,
        cursor: sqlite3.Cursor,
        results: List[Dict[str, Any]],
        database_source: Optional[str],
    ) -> None:
        """Cache individual papers for cross-referencing."""
        for result in results:
            try:
                # Generate paper ID
                paper_id = result.get("metadata", {}).get("paper_id") or result.get(
                    "url", ""
                )
                if not paper_id:
                    continue

                # Extract paper data
                authors = result.get("metadata", {}).get("authors", [])
                keywords = result.get("metadata", {}).get("keywords", [])

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO academic_papers
                    (paper_id, title, authors_json, abstract, url, doi, pmid,
                     database_source, publication_date, citation_count,
                     keywords_json, metadata_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (
                        paper_id,
                        result.get("title", ""),
                        json.dumps(authors),
                        result.get("content", ""),  # Using content as abstract
                        result.get("url", ""),
                        result.get("metadata", {}).get("doi"),
                        result.get("metadata", {}).get("pmid"),
                        database_source or result.get("source", ""),
                        result.get("metadata", {}).get("publication_date"),
                        result.get("metadata", {}).get("citation_count", 0),
                        json.dumps(keywords),
                        json.dumps(result.get("metadata", {})),
                    ),
                )

            except Exception as e:
                self.logger.debug(f"Error caching individual paper: {e}")
                continue

    async def cleanup_expired_cache(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            int: Number of entries removed
        """
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()

                # Remove expired entries
                cursor.execute(
                    """
                    DELETE FROM search_cache
                    WHERE expires_at <= CURRENT_TIMESTAMP
                """
                )

                removed_count = cursor.rowcount
                conn.commit()

                if removed_count > 0:
                    self.logger.info(
                        f"Cleaned up {removed_count} expired cache entries"
                    )

                return removed_count

        except Exception as e:
            self.logger.error(f"Cache cleanup error: {e}")
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics
        """
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()

                # Get search cache stats
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_entries,
                        SUM(hit_count) as total_hits,
                        AVG(hit_count) as avg_hits_per_entry,
                        COUNT(CASE WHEN expires_at > CURRENT_TIMESTAMP THEN 1 END) as active_entries,
                        SUM(result_count) as total_cached_results
                    FROM search_cache
                """
                )

                cache_stats = cursor.fetchone()

                # Get paper cache stats
                cursor.execute("SELECT COUNT(*) FROM academic_papers")
                paper_count = cursor.fetchone()[0]

                # Get database file size
                cache_file = Path(self.cache_db_path)
                file_size_mb = (
                    cache_file.stat().st_size / (1024 * 1024)
                    if cache_file.exists()
                    else 0
                )

                return {
                    "total_cache_entries": cache_stats[0] or 0,
                    "total_cache_hits": cache_stats[1] or 0,
                    "average_hits_per_entry": round(cache_stats[2] or 0, 2),
                    "active_entries": cache_stats[3] or 0,
                    "total_cached_results": cache_stats[4] or 0,
                    "cached_papers": paper_count,
                    "cache_file_size_mb": round(file_size_mb, 2),
                    "cache_efficiency": round(
                        (cache_stats[1] or 0) / max(cache_stats[0] or 1, 1), 2
                    ),
                }

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}

    async def find_similar_papers(
        self, title: str, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find similar papers in cache based on title similarity.

        Args:
            title: Paper title to find similar papers for
            threshold: Similarity threshold (not implemented-placeholder)

        Returns:
            List[Dict[str, Any]]: Similar papers found in cache
        """
        # Simple implementation - would benefit from more sophisticated similarity matching
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.cursor()

                # Simple keyword-based matching (could be enhanced with proper similarity algorithms)
                set(title.lower().split())

                cursor.execute(
                    """
                    SELECT paper_id, title, authors_json, doi, pmid, database_source, metadata_json
                    FROM academic_papers
                    WHERE title LIKE ? OR title LIKE ?
                    LIMIT 10
                """,
                    (
                        f"%{title[:20]}%",
                        f"%{title.split()[0]}%" if title.split() else "",
                    ),
                )

                results = cursor.fetchall()

                similar_papers = []
                for result in results:
                    (
                        paper_id,
                        paper_title,
                        authors_json,
                        doi,
                        pmid,
                        db_source,
                        metadata_json,
                    ) = result

                    similar_papers.append(
                        {
                            "paper_id": paper_id,
                            "title": paper_title,
                            "authors": json.loads(authors_json) if authors_json else [],
                            "doi": doi,
                            "pmid": pmid,
                            "database_source": db_source,
                            "metadata": (
                                json.loads(metadata_json) if metadata_json else {}
                            ),
                        }
                    )

                return similar_papers

        except Exception as e:
            self.logger.error(f"Error finding similar papers: {e}")
            return []
