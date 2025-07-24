"""
Real - time Collaboration Engine for Eunice Systematic Review Platform

This module provides WebSocket - based real - time collaboration features including:
- Live multi - user screening workflows
- Real - time evidence table editing
- Live progress tracking across teams
- Collaborative annotation and chat systems

Key Features:
- WebSocket connection management for multiple users
- Real - time synchronization of screening decisions
- Live progress updates and notifications
- Collaborative editing with conflict resolution
- Real - time chat and annotation system

Author: Eunice AI System
Date: 2024
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of real - time collaboration events"""

    SCREENING_UPDATE = "screening_update"
    EVIDENCE_EDIT = "evidence_edit"
    PROGRESS_UPDATE = "progress_update"
    CHAT_MESSAGE = "chat_message"
    ANNOTATION_ADD = "annotation_add"
    ANNOTATION_UPDATE = "annotation_update"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    CONFLICT_DETECTED = "conflict_detected"
    CONSENSUS_ACHIEVED = "consensus_achieved"


class UserRole(Enum):
    """User roles for collaboration"""

    LEAD_REVIEWER = "lead_reviewer"
    REVIEWER = "reviewer"
    EXPERT_REVIEWER = "expert_reviewer"
    OBSERVER = "observer"
    ADMIN = "admin"


@dataclass
class CollaborationEvent:
    """Real - time collaboration event structure"""

    event_id: str
    event_type: EventType
    user_id: str
    project_id: str
    timestamp: datetime
    data: Dict[str, Any]
    room_id: Optional[str] = None


@dataclass
class ActiveUser:
    """Active user in collaboration session"""

    user_id: str
    username: str
    role: UserRole
    project_id: str
    websocket: Any  # WebSocket connection
    last_activity: datetime
    current_screen: Optional[str] = None


@dataclass
class ScreeningDecision:
    """Screening decision with metadata"""

    decision_id: str
    study_id: str
    user_id: str
    decision: str  # 'include', 'exclude', 'uncertain'
    criteria: List[str]
    notes: Optional[str]
    timestamp: datetime
    confidence_score: float


@dataclass
class ProgressMetrics:
    """Real - time progress tracking metrics"""

    project_id: str
    total_studies: int
    screened_studies: int
    included_studies: int
    excluded_studies: int
    uncertain_studies: int
    active_reviewers: int
    screening_rate: float  # studies per hour
    estimated_completion: datetime
    conflicts_pending: int


