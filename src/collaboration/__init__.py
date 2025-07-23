"""
Collaboration Module for Eunice Systematic Review Platform

This module provides comprehensive collaboration features for systematic reviews including:
- Real-time collaboration engine with WebSocket support
- Advanced conflict detection and resolution
- Role-based access control and security
- Collaborative quality assurance workflows

Components:
- RealtimeCollaborationEngine: WebSocket-based real-time collaboration
- AdvancedConflictResolver: Intelligent conflict detection and resolution
- AccessControlManager: Role-based access control and security
- CollaborativeQAWorkflows: Quality assurance workflow management

Author: Eunice AI System
Date: 2024
"""

from .realtime_engine import (
    RealtimeCollaborationEngine,
    EventType,
    UserRole as CollabUserRole,
    CollaborationEvent,
    ActiveUser,
    ScreeningDecision,
    ProgressMetrics,
    create_collaboration_client,
    send_screening_decision
)

from .conflict_resolution import (
    AdvancedConflictResolver,
    ConflictType,
    ConflictSeverity,
    ResolutionStatus,
    ResolutionMethod,
    ConflictDetection,
    ResolutionSuggestion,
    ConflictResolution,
    ExpertAssignment
)

from .access_control import (
    AccessControlManager,
    UserRole,
    Permission,
    ResourceType,
    ActionType,
    User,
    Session,
    ProjectAccess,
    AuditLogEntry,
    require_permission
)

from .qa_workflows import (
    CollaborativeQAWorkflows,
    QAStage,
    ConsensusLevel,
    ValidationStatus,
    QAMetricType,
    QAWorkflow,
    QAAssignment,
    QASubmission,
    ConsensusMetrics,
    ExpertValidation,
    QAMetrics
)

__all__ = [
    # Real-time Collaboration
    'RealtimeCollaborationEngine',
    'EventType',
    'CollabUserRole',
    'CollaborationEvent',
    'ActiveUser',
    'ScreeningDecision',
    'ProgressMetrics',
    'create_collaboration_client',
    'send_screening_decision',
    
    # Conflict Resolution
    'AdvancedConflictResolver',
    'ConflictType',
    'ConflictSeverity',
    'ResolutionStatus',
    'ResolutionMethod',
    'ConflictDetection',
    'ResolutionSuggestion',
    'ConflictResolution',
    'ExpertAssignment',
    
    # Access Control
    'AccessControlManager',
    'UserRole',
    'Permission',
    'ResourceType',
    'ActionType',
    'User',
    'Session',
    'ProjectAccess',
    'AuditLogEntry',
    'require_permission',
    
    # QA Workflows
    'CollaborativeQAWorkflows',
    'QAStage',
    'ConsensusLevel',
    'ValidationStatus',
    'QAMetricType',
    'QAWorkflow',
    'QAAssignment',
    'QASubmission',
    'ConsensusMetrics',
    'ExpertValidation',
    'QAMetrics'
]

# Module version
__version__ = "1.0.0"

# Module metadata
__author__ = "Eunice AI System"
__description__ = "Comprehensive collaboration platform for systematic reviews"
