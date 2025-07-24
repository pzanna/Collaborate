"""
Collaboration Module for Eunice Systematic Review Platform

This module provides comprehensive collaboration features for systematic reviews including:
- Real - time collaboration engine with WebSocket support
- Advanced conflict detection and resolution
- Role - based access control and security
- Collaborative quality assurance workflows

Components:
- RealtimeCollaborationEngine: WebSocket - based real - time collaboration
- AdvancedConflictResolver: Intelligent conflict detection and resolution
- AccessControlManager: Role - based access control and security
- CollaborativeQAWorkflows: Quality assurance workflow management

Author: Eunice AI System
Date: 2024
"""

from .access_control import (
    AccessControlManager,
    ActionType,
    AuditLogEntry,
    Permission,
    ProjectAccess,
    ResourceType,
    Session,
    User,
    UserRole,
    require_permission,
)
from .conflict_resolution import (
    AdvancedConflictResolver,
    ConflictDetection,
    ConflictResolution,
    ConflictSeverity,
    ConflictType,
    ExpertAssignment,
    ResolutionMethod,
    ResolutionStatus,
    ResolutionSuggestion,
)
from .qa_workflows import (
    CollaborativeQAWorkflows,
    ConsensusLevel,
    ConsensusMetrics,
    ExpertValidation,
    QAAssignment,
    QAMetrics,
    QAMetricType,
    QAStage,
    QASubmission,
    QAWorkflow,
    ValidationStatus,
)
from .realtime_engine import (
    ActiveUser,
    CollaborationEvent,
    EventType,
    ProgressMetrics,
    RealtimeCollaborationEngine,
    ScreeningDecision,
)
from .realtime_engine import UserRole as CollabUserRole
from .realtime_engine import (
    create_collaboration_client,
    send_screening_decision,
)

__all__ = [
    # Real - time Collaboration
    "RealtimeCollaborationEngine",
    "EventType",
    "CollabUserRole",
    "CollaborationEvent",
    "ActiveUser",
    "ScreeningDecision",
    "ProgressMetrics",
    "create_collaboration_client",
    "send_screening_decision",
    # Conflict Resolution
    "AdvancedConflictResolver",
    "ConflictType",
    "ConflictSeverity",
    "ResolutionStatus",
    "ResolutionMethod",
    "ConflictDetection",
    "ResolutionSuggestion",
    "ConflictResolution",
    "ExpertAssignment",
    # Access Control
    "AccessControlManager",
    "UserRole",
    "Permission",
    "ResourceType",
    "ActionType",
    "User",
    "Session",
    "ProjectAccess",
    "AuditLogEntry",
    "require_permission",
    # QA Workflows
    "CollaborativeQAWorkflows",
    "QAStage",
    "ConsensusLevel",
    "ValidationStatus",
    "QAMetricType",
    "QAWorkflow",
    "QAAssignment",
    "QASubmission",
    "ConsensusMetrics",
    "ExpertValidation",
    "QAMetrics",
]

# Module version
__version__ = "1.0.0"

# Module metadata
__author__ = "Eunice AI System"
__description__ = "Comprehensive collaboration platform for systematic reviews"