class RealtimeCollaborationEngine:
    """
    Core engine for real - time collaboration in systematic reviews

    Features:
    - WebSocket connection management
    - Real - time event broadcasting
    - User session management
    - Live progress tracking
    - Collaborative screening workflows
    """

    def __init__(self, db_path: str = "data / eunice.db", port: int = 8765):
        self.db_path = db_path
        self.port = port
        self.active_users: Dict[str, ActiveUser] = {}
        self.project_rooms: Dict[str, Set[str]] = {}  # project_id -> set of user_ids
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.server = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Initialize database
        self._init_database()

        # Register default event handlers
        self._register_default_handlers()

        logger.info("Real - time Collaboration Engine initialized")

    def _init_database(self):
        """Initialize collaboration database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Collaboration events table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS collaboration_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        data TEXT NOT NULL,
                        room_id TEXT
                    )
                """
                )

                # Active sessions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS active_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        last_activity TEXT NOT NULL,
                        status TEXT DEFAULT 'active'
                    )
                """
                )

                # Screening decisions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS screening_decisions (
                        decision_id TEXT PRIMARY KEY,
                        study_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        decision TEXT NOT NULL,
                        criteria TEXT,
                        notes TEXT,
                        timestamp TEXT NOT NULL,
                        confidence_score REAL DEFAULT 0.5,
                        project_id TEXT NOT NULL
                    )
                """
                )

                # Progress metrics table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS progress_metrics (
                        project_id TEXT PRIMARY KEY,
                        total_studies INTEGER DEFAULT 0,
                        screened_studies INTEGER DEFAULT 0,
                        included_studies INTEGER DEFAULT 0,
                        excluded_studies INTEGER DEFAULT 0,
                        uncertain_studies INTEGER DEFAULT 0,
                        last_updated TEXT NOT NULL
                    )
                """
                )

                conn.commit()
                logger.info("Collaboration database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    def _register_default_handlers(self):
        """Register default event handlers"""
        self.register_event_handler(
            EventType.SCREENING_UPDATE, self._handle_screening_update
        )
        self.register_event_handler(EventType.EVIDENCE_EDIT, self._handle_evidence_edit)
        self.register_event_handler(
            EventType.PROGRESS_UPDATE, self._handle_progress_update
        )
        self.register_event_handler(EventType.CHAT_MESSAGE, self._handle_chat_message)
        self.register_event_handler(EventType.USER_JOIN, self._handle_user_join)
        self.register_event_handler(EventType.USER_LEAVE, self._handle_user_leave)

    async def start_server(self):
        """Start the WebSocket server for real - time collaboration"""
        try:
            self.server = await websockets.serve(
                self._handle_websocket_connection, "localhost", self.port
            )
            self.running = True
            logger.info(f"Real - time collaboration server started on port {self.port}")

            # Keep server running
            await self.server.wait_closed()

        except Exception as e:
            logger.error(f"Failed to start collaboration server: {str(e)}")
            raise

    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logger.info("Real - time collaboration server stopped")

    async def _handle_websocket_connection(self, websocket):
        """Handle new WebSocket connections"""
        user_id = None
        try:
            # Wait for authentication message
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            auth_data = json.loads(auth_message)

            # Validate authentication
            user_id = auth_data.get("user_id")
            project_id = auth_data.get("project_id")
            username = auth_data.get("username")
            role = UserRole(auth_data.get("role", "reviewer"))

            if not all([user_id, project_id, username]):
                await websocket.send(
                    json.dumps({"type": "error", "message": "Authentication required"})
                )
                return

            # Create active user session
            active_user = ActiveUser(
                user_id=user_id,
                username=username,
                role=role,
                project_id=project_id,
                websocket=websocket,
                last_activity=datetime.now(timezone.utc),
            )

            # Add user to active sessions
            self.active_users[user_id] = active_user

            # Add user to project room
            if project_id not in self.project_rooms:
                self.project_rooms[project_id] = set()
            self.project_rooms[project_id].add(user_id)

            # Send connection confirmation
            await websocket.send(
                json.dumps(
                    {
                        "type": "connected",
                        "user_id": user_id,
                        "message": "Successfully connected to collaboration session",
                    }
                )
            )

            # Broadcast user join event
            await self._broadcast_event(
                CollaborationEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.USER_JOIN,
                    user_id=user_id,
                    project_id=project_id,
                    timestamp=datetime.now(timezone.utc),
                    data={"username": username, "role": role.value},
                )
            )

            # Handle incoming messages
            async for message in websocket:
                await self._process_message(user_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"User {user_id} disconnected")
        except asyncio.TimeoutError:
            logger.warning("WebSocket authentication timeout")
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
        finally:
            # Clean up user session
            if user_id and user_id in self.active_users:
                await self._handle_user_disconnect(user_id)

    async def _process_message(self, user_id: str, message: str):
        """Process incoming WebSocket messages"""
        try:
            data = json.loads(message)
            event_type = EventType(data.get("type"))

            # Update user activity
            if user_id in self.active_users:
                self.active_users[user_id].last_activity = datetime.now(timezone.utc)

            # Create collaboration event
            event = CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                user_id=user_id,
                project_id=self.active_users[user_id].project_id,
                timestamp=datetime.now(timezone.utc),
                data=data.get("data", {}),
            )

            # Process event
            await self._handle_event(event)

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")
            await self._send_error(user_id, f"Failed to process message: {str(e)}")

    async def _handle_event(self, event: CollaborationEvent):
        """Handle collaboration events"""
        try:
            # Store event in database
            await self._store_event(event)

            # Call registered handlers
            handlers = self.event_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Event handler error: {str(e)}")

            # Broadcast event to project room
            await self._broadcast_event(event)

        except Exception as e:
            logger.error(f"Event handling error: {str(e)}")

    async def _broadcast_event(self, event: CollaborationEvent):
        """Broadcast event to all users in project room"""
        if event.project_id not in self.project_rooms:
            return

        message = json.dumps(
            {
                "type": event.event_type.value,
                "event_id": event.event_id,
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
            }
        )

        # Send to all users in project room
        disconnected_users = set()
        for user_id in self.project_rooms[event.project_id]:
            if user_id in self.active_users:
                try:
                    await self.active_users[user_id].websocket.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_users.add(user_id)
                except Exception as e:
                    logger.error(f"Broadcast error for user {user_id}: {str(e)}")

        # Clean up disconnected users
        for user_id in disconnected_users:
            await self._handle_user_disconnect(user_id)

    async def _handle_user_disconnect(self, user_id: str):
        """Handle user disconnection"""
        if user_id not in self.active_users:
            return

        active_user = self.active_users[user_id]
        project_id = active_user.project_id

        # Remove from active users
        del self.active_users[user_id]

        # Remove from project room
        if project_id in self.project_rooms:
            self.project_rooms[project_id].discard(user_id)

        # Broadcast user leave event
        await self._broadcast_event(
            CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.USER_LEAVE,
                user_id=user_id,
                project_id=project_id,
                timestamp=datetime.now(timezone.utc),
                data={"username": active_user.username},
            )
        )

    async def _store_event(self, event: CollaborationEvent):
        """Store collaboration event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO collaboration_events
                    (event_id, event_type, user_id, project_id, timestamp, data, room_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.event_id,
                        event.event_type.value,
                        event.user_id,
                        event.project_id,
                        event.timestamp.isoformat(),
                        json.dumps(event.data),
                        event.room_id,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store event: {str(e)}")

    async def _send_error(self, user_id: str, message: str):
        """Send error message to specific user"""
        if user_id in self.active_users:
            try:
                await self.active_users[user_id].websocket.send(
                    json.dumps({"type": "error", "message": message})
                )
            except Exception as e:
                logger.error(f"Failed to send error to user {user_id}: {str(e)}")

    # Event Handlers
    async def _handle_screening_update(self, event: CollaborationEvent):
        """Handle screening decision updates"""
        try:
            data = event.data
            decision = ScreeningDecision(
                decision_id=str(uuid.uuid4()),
                study_id=data["study_id"],
                user_id=event.user_id,
                decision=data["decision"],
                criteria=data.get("criteria", []),
                notes=data.get("notes"),
                timestamp=event.timestamp,
                confidence_score=data.get("confidence_score", 0.5),
            )

            # Store screening decision
            await self._store_screening_decision(decision, event.project_id)

            # Update progress metrics
            await self._update_progress_metrics(event.project_id)

            # Check for conflicts
            await self._check_screening_conflicts(decision, event.project_id)

        except Exception as e:
            logger.error(f"Screening update handling error: {str(e)}")

    async def _handle_evidence_edit(self, event: CollaborationEvent):
        """Handle evidence table edits"""
        try:
            # Store evidence edit in database
            # Implement evidence editing logic
            logger.info(f"Evidence edit by user {event.user_id}: {event.data}")

        except Exception as e:
            logger.error(f"Evidence edit handling error: {str(e)}")

    async def _handle_progress_update(self, event: CollaborationEvent):
        """Handle progress updates"""
        try:
            await self._update_progress_metrics(event.project_id)

        except Exception as e:
            logger.error(f"Progress update handling error: {str(e)}")

    async def _handle_chat_message(self, event: CollaborationEvent):
        """Handle chat messages"""
        try:
            # Store chat message
            # Implement chat functionality
            logger.info(
                f"Chat message from {event.user_id}: {event.data.get('message', '')}"
            )

        except Exception as e:
            logger.error(f"Chat message handling error: {str(e)}")

    async def _handle_user_join(self, event: CollaborationEvent):
        """Handle user join events"""
        logger.info(
            f"User {event.data.get('username')} joined project {event.project_id}"
        )

    async def _handle_user_leave(self, event: CollaborationEvent):
        """Handle user leave events"""
        logger.info(
            f"User {event.data.get('username')} left project {event.project_id}"
        )

    async def _store_screening_decision(
        self, decision: ScreeningDecision, project_id: str
    ):
        """Store screening decision in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO screening_decisions
                    (decision_id, study_id, user_id, decision, criteria, notes, timestamp, confidence_score, project_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        decision.decision_id,
                        decision.study_id,
                        decision.user_id,
                        decision.decision,
                        json.dumps(decision.criteria),
                        decision.notes,
                        decision.timestamp.isoformat(),
                        decision.confidence_score,
                        project_id,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store screening decision: {str(e)}")

    async def _update_progress_metrics(self, project_id: str):
        """Update progress metrics for project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Calculate metrics from screening decisions
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN decision = 'include' THEN 1 ELSE 0 END) as included,
                        SUM(CASE WHEN decision = 'exclude' THEN 1 ELSE 0 END) as excluded,
                        SUM(CASE WHEN decision = 'uncertain' THEN 1 ELSE 0 END) as uncertain
                    FROM screening_decisions
                    WHERE project_id = ?
                """,
                    (project_id,),
                )

                result = cursor.fetchone()
                if result:
                    total, included, excluded, uncertain = result
                    screened = included + excluded + uncertain

                    # Update or insert progress metrics
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO progress_metrics
                        (project_id,
                            screened_studies,
                            included_studies,
                            excluded_studies,
                            uncertain_studies,
                            last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            project_id,
                            screened,
                            included or 0,
                            excluded or 0,
                            uncertain or 0,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to update progress metrics: {str(e)}")

    async def _check_screening_conflicts(
        self, decision: ScreeningDecision, project_id: str
    ):
        """Check for screening conflicts between reviewers"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check for existing decisions on the same study
                cursor.execute(
                    """
                    SELECT user_id, decision FROM screening_decisions
                    WHERE study_id = ? AND project_id = ? AND user_id != ?
                """,
                    (decision.study_id, project_id, decision.user_id),
                )

                existing_decisions = cursor.fetchall()

                # Check for conflicts
                conflicts = []
                for user_id, existing_decision in existing_decisions:
                    if existing_decision != decision.decision:
                        conflicts.append(
                            {
                                "conflicting_user": user_id,
                                "existing_decision": existing_decision,
                                "new_decision": decision.decision,
                            }
                        )

                # Broadcast conflict events if found
                if conflicts:
                    await self._broadcast_event(
                        CollaborationEvent(
                            event_id=str(uuid.uuid4()),
                            event_type=EventType.CONFLICT_DETECTED,
                            user_id=decision.user_id,
                            project_id=project_id,
                            timestamp=datetime.now(timezone.utc),
                            data={
                                "study_id": decision.study_id,
                                "conflicts": conflicts,
                            },
                        )
                    )

        except Exception as e:
            logger.error(f"Conflict checking error: {str(e)}")

    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def get_active_users(self, project_id: str) -> List[Dict[str, Any]]:
        """Get list of active users in project"""
        users = []
        if project_id in self.project_rooms:
            for user_id in self.project_rooms[project_id]:
                if user_id in self.active_users:
                    user = self.active_users[user_id]
                    users.append(
                        {
                            "user_id": user.user_id,
                            "username": user.username,
                            "role": user.role.value,
                            "last_activity": user.last_activity.isoformat(),
                            "current_screen": user.current_screen,
                        }
                    )
        return users

    async def get_progress_metrics(self, project_id: str) -> Optional[ProgressMetrics]:
        """Get real - time progress metrics for project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM progress_metrics WHERE project_id = ?
                """,
                    (project_id,),
                )

                result = cursor.fetchone()
                if result:
                    # Calculate additional metrics
                    active_reviewers = len(self.project_rooms.get(project_id, set()))

                    # Estimate completion time (simplified)
                    screened = result[2] or 0
                    total = result[1] or 1
                    if total > 0:
                        screened / total
                    else:
                        pass

                    # Calculate screening rate
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM screening_decisions
                        WHERE project_id = ? AND timestamp > datetime('now', '-1 hour')
                    """,
                        (project_id,),
                    )
                    recent_decisions = cursor.fetchone()[0] or 0
                    screening_rate = recent_decisions  # decisions per hour

                    # Estimate completion
                    remaining = total - screened
                    hours_remaining = (
                        remaining / max(screening_rate, 1) if screening_rate > 0 else 0
                    )
                    estimated_completion = datetime.now(timezone.utc) + timedelta(
                        hours=hours_remaining
                    )

                    return ProgressMetrics(
                        project_id=project_id,
                        total_studies=result[1] or 0,
                        screened_studies=result[2] or 0,
                        included_studies=result[3] or 0,
                        excluded_studies=result[4] or 0,
                        uncertain_studies=result[5] or 0,
                        active_reviewers=active_reviewers,
                        screening_rate=screening_rate,
                        estimated_completion=estimated_completion,
                        conflicts_pending=0,  # TODO: Calculate from conflicts table
                    )

        except Exception as e:
            logger.error(f"Failed to get progress metrics: {str(e)}")
        return None


# Utility functions for client integration
async def create_collaboration_client(
    user_id: str,
    username: str,
    project_id: str,
    role: str = "reviewer",
    server_url: str = "ws://localhost:8765",
):
    """Create a collaboration client connection"""
    try:
        websocket = await websockets.connect(server_url)

        # Send authentication
        auth_data = {
            "user_id": user_id,
            "username": username,
            "project_id": project_id,
            "role": role,
        }
        await websocket.send(json.dumps(auth_data))

        # Wait for confirmation
        response = await websocket.recv()
        response_data = json.loads(response)

        if response_data.get("type") == "connected":
            logger.info("Successfully connected to collaboration session")
            return websocket
        else:
            raise Exception(
                f"Connection failed: {response_data.get('message', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(f"Failed to create collaboration client: {str(e)}")
        raise


async def send_screening_decision(
    websocket: Any,
    study_id: str,
    decision: str,
    criteria: Optional[List[str]] = None,
    notes: Optional[str] = None,
    confidence: float = 0.5,
):
    """Send screening decision through collaboration client"""
    try:
        message = {
            "type": EventType.SCREENING_UPDATE.value,
            "data": {
                "study_id": study_id,
                "decision": decision,
                "criteria": criteria or [],
                "notes": notes,
                "confidence_score": confidence,
            },
        }
        await websocket.send(json.dumps(message))

    except Exception as e:
        logger.error(f"Failed to send screening decision: {str(e)}")
        raise


if __name__ == "__main__":
    # Example usage
    engine = RealtimeCollaborationEngine()

    # Start the collaboration server
    try:
        asyncio.run(engine.start_server())
    except KeyboardInterrupt:
        print("Collaboration server stopped")
