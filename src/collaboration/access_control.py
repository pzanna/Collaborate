"""
Role - based Access Control System for Collaborative Systematic Reviews

This module provides comprehensive access control and security features including:
- Granular permission system for different user roles
- Project - based access management
- Audit trails for all user actions
- Secure authentication and authorization

Key Features:
- Hierarchical role - based permissions
- Resource - level access control
- Session management and security
- Comprehensive audit logging
- Multi - factor authentication support

Author: Eunice AI System
Date: 2024
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserRole(Enum):
    """Hierarchical user roles with increasing privileges"""

    OBSERVER = "observer"  # Read - only access
    REVIEWER = "reviewer"  # Can screen and assess studies
    SENIOR_REVIEWER = "senior_reviewer"  # Can resolve conflicts, mentor others
    LEAD_REVIEWER = "lead_reviewer"  # Can manage project settings
    PROJECT_ADMIN = "project_admin"  # Full project control
    SYSTEM_ADMIN = "system_admin"  # System - wide administration


class Permission(Enum):
    """Granular permissions for system operations"""

    # Reading permissions
    VIEW_STUDIES = "view_studies"
    VIEW_DECISIONS = "view_decisions"
    VIEW_PROGRESS = "view_progress"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT_LOGS = "view_audit_logs"

    # Screening permissions
    SCREEN_STUDIES = "screen_studies"
    EDIT_DECISIONS = "edit_decisions"
    ADD_NOTES = "add_notes"

    # Quality assessment permissions
    ASSESS_QUALITY = "assess_quality"
    EDIT_ASSESSMENTS = "edit_assessments"

    # Collaboration permissions
    RESOLVE_CONFLICTS = "resolve_conflicts"
    ASSIGN_REVIEWERS = "assign_reviewers"
    MENTOR_REVIEWERS = "mentor_reviewers"

    # Project management permissions
    EDIT_PROJECT_SETTINGS = "edit_project_settings"
    MANAGE_USERS = "manage_users"
    EXPORT_DATA = "export_data"
    IMPORT_DATA = "import_data"

    # Administrative permissions
    CREATE_PROJECTS = "create_projects"
    DELETE_PROJECTS = "delete_projects"
    MANAGE_SYSTEM = "manage_system"
    VIEW_ALL_PROJECTS = "view_all_projects"


class ResourceType(Enum):
    """Types of resources that can be access - controlled"""

    PROJECT = "project"
    STUDY = "study"
    DECISION = "decision"
    ASSESSMENT = "assessment"
    CONFLICT = "conflict"
    REPORT = "report"
    SYSTEM = "system"


class ActionType(Enum):
    """Types of actions for audit logging"""

    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    RESOLVE = "resolve"
    ASSIGN = "assign"
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class User:
    """System user with authentication details"""

    user_id: str
    username: str
    email: str
    full_name: str
    password_hash: str
    salt: str
    role: UserRole
    is_active: bool
    created_date: datetime
    last_login: Optional[datetime]
    failed_login_attempts: int
    lockout_until: Optional[datetime]
    mfa_enabled: bool
    mfa_secret: Optional[str]


@dataclass
class Session:
    """User session management"""

    session_id: str
    user_id: str
    created_timestamp: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_active: bool
    expires_at: datetime


@dataclass
class ProjectAccess:
    """Project - specific access control"""

    access_id: str
    user_id: str
    project_id: str
    role: UserRole
    permissions: Set[Permission]
    granted_by: str
    granted_date: datetime
    expires_date: Optional[datetime]
    is_active: bool


@dataclass
class AuditLogEntry:
    """Audit log entry for tracking user actions"""

    log_id: str
    user_id: str
    session_id: str
    action: ActionType
    resource_type: ResourceType
    resource_id: str
    project_id: Optional[str]
    timestamp: datetime
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str]


class AccessControlManager:
    """
    Comprehensive access control and security management system

    Features:
    - Role - based access control (RBAC)
    - Resource - level permissions
    - Session management
    - Audit logging
    - Multi - factor authentication
    - Security monitoring
    """

    def __init__(self, db_path: str = "data / eunice.db"):
        self.db_path = db_path
        self.session_timeout = timedelta(hours=8)  # 8 - hour sessions
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)

        # Role - permission mappings
        self.role_permissions = self._initialize_role_permissions()

        # Initialize database
        self._init_database()

        logger.info("Access Control Manager initialized")

    def _initialize_role_permissions(self) -> Dict[UserRole, Set[Permission]]:
        """Initialize role - based permission mappings"""
        return {
            UserRole.OBSERVER: {
                Permission.VIEW_STUDIES,
                Permission.VIEW_DECISIONS,
                Permission.VIEW_PROGRESS,
            },
            UserRole.REVIEWER: {
                Permission.VIEW_STUDIES,
                Permission.VIEW_DECISIONS,
                Permission.VIEW_PROGRESS,
                Permission.SCREEN_STUDIES,
                Permission.EDIT_DECISIONS,
                Permission.ADD_NOTES,
                Permission.ASSESS_QUALITY,
                Permission.EDIT_ASSESSMENTS,
            },
            UserRole.SENIOR_REVIEWER: {
                Permission.VIEW_STUDIES,
                Permission.VIEW_DECISIONS,
                Permission.VIEW_PROGRESS,
                Permission.VIEW_ANALYTICS,
                Permission.SCREEN_STUDIES,
                Permission.EDIT_DECISIONS,
                Permission.ADD_NOTES,
                Permission.ASSESS_QUALITY,
                Permission.EDIT_ASSESSMENTS,
                Permission.RESOLVE_CONFLICTS,
                Permission.MENTOR_REVIEWERS,
            },
            UserRole.LEAD_REVIEWER: {
                Permission.VIEW_STUDIES,
                Permission.VIEW_DECISIONS,
                Permission.VIEW_PROGRESS,
                Permission.VIEW_ANALYTICS,
                Permission.SCREEN_STUDIES,
                Permission.EDIT_DECISIONS,
                Permission.ADD_NOTES,
                Permission.ASSESS_QUALITY,
                Permission.EDIT_ASSESSMENTS,
                Permission.RESOLVE_CONFLICTS,
                Permission.ASSIGN_REVIEWERS,
                Permission.MENTOR_REVIEWERS,
                Permission.EXPORT_DATA,
            },
            UserRole.PROJECT_ADMIN: {
                Permission.VIEW_STUDIES,
                Permission.VIEW_DECISIONS,
                Permission.VIEW_PROGRESS,
                Permission.VIEW_ANALYTICS,
                Permission.VIEW_AUDIT_LOGS,
                Permission.SCREEN_STUDIES,
                Permission.EDIT_DECISIONS,
                Permission.ADD_NOTES,
                Permission.ASSESS_QUALITY,
                Permission.EDIT_ASSESSMENTS,
                Permission.RESOLVE_CONFLICTS,
                Permission.ASSIGN_REVIEWERS,
                Permission.MENTOR_REVIEWERS,
                Permission.EDIT_PROJECT_SETTINGS,
                Permission.MANAGE_USERS,
                Permission.EXPORT_DATA,
                Permission.IMPORT_DATA,
            },
            UserRole.SYSTEM_ADMIN: set(Permission),  # All permissions
        }

    def _init_database(self):
        """Initialize access control database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Users table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        full_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        role TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_date TEXT NOT NULL,
                        last_login TEXT,
                        failed_login_attempts INTEGER DEFAULT 0,
                        lockout_until TEXT,
                        mfa_enabled BOOLEAN DEFAULT FALSE,
                        mfa_secret TEXT
                    )
                """
                )

                # Sessions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_timestamp TEXT NOT NULL,
                        last_activity TEXT NOT NULL,
                        ip_address TEXT NOT NULL,
                        user_agent TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        expires_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """
                )

                # Project access table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS project_access (
                        access_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        permissions TEXT NOT NULL,
                        granted_by TEXT NOT NULL,
                        granted_date TEXT NOT NULL,
                        expires_date TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """
                )

                # Audit logs table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        log_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        project_id TEXT,
                        timestamp TEXT NOT NULL,
                        ip_address TEXT NOT NULL,
                        user_agent TEXT NOT NULL,
                        details TEXT,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (session_id) REFERENCES user_sessions (session_id)
                    )
                """
                )

                # Create indexes for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_project_access_user_project ON project_access(user_id, project_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp)"
                )

                conn.commit()
                logger.info("Access control database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    async def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        password: str,
        role: UserRole = UserRole.REVIEWER,
    ) -> User:
        """
        Create a new user with secure password hashing

        Args:
            username: Unique username
            email: User email address
            full_name: User's full name
            password: Plain text password (will be hashed)
            role: User role (default: REVIEWER)

        Returns:
            Created user object
        """
        try:
            # Generate salt and hash password
            salt = secrets.token_hex(32)
            password_hash = self._hash_password(password, salt)

            user = User(
                user_id=str(uuid.uuid4()),
                username=username,
                email=email,
                full_name=full_name,
                password_hash=password_hash,
                salt=salt,
                role=role,
                is_active=True,
                created_date=datetime.now(timezone.utc),
                last_login=None,
                failed_login_attempts=0,
                lockout_until=None,
                mfa_enabled=False,
                mfa_secret=None,
            )

            # Store user in database
            await self._store_user(user)

            # Log user creation
            await self._log_action(
                user_id=user.user_id,
                session_id="system",
                action=ActionType.CREATE,
                resource_type=ResourceType.SYSTEM,
                resource_id=user.user_id,
                ip_address="127.0.0.1",
                user_agent="system",
                details={"username": username, "role": role.value},
                success=True,
            )

            logger.info(f"Created user: {username} ({role.value})")
            return user

        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise

    async def authenticate_user(
        self, username: str, password: str, ip_address: str, user_agent: str
    ) -> Tuple[Optional[User], Optional[Session]]:
        """
        Authenticate user and create session

        Args:
            username: Username or email
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (User, Session) if successful, (None, None) if failed
        """
        try:
            # Get user from database
            user = await self._get_user_by_username(username)

            if not user:
                await self._log_action(
                    user_id="unknown",
                    session_id="none",
                    action=ActionType.LOGIN,
                    resource_type=ResourceType.SYSTEM,
                    resource_id="authentication",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"username": username, "reason": "user_not_found"},
                    success=False,
                    error_message="User not found",
                )
                return None, None

            # Check if account is locked
            if user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
                await self._log_action(
                    user_id=user.user_id,
                    session_id="none",
                    action=ActionType.LOGIN,
                    resource_type=ResourceType.SYSTEM,
                    resource_id="authentication",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"username": username, "reason": "account_locked"},
                    success=False,
                    error_message="Account temporarily locked",
                )
                return None, None

            # Check if account is active
            if not user.is_active:
                await self._log_action(
                    user_id=user.user_id,
                    session_id="none",
                    action=ActionType.LOGIN,
                    resource_type=ResourceType.SYSTEM,
                    resource_id="authentication",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"username": username, "reason": "account_inactive"},
                    success=False,
                    error_message="Account is inactive",
                )
                return None, None

            # Verify password
            if not self._verify_password(password, user.password_hash, user.salt):
                # Increment failed attempts
                await self._handle_failed_login(user)

                await self._log_action(
                    user_id=user.user_id,
                    session_id="none",
                    action=ActionType.LOGIN,
                    resource_type=ResourceType.SYSTEM,
                    resource_id="authentication",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"username": username, "reason": "invalid_password"},
                    success=False,
                    error_message="Invalid password",
                )
                return None, None

            # Reset failed attempts on successful login
            await self._reset_failed_attempts(user.user_id)

            # Create session
            session = await self._create_session(user, ip_address, user_agent)

            # Update last login
            await self._update_last_login(user.user_id)

            # Log successful login
            await self._log_action(
                user_id=user.user_id,
                session_id=session.session_id,
                action=ActionType.LOGIN,
                resource_type=ResourceType.SYSTEM,
                resource_id="authentication",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"username": username},
                success=True,
            )

            logger.info(f"User authenticated: {username}")
            return user, session

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return None, None

    async def validate_session(
        self, session_id: str, ip_address: Optional[str] = None
    ) -> Optional[Tuple[User, Session]]:
        """
        Validate user session and return user / session info

        Args:
            session_id: Session identifier
            ip_address: Optional IP validation

        Returns:
            Tuple of (User, Session) if valid, None if invalid
        """
        try:
            # Get session from database
            session = await self._get_session(session_id)

            if not session or not session.is_active:
                return None

            # Check expiration
            if session.expires_at < datetime.now(timezone.utc):
                await self._invalidate_session(session_id)
                return None

            # Optional IP validation
            if ip_address and session.ip_address != ip_address:
                logger.warning(
                    f"IP mismatch for session {session_id}: {session.ip_address} vs {ip_address}"
                )
                # Could be more strict here depending on security requirements

            # Get user
            user = await self._get_user_by_id(session.user_id)
            if not user or not user.is_active:
                await self._invalidate_session(session_id)
                return None

            # Update last activity
            await self._update_session_activity(session_id)

            return user, session

        except Exception as e:
            logger.error(f"Session validation failed: {str(e)}")
            return None

    async def check_permission(
        self,
        user_id: str,
        permission: Permission,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        Check if user has specific permission

        Args:
            user_id: User identifier
            permission: Permission to check
            project_id: Optional project context
            resource_id: Optional resource context

        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Get user
            user = await self._get_user_by_id(user_id)
            if not user or not user.is_active:
                return False

            # System admin has all permissions
            if user.role == UserRole.SYSTEM_ADMIN:
                return True

            # Check role - based permissions
            role_permissions = self.role_permissions.get(user.role, set())
            if permission in role_permissions:
                # For project - specific permissions, check project access
                if project_id:
                    project_access = await self._get_project_access(user_id, project_id)
                    if project_access and project_access.is_active:
                        # Check if project role has the permission
                        project_permissions = self.role_permissions.get(
                            project_access.role, set()
                        )
                        return permission in project_permissions
                    else:
                        return False
                else:
                    return True

            return False

        except Exception as e:
            logger.error(f"Permission check failed: {str(e)}")
            return False

    async def grant_project_access(
        self,
        user_id: str,
        project_id: str,
        role: UserRole,
        granted_by: str,
        expires_date: Optional[datetime] = None,
    ) -> ProjectAccess:
        """
        Grant user access to a specific project

        Args:
            user_id: User to grant access
            project_id: Project identifier
            role: Role within the project
            granted_by: User granting the access
            expires_date: Optional expiration date

        Returns:
            Project access record
        """
        try:
            project_access = ProjectAccess(
                access_id=str(uuid.uuid4()),
                user_id=user_id,
                project_id=project_id,
                role=role,
                permissions=self.role_permissions.get(role, set()),
                granted_by=granted_by,
                granted_date=datetime.now(timezone.utc),
                expires_date=expires_date,
                is_active=True,
            )

            await self._store_project_access(project_access)

            # Log access grant
            await self._log_action(
                user_id=granted_by,
                session_id="system",
                action=ActionType.ASSIGN,
                resource_type=ResourceType.PROJECT,
                resource_id=project_id,
                project_id=project_id,
                ip_address="127.0.0.1",
                user_agent="system",
                details={
                    "granted_to": user_id,
                    "role": role.value,
                    "expires_date": expires_date.isoformat() if expires_date else None,
                },
                success=True,
            )

            logger.info(
                f"Granted {role.value} access to project {project_id} for user {user_id}"
            )
            return project_access

        except Exception as e:
            logger.error(f"Project access grant failed: {str(e)}")
            raise

    async def log_user_action(
        self,
        user_id: str,
        session_id: str,
        action: ActionType,
        resource_type: ResourceType,
        resource_id: str,
        project_id: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """
        Log user action for audit trail

        Args:
            user_id: User performing action
            session_id: Session identifier
            action: Type of action performed
            resource_type: Type of resource affected
            resource_id: Resource identifier
            project_id: Optional project context
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional action details
            success: Whether action was successful
            error_message: Error message if failed
        """
        await self._log_action(
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            success=success,
            error_message=error_message,
        )

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_types: Optional[List[ActionType]] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit logs with filtering

        Args:
            user_id: Filter by user
            project_id: Filter by project
            start_date: Filter by start date
            end_date: Filter by end date
            action_types: Filter by action types
            limit: Maximum number of records

        Returns:
            List of audit log entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM audit_logs WHERE 1=1"
                params = []

                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)

                if project_id:
                    query += " AND project_id = ?"
                    params.append(project_id)

                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())

                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())

                if action_types:
                    action_placeholders = ",".join("?" * len(action_types))
                    query += f" AND action IN ({action_placeholders})"
                    params.extend([action.value for action in action_types])

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    log_entry = AuditLogEntry(
                        log_id=row[0],
                        user_id=row[1],
                        session_id=row[2],
                        action=ActionType(row[3]),
                        resource_type=ResourceType(row[4]),
                        resource_id=row[5],
                        project_id=row[6],
                        timestamp=datetime.fromisoformat(row[7]),
                        ip_address=row[8],
                        user_agent=row[9],
                        details=json.loads(row[10]) if row[10] else {},
                        success=bool(row[11]),
                        error_message=row[12],
                    )
                    logs.append(log_entry)

                return logs

        except Exception as e:
            logger.error(f"Audit log retrieval failed: {str(e)}")
            return []

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2"""
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()  # iterations

    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        return hmac.compare_digest(self._hash_password(password, salt), password_hash)

    async def _store_user(self, user: User):
        """Store user in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users
                    (user_id, username, email, full_name, password_hash, salt, role,
                     is_active, created_date, last_login, failed_login_attempts,
                     lockout_until, mfa_enabled, mfa_secret)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user.user_id,
                        user.username,
                        user.email,
                        user.full_name,
                        user.password_hash,
                        user.salt,
                        user.role.value,
                        user.is_active,
                        user.created_date.isoformat(),
                        user.last_login.isoformat() if user.last_login else None,
                        user.failed_login_attempts,
                        user.lockout_until.isoformat() if user.lockout_until else None,
                        user.mfa_enabled,
                        user.mfa_secret,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store user: {str(e)}")
            raise

    async def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username or email"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM users WHERE username = ? OR email = ?
                """,
                    (username, username),
                )

                row = cursor.fetchone()
                if row:
                    return User(
                        user_id=row[0],
                        username=row[1],
                        email=row[2],
                        full_name=row[3],
                        password_hash=row[4],
                        salt=row[5],
                        role=UserRole(row[6]),
                        is_active=bool(row[7]),
                        created_date=datetime.fromisoformat(row[8]),
                        last_login=datetime.fromisoformat(row[9]) if row[9] else None,
                        failed_login_attempts=row[10],
                        lockout_until=(
                            datetime.fromisoformat(row[11]) if row[11] else None
                        ),
                        mfa_enabled=bool(row[12]),
                        mfa_secret=row[13],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            return None

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))

                row = cursor.fetchone()
                if row:
                    return User(
                        user_id=row[0],
                        username=row[1],
                        email=row[2],
                        full_name=row[3],
                        password_hash=row[4],
                        salt=row[5],
                        role=UserRole(row[6]),
                        is_active=bool(row[7]),
                        created_date=datetime.fromisoformat(row[8]),
                        last_login=datetime.fromisoformat(row[9]) if row[9] else None,
                        failed_login_attempts=row[10],
                        lockout_until=(
                            datetime.fromisoformat(row[11]) if row[11] else None
                        ),
                        mfa_enabled=bool(row[12]),
                        mfa_secret=row[13],
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get user by ID: {str(e)}")
            return None

    async def _create_session(
        self, user: User, ip_address: str, user_agent: str
    ) -> Session:
        """Create new user session"""
        try:
            session = Session(
                session_id=secrets.token_urlsafe(32),
                user_id=user.user_id,
                created_timestamp=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
                expires_at=datetime.now(timezone.utc) + self.session_timeout,
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_sessions
                    (session_id, user_id, created_timestamp, last_activity,
                     ip_address, user_agent, is_active, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session.session_id,
                        session.user_id,
                        session.created_timestamp.isoformat(),
                        session.last_activity.isoformat(),
                        session.ip_address,
                        session.user_agent,
                        session.is_active,
                        session.expires_at.isoformat(),
                    ),
                )
                conn.commit()

            return session

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise

    async def _get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM user_sessions WHERE session_id = ?", (session_id,)
                )

                row = cursor.fetchone()
                if row:
                    return Session(
                        session_id=row[0],
                        user_id=row[1],
                        created_timestamp=datetime.fromisoformat(row[2]),
                        last_activity=datetime.fromisoformat(row[3]),
                        ip_address=row[4],
                        user_agent=row[5],
                        is_active=bool(row[6]),
                        expires_at=datetime.fromisoformat(row[7]),
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            return None

    async def _get_project_access(
        self, user_id: str, project_id: str
    ) -> Optional[ProjectAccess]:
        """Get project access for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM project_access
                    WHERE user_id = ? AND project_id = ? AND is_active = TRUE
                """,
                    (user_id, project_id),
                )

                row = cursor.fetchone()
                if row:
                    return ProjectAccess(
                        access_id=row[0],
                        user_id=row[1],
                        project_id=row[2],
                        role=UserRole(row[3]),
                        permissions=set(Permission(p) for p in json.loads(row[4])),
                        granted_by=row[5],
                        granted_date=datetime.fromisoformat(row[6]),
                        expires_date=datetime.fromisoformat(row[7]) if row[7] else None,
                        is_active=bool(row[8]),
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get project access: {str(e)}")
            return None

    async def _store_project_access(self, project_access: ProjectAccess):
        """Store project access in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO project_access
                    (access_id, user_id, project_id, role, permissions, granted_by,
                     granted_date, expires_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        project_access.access_id,
                        project_access.user_id,
                        project_access.project_id,
                        project_access.role.value,
                        json.dumps([p.value for p in project_access.permissions]),
                        project_access.granted_by,
                        project_access.granted_date.isoformat(),
                        (
                            project_access.expires_date.isoformat()
                            if project_access.expires_date
                            else None
                        ),
                        project_access.is_active,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store project access: {str(e)}")
            raise

    async def _log_action(
        self,
        user_id: str,
        session_id: str,
        action: ActionType,
        resource_type: ResourceType,
        resource_id: str,
        ip_address: str,
        user_agent: str,
        details: Dict[str, Any],
        success: bool,
        project_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Log action to audit trail"""
        try:
            log_entry = AuditLogEntry(
                log_id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                project_id=project_id,
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                success=success,
                error_message=error_message,
            )

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO audit_logs
                    (log_id, user_id, session_id, action, resource_type, resource_id,
                     project_id, timestamp, ip_address, user_agent, details, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log_entry.log_id,
                        log_entry.user_id,
                        log_entry.session_id,
                        log_entry.action.value,
                        log_entry.resource_type.value,
                        log_entry.resource_id,
                        log_entry.project_id,
                        log_entry.timestamp.isoformat(),
                        log_entry.ip_address,
                        log_entry.user_agent,
                        json.dumps(log_entry.details),
                        log_entry.success,
                        log_entry.error_message,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")

    async def _handle_failed_login(self, user: User):
        """Handle failed login attempt"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                new_attempts = user.failed_login_attempts + 1
                lockout_until = None

                if new_attempts >= self.max_failed_attempts:
                    lockout_until = datetime.now(timezone.utc) + self.lockout_duration

                cursor.execute(
                    """
                    UPDATE users
                    SET failed_login_attempts = ?, lockout_until = ?
                    WHERE user_id = ?
                """,
                    (
                        new_attempts,
                        lockout_until.isoformat() if lockout_until else None,
                        user.user_id,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to handle failed login: {str(e)}")

    async def _reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET failed_login_attempts = 0, lockout_until = NULL
                    WHERE user_id = ?
                """,
                    (user_id,),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to reset failed attempts: {str(e)}")

    async def _update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users SET last_login = ? WHERE user_id = ?
                """,
                    (datetime.now(timezone.utc).isoformat(), user_id),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update last login: {str(e)}")

    async def _update_session_activity(self, session_id: str):
        """Update session last activity"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE user_sessions SET last_activity = ? WHERE session_id = ?
                """,
                    (datetime.now(timezone.utc).isoformat(), session_id),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session activity: {str(e)}")

    async def _invalidate_session(self, session_id: str):
        """Invalidate user session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE user_sessions SET is_active = FALSE WHERE session_id = ?
                """,
                    (session_id,),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to invalidate session: {str(e)}")


def require_permission(permission: Permission, project_id_param: Optional[str] = None):
    """
    Decorator to require specific permission for a function

    Args:
        permission: Required permission
        project_id_param: Parameter name that contains project_id
    """

    def decorator(func):
        """TODO: Add docstring for decorator."""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would need integration with the request context
            # For now, this is a placeholder for the pattern
            # In a real implementation, you'd extract user / session from request
            pass

        return wrapper

    return decorator


if __name__ == "__main__":
    # Example usage
    async def test_access_control():
        access_control = AccessControlManager()

        # Create test user
        await access_control.create_user(
            username="test_reviewer",
            email="test@example.com",
            full_name="Test Reviewer",
            password="secure_password123",
            role=UserRole.REVIEWER,
        )

        # Authenticate user
        user_result, session = await access_control.authenticate_user(
            username="test_reviewer",
            password="secure_password123",
            ip_address="127.0.0.1",
            user_agent="test - client",
        )

        if user_result and session:
            print(f"User authenticated: {user_result.username}")

            # Check permissions
            can_screen = await access_control.check_permission(
                user_id=user_result.user_id, permission=Permission.SCREEN_STUDIES
            )
            print(f"Can screen studies: {can_screen}")

            # Grant project access
            project_access = await access_control.grant_project_access(
                user_id=user_result.user_id,
                project_id="test_project",
                role=UserRole.SENIOR_REVIEWER,
                granted_by="system",
            )
            print(f"Project access granted: {project_access.role.value}")

            # Log user action
            await access_control.log_user_action(
                user_id=user_result.user_id,
                session_id=session.session_id,
                action=ActionType.VIEW,
                resource_type=ResourceType.STUDY,
                resource_id="study_123",
                project_id="test_project",
                details={"study_title": "Test Study"},
            )

            # Get audit logs
            logs = await access_control.get_audit_logs(
                user_id=user_result.user_id, limit=10
            )
            print(f"Audit logs retrieved: {len(logs)}")

    # Run test
    asyncio.run(test_access_control())
