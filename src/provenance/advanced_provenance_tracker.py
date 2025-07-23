"""
Advanced Provenance Tracking System for Systematic Reviews - Phase 3 Implementation.

This module provides comprehensive provenance tracking for systematic review workflows,
enabling reproducibility, audit trails, and quality assurance.
"""

import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid


class ProvenanceType(Enum):
    """Types of provenance events."""
    SEARCH_EXECUTION = "search_execution"
    STUDY_IMPORT = "study_import"
    DEDUPLICATION = "deduplication"
    SCREENING_DECISION = "screening_decision"
    QUALITY_ASSESSMENT = "quality_assessment"
    DATA_EXTRACTION = "data_extraction"
    EVIDENCE_SYNTHESIS = "evidence_synthesis"
    REPORT_GENERATION = "report_generation"
    CONFIGURATION_CHANGE = "configuration_change"
    AGENT_EXECUTION = "agent_execution"
    ERROR_OCCURRENCE = "error_occurrence"
    USER_ACTION = "user_action"


class EventStatus(Enum):
    """Status of provenance events."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass
class ProvenanceAgent:
    """Agent information for provenance tracking."""
    agent_id: str
    agent_type: str
    agent_version: str
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceEntity:
    """Entity information for provenance tracking."""
    entity_id: str
    entity_type: str
    entity_name: str
    entity_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceActivity:
    """Activity information for provenance tracking."""
    activity_id: str
    activity_type: ProvenanceType
    activity_name: str
    status: EventStatus
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceRelation:
    """Relationship between provenance entities."""
    relation_id: str
    relation_type: str
    source_entity: str
    target_entity: str
    activity_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceRecord:
    """Complete provenance record."""
    record_id: str
    review_id: str
    timestamp: str
    activity: ProvenanceActivity
    agent: Optional[ProvenanceAgent] = None
    entities: List[ProvenanceEntity] = field(default_factory=list)
    relations: List[ProvenanceRelation] = field(default_factory=list)
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Calculate checksum after initialization."""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of the record."""
        record_data = {
            'record_id': self.record_id,
            'review_id': self.review_id,
            'timestamp': self.timestamp,
            'activity': self.activity.to_dict(),
            'agent': self.agent.to_dict() if self.agent else None,
            'entities': [e.to_dict() for e in self.entities],
            'relations': [r.to_dict() for r in self.relations]
        }
        
        record_json = json.dumps(record_data, sort_keys=True, default=str)
        return hashlib.sha256(record_json.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def verify_integrity(self) -> bool:
        """Verify record integrity using checksum."""
        calculated_checksum = self._calculate_checksum()
        return calculated_checksum == self.checksum


@dataclass
class ProvenanceQuery:
    """Query parameters for provenance retrieval."""
    review_id: Optional[str] = None
    activity_types: Optional[List[ProvenanceType]] = None
    agent_types: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status_filter: Optional[List[EventStatus]] = None
    entity_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class AdvancedProvenanceTracker:
    """
    Advanced provenance tracking system for systematic review workflows.
    
    Provides comprehensive tracking of all activities, entities, and relationships
    in systematic review processes to ensure reproducibility and audit capabilities.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, database: Any, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provenance tracker.
        
        Args:
            database: Database connection for provenance storage
            config: Configuration options for provenance tracking
        """
        self.database = database
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration options
        self.enable_checksums = self.config.get('enable_checksums', True)
        self.auto_compress = self.config.get('auto_compress', False)
        self.retention_days = self.config.get('retention_days', 365)
        self.detailed_tracking = self.config.get('detailed_tracking', True)
        
        # Active tracking context
        self.active_activities: Dict[str, ProvenanceActivity] = {}
    
    def start_activity(
        self, 
        review_id: str, 
        activity_type: ProvenanceType,
        activity_name: str,
        agent: Optional[ProvenanceAgent] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a new activity.
        
        Args:
            review_id: Systematic review identifier
            activity_type: Type of activity being tracked
            activity_name: Human-readable activity name
            agent: Agent performing the activity
            parameters: Activity parameters
            
        Returns:
            Activity ID for tracking
        """
        activity_id = str(uuid.uuid4())
        
        activity = ProvenanceActivity(
            activity_id=activity_id,
            activity_type=activity_type,
            activity_name=activity_name,
            status=EventStatus.INITIATED,
            start_time=datetime.now().isoformat(),
            parameters=parameters or {}
        )
        
        # Store active activity
        self.active_activities[activity_id] = activity
        
        # Create initial provenance record
        record = ProvenanceRecord(
            record_id=str(uuid.uuid4()),
            review_id=review_id,
            timestamp=datetime.now().isoformat(),
            activity=activity,
            agent=agent
        )
        
        self._store_provenance_record(record)
        
        self.logger.info(f"Started activity {activity_id}: {activity_name}")
        return activity_id
    
    def update_activity_status(
        self, 
        activity_id: str, 
        status: EventStatus,
        outputs: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update activity status and record progress.
        
        Args:
            activity_id: Activity identifier
            status: New activity status
            outputs: Activity outputs or results
            error_details: Error information if status is FAILED
        """
        if activity_id not in self.active_activities:
            self.logger.warning(f"Activity {activity_id} not found in active activities")
            return
        
        activity = self.active_activities[activity_id]
        activity.status = status
        
        if outputs:
            activity.outputs.update(outputs)
        
        if error_details:
            activity.error_details = error_details
        
        if status in [EventStatus.COMPLETED, EventStatus.FAILED, EventStatus.CANCELLED]:
            activity.end_time = datetime.now().isoformat()
            
            # Calculate duration
            if activity.start_time and activity.end_time:
                start = datetime.fromisoformat(activity.start_time)
                end = datetime.fromisoformat(activity.end_time)
                activity.duration_seconds = (end - start).total_seconds()
            
            # Remove from active activities
            del self.active_activities[activity_id]
        
        self.logger.info(f"Updated activity {activity_id} status to {status.value}")
    
    def record_entity(
        self, 
        review_id: str,
        activity_id: str,
        entity_type: str,
        entity_name: str,
        entity_id: Optional[str] = None,
        entity_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an entity involved in an activity.
        
        Args:
            review_id: Systematic review identifier
            activity_id: Associated activity identifier
            entity_type: Type of entity (study, database, file, etc.)
            entity_name: Human-readable entity name
            entity_id: Unique entity identifier
            entity_version: Entity version
            metadata: Additional entity metadata
            
        Returns:
            Entity identifier
        """
        if not entity_id:
            entity_id = str(uuid.uuid4())
        
        entity = ProvenanceEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            entity_version=entity_version,
            metadata=metadata or {}
        )
        
        # Create provenance record for entity
        if activity_id in self.active_activities:
            activity = self.active_activities[activity_id]
        else:
            # Create minimal activity record
            activity = ProvenanceActivity(
                activity_id=activity_id,
                activity_type=ProvenanceType.USER_ACTION,
                activity_name="Entity recording",
                status=EventStatus.COMPLETED,
                start_time=datetime.now().isoformat()
            )
        
        record = ProvenanceRecord(
            record_id=str(uuid.uuid4()),
            review_id=review_id,
            timestamp=datetime.now().isoformat(),
            activity=activity,
            entities=[entity]
        )
        
        self._store_provenance_record(record)
        
        self.logger.info(f"Recorded entity {entity_id}: {entity_name}")
        return entity_id
    
    def record_relation(
        self,
        review_id: str,
        activity_id: str,
        relation_type: str,
        source_entity: str,
        target_entity: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a relationship between entities.
        
        Args:
            review_id: Systematic review identifier
            activity_id: Associated activity identifier
            relation_type: Type of relationship
            source_entity: Source entity identifier
            target_entity: Target entity identifier
            properties: Relationship properties
            
        Returns:
            Relation identifier
        """
        relation_id = str(uuid.uuid4())
        
        relation = ProvenanceRelation(
            relation_id=relation_id,
            relation_type=relation_type,
            source_entity=source_entity,
            target_entity=target_entity,
            activity_id=activity_id,
            properties=properties or {}
        )
        
        # Create provenance record for relation
        if activity_id in self.active_activities:
            activity = self.active_activities[activity_id]
        else:
            activity = ProvenanceActivity(
                activity_id=activity_id,
                activity_type=ProvenanceType.USER_ACTION,
                activity_name="Relation recording",
                status=EventStatus.COMPLETED,
                start_time=datetime.now().isoformat()
            )
        
        record = ProvenanceRecord(
            record_id=str(uuid.uuid4()),
            review_id=review_id,
            timestamp=datetime.now().isoformat(),
            activity=activity,
            relations=[relation]
        )
        
        self._store_provenance_record(record)
        
        self.logger.info(f"Recorded relation {relation_id}: {relation_type}")
        return relation_id
    
    def track_search_execution(
        self,
        review_id: str,
        database_name: str,
        search_terms: str,
        search_strategy: Dict[str, Any],
        results_count: int,
        agent: Optional[ProvenanceAgent] = None
    ) -> str:
        """
        Track search execution with detailed provenance.
        
        Args:
            review_id: Systematic review identifier
            database_name: Database being searched
            search_terms: Search terms used
            search_strategy: Complete search strategy
            results_count: Number of results returned
            agent: Agent performing the search
            
        Returns:
            Activity identifier
        """
        activity_id = self.start_activity(
            review_id=review_id,
            activity_type=ProvenanceType.SEARCH_EXECUTION,
            activity_name=f"Search execution on {database_name}",
            agent=agent,
            parameters={
                'database': database_name,
                'search_terms': search_terms,
                'search_strategy': search_strategy
            }
        )
        
        # Record database entity
        database_entity_id = self.record_entity(
            review_id=review_id,
            activity_id=activity_id,
            entity_type="database",
            entity_name=database_name,
            metadata={'search_date': datetime.now().isoformat()}
        )
        
        # Record search results entity
        results_entity_id = self.record_entity(
            review_id=review_id,
            activity_id=activity_id,
            entity_type="search_results",
            entity_name=f"Search results from {database_name}",
            metadata={
                'results_count': results_count,
                'search_terms': search_terms
            }
        )
        
        # Record relation between database and results
        self.record_relation(
            review_id=review_id,
            activity_id=activity_id,
            relation_type="generated_by",
            source_entity=results_entity_id,
            target_entity=database_entity_id,
            properties={'search_execution_time': datetime.now().isoformat()}
        )
        
        # Complete activity
        self.update_activity_status(
            activity_id=activity_id,
            status=EventStatus.COMPLETED,
            outputs={'results_count': results_count, 'results_entity_id': results_entity_id}
        )
        
        return activity_id
    
    def track_screening_decision(
        self,
        review_id: str,
        study_id: str,
        decision: str,
        reviewer_id: str,
        screening_stage: str,
        criteria_used: List[str],
        confidence_score: Optional[float] = None,
        agent: Optional[ProvenanceAgent] = None
    ) -> str:
        """
        Track screening decisions with detailed provenance.
        
        Args:
            review_id: Systematic review identifier
            study_id: Study being screened
            decision: Screening decision (include/exclude)
            reviewer_id: Reviewer making decision
            screening_stage: Stage of screening (title_abstract/full_text)
            criteria_used: Criteria applied in decision
            confidence_score: Decision confidence score
            agent: Agent making the decision
            
        Returns:
            Activity identifier
        """
        activity_id = self.start_activity(
            review_id=review_id,
            activity_type=ProvenanceType.SCREENING_DECISION,
            activity_name=f"Screening decision for study {study_id}",
            agent=agent,
            parameters={
                'study_id': study_id,
                'screening_stage': screening_stage,
                'criteria_used': criteria_used,
                'reviewer_id': reviewer_id
            }
        )
        
        # Record study entity
        study_entity_id = self.record_entity(
            review_id=review_id,
            activity_id=activity_id,
            entity_type="study",
            entity_name=f"Study {study_id}",
            entity_id=study_id
        )
        
        # Record decision entity
        decision_entity_id = self.record_entity(
            review_id=review_id,
            activity_id=activity_id,
            entity_type="screening_decision",
            entity_name=f"Screening decision for {study_id}",
            metadata={
                'decision': decision,
                'screening_stage': screening_stage,
                'confidence_score': confidence_score,
                'reviewer_id': reviewer_id,
                'criteria_used': criteria_used
            }
        )
        
        # Record relation
        self.record_relation(
            review_id=review_id,
            activity_id=activity_id,
            relation_type="decision_about",
            source_entity=decision_entity_id,
            target_entity=study_entity_id,
            properties={
                'decision': decision,
                'stage': screening_stage
            }
        )
        
        # Complete activity
        self.update_activity_status(
            activity_id=activity_id,
            status=EventStatus.COMPLETED,
            outputs={
                'decision': decision,
                'decision_entity_id': decision_entity_id,
                'confidence_score': confidence_score
            }
        )
        
        return activity_id
    
    def track_evidence_synthesis(
        self,
        review_id: str,
        synthesis_type: str,
        included_studies: List[str],
        synthesis_parameters: Dict[str, Any],
        synthesis_results: Dict[str, Any],
        agent: Optional[ProvenanceAgent] = None
    ) -> str:
        """
        Track evidence synthesis with comprehensive provenance.
        
        Args:
            review_id: Systematic review identifier
            synthesis_type: Type of synthesis (meta-analysis, narrative, etc.)
            included_studies: Studies included in synthesis
            synthesis_parameters: Parameters used for synthesis
            synthesis_results: Results of synthesis
            agent: Agent performing synthesis
            
        Returns:
            Activity identifier
        """
        activity_id = self.start_activity(
            review_id=review_id,
            activity_type=ProvenanceType.EVIDENCE_SYNTHESIS,
            activity_name=f"{synthesis_type} evidence synthesis",
            agent=agent,
            parameters={
                'synthesis_type': synthesis_type,
                'included_studies': included_studies,
                'synthesis_parameters': synthesis_parameters
            }
        )
        
        # Record synthesis entity
        synthesis_entity_id = self.record_entity(
            review_id=review_id,
            activity_id=activity_id,
            entity_type="evidence_synthesis",
            entity_name=f"{synthesis_type} synthesis results",
            metadata={
                'synthesis_type': synthesis_type,
                'study_count': len(included_studies),
                'synthesis_results': synthesis_results
            }
        )
        
        # Record relations to included studies
        for study_id in included_studies:
            self.record_relation(
                review_id=review_id,
                activity_id=activity_id,
                relation_type="synthesized_from",
                source_entity=synthesis_entity_id,
                target_entity=study_id,
                properties={'synthesis_type': synthesis_type}
            )
        
        # Complete activity
        self.update_activity_status(
            activity_id=activity_id,
            status=EventStatus.COMPLETED,
            outputs={
                'synthesis_entity_id': synthesis_entity_id,
                'synthesis_results': synthesis_results
            }
        )
        
        return activity_id
    
    def query_provenance(self, query: ProvenanceQuery) -> List[ProvenanceRecord]:
        """
        Query provenance records based on criteria.
        
        Args:
            query: Query parameters
            
        Returns:
            List of matching provenance records
        """
        self.logger.info(f"Querying provenance with parameters: {query.to_dict()}")
        
        try:
            # For demonstration, return mock records
            # In production, this would query the database
            records = self._mock_query_results(query)
            
            # Verify integrity of records
            if self.enable_checksums:
                verified_records = []
                for record in records:
                    if record.verify_integrity():
                        verified_records.append(record)
                    else:
                        self.logger.warning(f"Integrity check failed for record {record.record_id}")
                
                return verified_records
            
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to query provenance: {e}")
            return []
    
    def generate_provenance_report(
        self, 
        review_id: str,
        include_detailed: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive provenance report for a review.
        
        Args:
            review_id: Systematic review identifier
            include_detailed: Include detailed activity information
            
        Returns:
            Provenance report
        """
        self.logger.info(f"Generating provenance report for review {review_id}")
        
        query = ProvenanceQuery(review_id=review_id)
        records = self.query_provenance(query)
        
        # Analyze provenance data
        activities_by_type = {}
        entities_by_type = {}
        relations_by_type = {}
        timeline = []
        
        for record in records:
            # Group activities
            activity_type = record.activity.activity_type.value
            if activity_type not in activities_by_type:
                activities_by_type[activity_type] = []
            activities_by_type[activity_type].append(record.activity)
            
            # Group entities
            for entity in record.entities:
                entity_type = entity.entity_type
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)
            
            # Group relations
            for relation in record.relations:
                relation_type = relation.relation_type
                if relation_type not in relations_by_type:
                    relations_by_type[relation_type] = []
                relations_by_type[relation_type].append(relation)
            
            # Build timeline
            timeline.append({
                'timestamp': record.timestamp,
                'activity_type': activity_type,
                'activity_name': record.activity.activity_name,
                'status': record.activity.status.value
            })
        
        # Sort timeline
        timeline.sort(key=lambda x: x['timestamp'])
        
        report = {
            'review_id': review_id,
            'report_generated': datetime.now().isoformat(),
            'total_records': len(records),
            'summary': {
                'activities_by_type': {k: len(v) for k, v in activities_by_type.items()},
                'entities_by_type': {k: len(v) for k, v in entities_by_type.items()},
                'relations_by_type': {k: len(v) for k, v in relations_by_type.items()}
            },
            'timeline': timeline
        }
        
        if include_detailed:
            report['detailed'] = {
                'activities': {k: [a.to_dict() for a in v] for k, v in activities_by_type.items()},
                'entities': {k: [e.to_dict() for e in v] for k, v in entities_by_type.items()},
                'relations': {k: [r.to_dict() for r in v] for k, v in relations_by_type.items()}
            }
        
        return report
    
    def export_provenance_graph(
        self, 
        review_id: str, 
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export provenance as a graph structure.
        
        Args:
            review_id: Systematic review identifier
            output_format: Export format (json, graphml, dot)
            
        Returns:
            Graph representation of provenance
        """
        query = ProvenanceQuery(review_id=review_id)
        records = self.query_provenance(query)
        
        nodes = []
        edges = []
        
        # Create nodes for activities and entities
        for record in records:
            # Activity node
            activity_node = {
                'id': record.activity.activity_id,
                'type': 'activity',
                'label': record.activity.activity_name,
                'activity_type': record.activity.activity_type.value,
                'status': record.activity.status.value,
                'timestamp': record.timestamp
            }
            nodes.append(activity_node)
            
            # Entity nodes
            for entity in record.entities:
                entity_node = {
                    'id': entity.entity_id,
                    'type': 'entity',
                    'label': entity.entity_name,
                    'entity_type': entity.entity_type
                }
                nodes.append(entity_node)
                
                # Edge from activity to entity
                edge = {
                    'source': record.activity.activity_id,
                    'target': entity.entity_id,
                    'type': 'used'
                }
                edges.append(edge)
            
            # Relation edges
            for relation in record.relations:
                edge = {
                    'source': relation.source_entity,
                    'target': relation.target_entity,
                    'type': relation.relation_type,
                    'activity_id': relation.activity_id
                }
                edges.append(edge)
        
        # Remove duplicate nodes
        unique_nodes = {node['id']: node for node in nodes}.values()
        
        graph = {
            'review_id': review_id,
            'export_timestamp': datetime.now().isoformat(),
            'nodes': list(unique_nodes),
            'edges': edges,
            'format': output_format
        }
        
        return graph
    
    def _store_provenance_record(self, record: ProvenanceRecord) -> None:
        """Store provenance record in database."""
        
        try:
            record_data = record.to_dict()
            
            # Use the existing database pattern
            if hasattr(self.database, 'create_provenance_record'):
                self.database.create_provenance_record(record_data)
            else:
                # Log that storage is not implemented
                self.logger.info(f"Provenance storage not implemented. Record: {record.record_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store provenance record: {e}")
            # Don't raise exception to allow tracking to continue
    
    def _mock_query_results(self, query: ProvenanceQuery) -> List[ProvenanceRecord]:
        """Generate mock query results for demonstration."""
        
        # Create sample provenance records
        records = []
        
        # Search execution record
        search_activity = ProvenanceActivity(
            activity_id="activity_search_001",
            activity_type=ProvenanceType.SEARCH_EXECUTION,
            activity_name="PubMed search execution",
            status=EventStatus.COMPLETED,
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T10:05:00",
            duration_seconds=300.0,
            parameters={'database': 'PubMed', 'search_terms': 'AI diagnosis'},
            outputs={'results_count': 847}
        )
        
        search_agent = ProvenanceAgent(
            agent_id="agent_literature_001",
            agent_type="LiteratureAgent",
            agent_version="2.1.0",
            configuration={'max_results': 1000}
        )
        
        pubmed_entity = ProvenanceEntity(
            entity_id="entity_pubmed_001",
            entity_type="database",
            entity_name="PubMed",
            metadata={'search_date': '2024-01-15'}
        )
        
        search_record = ProvenanceRecord(
            record_id="record_001",
            review_id=query.review_id or "review_001",
            timestamp="2024-01-15T10:00:00",
            activity=search_activity,
            agent=search_agent,
            entities=[pubmed_entity]
        )
        
        records.append(search_record)
        
        # Screening decision record
        screening_activity = ProvenanceActivity(
            activity_id="activity_screening_001",
            activity_type=ProvenanceType.SCREENING_DECISION,
            activity_name="Title/abstract screening",
            status=EventStatus.COMPLETED,
            start_time="2024-01-16T09:00:00",
            end_time="2024-01-16T09:30:00",
            duration_seconds=1800.0,
            parameters={'screening_stage': 'title_abstract', 'reviewer_id': 'reviewer_001'},
            outputs={'decision': 'include', 'confidence_score': 0.85}
        )
        
        study_entity = ProvenanceEntity(
            entity_id="entity_study_001",
            entity_type="study",
            entity_name="AI Diagnosis Study 001",
            metadata={'title': 'AI-Assisted Diagnosis in Emergency Medicine'}
        )
        
        screening_record = ProvenanceRecord(
            record_id="record_002",
            review_id=query.review_id or "review_001",
            timestamp="2024-01-16T09:00:00",
            activity=screening_activity,
            entities=[study_entity]
        )
        
        records.append(screening_record)
        
        return records


# Integration function for Phase 3 testing
async def demonstrate_provenance_tracking():
    """Demonstrate advanced provenance tracking capabilities."""
    
    print("🔍 Phase 3: Advanced Provenance Tracking Demonstration")
    print("=" * 60)
    
    # Mock database for demonstration
    class MockDatabase:
        def create_provenance_record(self, data):
            print(f"📊 Provenance record stored: {data['record_id']} ({data['activity']['activity_type']})")
    
    # Initialize provenance tracker
    db = MockDatabase()
    config = {
        'enable_checksums': True,
        'detailed_tracking': True,
        'retention_days': 365
    }
    tracker = AdvancedProvenanceTracker(db, config)
    
    review_id = "systematic_review_001"
    
    print(f"📝 Tracking systematic review workflow: {review_id}")
    
    # 1. Track search execution
    print(f"\n🔍 1. Tracking search execution...")
    search_agent = ProvenanceAgent(
        agent_id="agent_literature_001",
        agent_type="LiteratureAgent",
        agent_version="2.1.0",
        configuration={'max_results': 1000, 'timeout': 300}
    )
    
    search_activity_id = tracker.track_search_execution(
        review_id=review_id,
        database_name="PubMed",
        search_terms="artificial intelligence AND diagnosis",
        search_strategy={
            'boolean_operators': ['AND', 'OR'],
            'field_restrictions': ['title', 'abstract'],
            'date_range': '2015-2024'
        },
        results_count=847,
        agent=search_agent
    )
    print(f"   ✅ Search activity tracked: {search_activity_id}")
    
    # 2. Track screening decisions
    print(f"\n📋 2. Tracking screening decisions...")
    screening_agent = ProvenanceAgent(
        agent_id="agent_screening_001",
        agent_type="ScreeningAgent",
        agent_version="1.5.0"
    )
    
    screening_decisions = [
        {'study_id': 'study_001', 'decision': 'include', 'confidence': 0.92},
        {'study_id': 'study_002', 'decision': 'exclude', 'confidence': 0.78},
        {'study_id': 'study_003', 'decision': 'include', 'confidence': 0.85}
    ]
    
    screening_activity_ids = []
    for decision_data in screening_decisions:
        activity_id = tracker.track_screening_decision(
            review_id=review_id,
            study_id=decision_data['study_id'],
            decision=decision_data['decision'],
            reviewer_id="reviewer_001",
            screening_stage="title_abstract",
            criteria_used=['population', 'intervention', 'outcomes'],
            confidence_score=decision_data['confidence'],
            agent=screening_agent
        )
        screening_activity_ids.append(activity_id)
        print(f"   ✅ Screening decision tracked: {activity_id} ({decision_data['decision']})")
    
    # 3. Track evidence synthesis
    print(f"\n📊 3. Tracking evidence synthesis...")
    synthesis_agent = ProvenanceAgent(
        agent_id="agent_synthesis_001",
        agent_type="EvidenceSynthesisEngine",
        agent_version="1.0.0"
    )
    
    synthesis_activity_id = tracker.track_evidence_synthesis(
        review_id=review_id,
        synthesis_type="meta_analysis",
        included_studies=['study_001', 'study_003'],
        synthesis_parameters={
            'effect_measure': 'odds_ratio',
            'random_effects': True,
            'heterogeneity_threshold': 0.5
        },
        synthesis_results={
            'pooled_or': 2.34,
            'ci_lower': 1.87,
            'ci_upper': 2.92,
            'p_value': 0.001,
            'i2': 45.6
        },
        agent=synthesis_agent
    )
    print(f"   ✅ Evidence synthesis tracked: {synthesis_activity_id}")
    
    # 4. Query provenance
    print(f"\n🔍 4. Querying provenance records...")
    query = ProvenanceQuery(
        review_id=review_id,
        activity_types=[ProvenanceType.SEARCH_EXECUTION, ProvenanceType.SCREENING_DECISION]
    )
    
    provenance_records = tracker.query_provenance(query)
    print(f"   📊 Retrieved {len(provenance_records)} provenance records")
    
    for record in provenance_records:
        print(f"     - {record.activity.activity_name} ({record.activity.status.value})")
        print(f"       Entities: {len(record.entities)}, Relations: {len(record.relations)}")
        if record.verify_integrity():
            print(f"       ✅ Integrity verified")
        else:
            print(f"       ❌ Integrity check failed")
    
    # 5. Generate provenance report
    print(f"\n📈 5. Generating provenance report...")
    provenance_report = tracker.generate_provenance_report(review_id, include_detailed=False)
    
    print(f"   📋 Provenance Report Summary:")
    print(f"     Total records: {provenance_report['total_records']}")
    print(f"     Activities by type:")
    for activity_type, count in provenance_report['summary']['activities_by_type'].items():
        print(f"       {activity_type}: {count}")
    
    print(f"     Entities by type:")
    for entity_type, count in provenance_report['summary']['entities_by_type'].items():
        print(f"       {entity_type}: {count}")
    
    print(f"     Timeline events: {len(provenance_report['timeline'])}")
    
    # 6. Export provenance graph
    print(f"\n🌐 6. Exporting provenance graph...")
    provenance_graph = tracker.export_provenance_graph(review_id)
    
    print(f"   📊 Provenance Graph:")
    print(f"     Nodes: {len(provenance_graph['nodes'])}")
    print(f"     Edges: {len(provenance_graph['edges'])}")
    print(f"     Node types: {set(node['type'] for node in provenance_graph['nodes'])}")
    print(f"     Edge types: {set(edge['type'] for edge in provenance_graph['edges'])}")
    
    # 7. Display active activities
    print(f"\n⚡ 7. Active activities monitor:")
    if tracker.active_activities:
        for activity_id, activity in tracker.active_activities.items():
            print(f"     {activity_id}: {activity.activity_name} ({activity.status.value})")
    else:
        print(f"     No active activities")
    
    print(f"\n✅ Phase 3 Advanced Provenance Tracking demonstration completed!")
    print(f"   Review ID: {review_id}")
    print(f"   Total activities tracked: {len(screening_activity_ids) + 2}")  # +2 for search and synthesis
    print(f"   Provenance records: {len(provenance_records)}")
    
    return tracker, provenance_report, provenance_graph


if __name__ == "__main__":
    import asyncio
    asyncio.run(demonstrate_provenance_tracking())
