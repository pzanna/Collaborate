"""
Database schema extensions for systematic literature reviews.

This module provides database table definitions and operations
specifically for systematic review workflows following PRISMA guidelines.
"""

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

try:
    from ..utils.error_handler import handle_errors
    from ..utils.id_utils import generate_timestamped_id
except ImportError:
    # For testing or standalone use
    from utils.error_handler import handle_errors
    from utils.id_utils import generate_timestamped_id


class SystematicReviewDatabase:
    """Database operations for systematic literature reviews."""

    def __init__(self, db_path: str = "data / eunice.db"):
        """
        Initialize systematic review database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_tables()

    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @handle_errors(context="systematic_review_table_creation")
    def init_tables(self) -> None:
        """Initialize systematic review specific tables."""
        with self.get_connection() as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")

            # Study records table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_records (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,  -- JSON array of author names
                    year INTEGER,
                    doi TEXT,
                    source TEXT NOT NULL,
                    abstract TEXT,
                    full_text_path TEXT,
                    content_hash TEXT UNIQUE,
                    license_info TEXT,
                    metadata TEXT,  -- JSON metadata
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """
            )

            # Screening decisions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS screening_decisions (
                    id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    stage TEXT NOT NULL CHECK (stage IN ('title_abstract', 'full_text')),
                    decision TEXT NOT NULL CHECK (decision IN ('include', 'exclude', 'uncertain')),
                    reason_code TEXT,
                    actor TEXT NOT NULL CHECK (actor IN ('human', 'ai', 'human_required')),
                    confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
                    rationale TEXT,
                    model_id TEXT,
                    prompt_hash TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (record_id) REFERENCES study_records(id) ON DELETE CASCADE
                )
            """
            )

            # Quality / bias assessments table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bias_assessments (
                    id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    tool_id TEXT NOT NULL,  -- e.g., 'robins - i', 'rob2'
                    scores TEXT NOT NULL,   -- JSON object with scores
                    justification TEXT,
                    assessor TEXT NOT NULL,
                    model_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (record_id) REFERENCES study_records(id) ON DELETE CASCADE
                )
            """
            )

            # Evidence table entries
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_rows (
                    id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    effect_size REAL,
                    units TEXT,
                    direction TEXT CHECK (direction IN ('positive', 'negative', 'neutral', 'unclear')),
                    confidence TEXT CHECK (confidence IN ('weak', 'moderate', 'strong')),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (record_id) REFERENCES study_records(id) ON DELETE CASCADE
                )
            """
            )

            # PRISMA flow logs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prisma_logs (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    identified INTEGER DEFAULT 0,
                    duplicates_removed INTEGER DEFAULT 0,
                    screened_title_abstract INTEGER DEFAULT 0,
                    excluded_title_abstract INTEGER DEFAULT 0,
                    screened_full_text INTEGER DEFAULT 0,
                    excluded_full_text INTEGER DEFAULT 0,
                    included INTEGER DEFAULT 0,
                    exclusion_reasons TEXT,  -- JSON array of reason objects
                    search_strategy TEXT,    -- JSON object with search details
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """
            )

            # Study clusters table (for grouping related studies)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_clusters (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    cluster_type TEXT DEFAULT 'author_overlap',
                    primary_study_id TEXT NOT NULL,
                    related_study_ids TEXT,  -- JSON array of study IDs
                    cluster_metadata TEXT,   -- JSON metadata about cluster
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (primary_study_id) REFERENCES study_records(id) ON DELETE CASCADE
                )
            """
            )

            # Provenance events table (for audit trail)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provenance_events (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    stage TEXT,
                    payload TEXT NOT NULL,     -- JSON event data
                    actor TEXT,               -- human / ai / system
                    model_id TEXT,
                    prompt_hash TEXT,
                    content_hashes TEXT,      -- JSON array of content hashes
                    software_versions TEXT,   -- JSON object with version info
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """
            )

            # Create indexes for performance
            self._create_indexes(conn)

            conn.commit()

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_study_records_task_id ON study_records(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_study_records_content_hash ON study_records(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_study_records_doi ON study_records(doi)",
            "CREATE INDEX IF NOT EXISTS idx_screening_decisions_record_id ON screening_decisions(record_id)",
            "CREATE INDEX IF NOT EXISTS idx_screening_decisions_stage ON screening_decisions(stage)",
            "CREATE INDEX IF NOT EXISTS idx_bias_assessments_record_id ON bias_assessments(record_id)",
            "CREATE INDEX IF NOT EXISTS idx_evidence_rows_record_id ON evidence_rows(record_id)",
            "CREATE INDEX IF NOT EXISTS idx_prisma_logs_task_id ON prisma_logs(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_study_clusters_task_id ON study_clusters(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_provenance_events_task_id ON provenance_events(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_provenance_events_timestamp ON provenance_events(timestamp)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    @handle_errors(context="study_record_creation")
    def create_study_record(self, study_data: Dict[str, Any]) -> str:
        """
        Create a new study record.

        Args:
            study_data: Study information dictionary

        Returns:
            str: Created study record ID
        """
        study_id = study_data.get("id", generate_timestamped_id("study"))

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO study_records (
                    id, task_id, title, authors, year, doi, source,
                    abstract, full_text_path, content_hash, license_info, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    study_id,
                    study_data.get("task_id"),
                    study_data.get("title"),
                    json.dumps(study_data.get("authors", [])),
                    study_data.get("year"),
                    study_data.get("doi"),
                    study_data.get("source"),
                    study_data.get("abstract"),
                    study_data.get("full_text_path"),
                    study_data.get("content_hash"),
                    study_data.get("license_info"),
                    json.dumps(study_data.get("metadata", {})),
                ),
            )
            conn.commit()

        return study_id

    @handle_errors(context="screening_decision_creation")
    def create_screening_decision(self, decision_data: Dict[str, Any]) -> str:
        """
        Create a screening decision record.

        Args:
            decision_data: Screening decision information

        Returns:
            str: Created decision record ID
        """
        decision_id = generate_timestamped_id("decision")

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO screening_decisions (
                    id, record_id, stage, decision, reason_code, actor,
                    confidence_score, rationale, model_id, prompt_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    decision_id,
                    decision_data.get("record_id"),
                    decision_data.get("stage"),
                    decision_data.get("decision"),
                    decision_data.get("reason_code"),
                    decision_data.get("actor"),
                    decision_data.get("confidence_score"),
                    decision_data.get("rationale"),
                    decision_data.get("model_id"),
                    decision_data.get("prompt_hash"),
                ),
            )
            conn.commit()

        return decision_id

    @handle_errors(context="bias_assessment_creation")
    def create_bias_assessment(self, assessment_data: Dict[str, Any]) -> str:
        """
        Create a bias assessment record.

        Args:
            assessment_data: Bias assessment information

        Returns:
            str: Created assessment record ID
        """
        assessment_id = generate_timestamped_id("assessment")

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO bias_assessments (
                    id, record_id, tool_id, scores, justification, assessor, model_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    assessment_id,
                    assessment_data.get("record_id"),
                    assessment_data.get("tool_id"),
                    json.dumps(assessment_data.get("scores", {})),
                    assessment_data.get("justification"),
                    assessment_data.get("assessor"),
                    assessment_data.get("model_id"),
                ),
            )
            conn.commit()

        return assessment_id

    @handle_errors(context="evidence_row_creation")
    def create_evidence_row(self, evidence_data: Dict[str, Any]) -> str:
        """
        Create an evidence table row.

        Args:
            evidence_data: Evidence information

        Returns:
            str: Created evidence row ID
        """
        evidence_id = generate_timestamped_id("evidence")

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence_rows (
                    id, record_id, outcome, effect_size, units, direction, confidence, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    evidence_id,
                    evidence_data.get("record_id"),
                    evidence_data.get("outcome"),
                    evidence_data.get("effect_size"),
                    evidence_data.get("units"),
                    evidence_data.get("direction"),
                    evidence_data.get("confidence"),
                    evidence_data.get("notes"),
                ),
            )
            conn.commit()

        return evidence_id

    @handle_errors(context="prisma_log_update")
    def update_prisma_log(self, task_id: str, prisma_data: Dict[str, Any]) -> None:
        """
        Update PRISMA flow log for a task.

        Args:
            task_id: Task identifier
            prisma_data: PRISMA log data
        """
        with self.get_connection() as conn:
            # Check if log exists
            cursor = conn.execute(
                "SELECT id FROM prisma_logs WHERE task_id = ?", (task_id,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing log
                conn.execute(
                    """
                    UPDATE prisma_logs SET
                        stage = ?, identified = ?, duplicates_removed = ?,
                        screened_title_abstract = ?, excluded_title_abstract = ?,
                        screened_full_text = ?, excluded_full_text = ?,
                        included = ?, exclusion_reasons = ?, search_strategy = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """,
                    (
                        prisma_data.get("stage"),
                        prisma_data.get("identified", 0),
                        prisma_data.get("duplicates_removed", 0),
                        prisma_data.get("screened_title_abstract", 0),
                        prisma_data.get("excluded_title_abstract", 0),
                        prisma_data.get("screened_full_text", 0),
                        prisma_data.get("excluded_full_text", 0),
                        prisma_data.get("included", 0),
                        json.dumps(prisma_data.get("exclusion_reasons", [])),
                        json.dumps(prisma_data.get("search_strategy", {})),
                        task_id,
                    ),
                )
            else:
                # Create new log
                log_id = generate_timestamped_id("prisma")
                conn.execute(
                    """
                    INSERT INTO prisma_logs (
                        id, task_id, stage, identified, duplicates_removed,
                        screened_title_abstract, excluded_title_abstract,
                        screened_full_text, excluded_full_text, included,
                        exclusion_reasons, search_strategy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log_id,
                        task_id,
                        prisma_data.get("stage"),
                        prisma_data.get("identified", 0),
                        prisma_data.get("duplicates_removed", 0),
                        prisma_data.get("screened_title_abstract", 0),
                        prisma_data.get("excluded_title_abstract", 0),
                        prisma_data.get("screened_full_text", 0),
                        prisma_data.get("excluded_full_text", 0),
                        prisma_data.get("included", 0),
                        json.dumps(prisma_data.get("exclusion_reasons", [])),
                        json.dumps(prisma_data.get("search_strategy", {})),
                    ),
                )

            conn.commit()

    @handle_errors(context="study_cluster_creation")
    def create_study_cluster(self, cluster_data: Dict[str, Any]) -> str:
        """
        Create a study cluster record.

        Args:
            cluster_data: Cluster information

        Returns:
            str: Created cluster ID
        """
        cluster_id = cluster_data.get("cluster_id", generate_timestamped_id("cluster"))

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO study_clusters (
                    id, task_id, cluster_type, primary_study_id,
                    related_study_ids, cluster_metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    cluster_id,
                    cluster_data.get("task_id"),
                    cluster_data.get("cluster_type", "author_overlap"),
                    cluster_data.get("primary_study_id"),
                    json.dumps(cluster_data.get("related_study_ids", [])),
                    json.dumps(cluster_data.get("cluster_metadata", {})),
                ),
            )
            conn.commit()

        return cluster_id

    @handle_errors(context="provenance_event_creation")
    def create_provenance_event(self, event_data: Dict[str, Any]) -> str:
        """
        Create a provenance event record.

        Args:
            event_data: Provenance event information

        Returns:
            str: Created event ID
        """
        event_id = generate_timestamped_id("event")

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO provenance_events (
                    id, task_id, event_type, stage, payload, actor,
                    model_id, prompt_hash, content_hashes, software_versions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event_id,
                    event_data.get("task_id"),
                    event_data.get("event_type"),
                    event_data.get("stage"),
                    json.dumps(event_data.get("payload", {})),
                    event_data.get("actor"),
                    event_data.get("model_id"),
                    event_data.get("prompt_hash"),
                    json.dumps(event_data.get("content_hashes", [])),
                    json.dumps(event_data.get("software_versions", {})),
                ),
            )
            conn.commit()

        return event_id

    def get_studies_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all studies for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of study records
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM study_records WHERE task_id = ?
                ORDER BY created_at
            """,
                (task_id,),
            )

            studies = []
            for row in cursor.fetchall():
                study = dict(row)
                study["authors"] = (
                    json.loads(study["authors"]) if study["authors"] else []
                )
                study["metadata"] = (
                    json.loads(study["metadata"]) if study["metadata"] else {}
                )
                studies.append(study)

            return studies

    def get_prisma_log(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get PRISMA log for a task.

        Args:
            task_id: Task identifier

        Returns:
            PRISMA log data or None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM prisma_logs WHERE task_id = ?
                ORDER BY updated_at DESC LIMIT 1
            """,
                (task_id,),
            )

            row = cursor.fetchone()
            if row:
                log = dict(row)
                log["exclusion_reasons"] = (
                    json.loads(log["exclusion_reasons"])
                    if log["exclusion_reasons"]
                    else []
                )
                log["search_strategy"] = (
                    json.loads(log["search_strategy"]) if log["search_strategy"] else {}
                )
                return log

            return None

    def get_screening_decisions(self, record_id: str) -> List[Dict[str, Any]]:
        """
        Get screening decisions for a study record.

        Args:
            record_id: Study record identifier

        Returns:
            List of screening decisions
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM screening_decisions WHERE record_id = ?
                ORDER BY timestamp
            """,
                (record_id,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_task_statistics(self, task_id: str) -> Dict[str, Any]:
        """
        Get systematic review statistics for a task.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with statistics
        """
        with self.get_connection() as conn:
            # Get study counts
            cursor = conn.execute(
                """
                SELECT COUNT(*) as total_studies FROM study_records WHERE task_id = ?
            """,
                (task_id,),
            )
            total_studies = cursor.fetchone()["total_studies"]

            # Get screening counts
            cursor = conn.execute(
                """
                SELECT
                    stage,
                    decision,
                    COUNT(*) as count
                FROM screening_decisions sd
                JOIN study_records sr ON sd.record_id = sr.id
                WHERE sr.task_id = ?
                GROUP BY stage, decision
            """,
                (task_id,),
            )

            screening_stats = {}
            for row in cursor.fetchall():
                stage = row["stage"]
                decision = row["decision"]
                count = row["count"]

                if stage not in screening_stats:
                    screening_stats[stage] = {}
                screening_stats[stage][decision] = count

            # Get PRISMA log
            prisma_log = self.get_prisma_log(task_id)

            return {
                "total_studies": total_studies,
                "screening_statistics": screening_stats,
                "prisma_log": prisma_log,
            }


if __name__ == "__main__":
    # Test the database schema
    db = SystematicReviewDatabase(":memory:")

    # Test creating a study record
    study_data = {
        "task_id": "test_task_001",
        "title": "Test Study Title",
        "authors": ["Author One", "Author Two"],
        "year": 2023,
        "doi": "10.1000 / test.doi",
        "source": "pubmed",
        "abstract": "This is a test abstract.",
        "content_hash": "test_hash_123",
        "metadata": {"test": "data"},
    }

    study_id = db.create_study_record(study_data)
    print(f"Created study record: {study_id}")

    # Test creating a screening decision
    decision_data = {
        "record_id": study_id,
        "stage": "title_abstract",
        "decision": "include",
        "actor": "ai",
        "confidence_score": 0.85,
        "rationale": "Meets inclusion criteria",
    }

    decision_id = db.create_screening_decision(decision_data)
    print(f"Created screening decision: {decision_id}")

    # Test PRISMA log update
    prisma_data = {
        "stage": "title_abstract_screening",
        "identified": 100,
        "duplicates_removed": 15,
        "screened_title_abstract": 85,
        "excluded_title_abstract": 60,
        "exclusion_reasons": [
            {"code": "WRONG_POPULATION", "count": 30},
            {"code": "WRONG_INTERVENTION", "count": 20},
        ],
    }

    db.update_prisma_log("test_task_001", prisma_data)
    print("Updated PRISMA log")

    # Get statistics
    stats = db.get_task_statistics("test_task_001")
    print(f"Task statistics: {stats}")
