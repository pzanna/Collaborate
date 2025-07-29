"""
Eunice Authentication Service

This service handles user authentication, JWT token management, RBAC, and 2FA.
Part of the Eunice Research Platform microservices architecture.
"""

import json
import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from io import BytesIO
import base64
import shutil
from pathlib import Path
import subprocess
import psutil

from jose import JWTError, jwt
from fastapi import Depends, FastAPI, HTTPException, status, Response, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, SQLModel, create_engine, select

from .models import (
    User, UserCreate, UserInDB, UserPublic, UserUpdate, Token, TokenData,
    LoginWith2FARequest, Setup2FAResponse, Verify2FARequest, 
    Disable2FARequest, BackupCodeRequest
)
from .database import get_session, create_db_and_tables
from .config import get_settings
from .two_factor import TwoFactorAuthService
from .two_factor import TwoFactorAuthService

# Password change request model
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# Initialize settings
settings = get_settings()

# Initialize logger
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="Eunice Authentication Service",
    description="JWT-based authentication and RBAC for the Eunice Research Platform",
    version="0.3.2",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize 2FA service
tfa_service = TwoFactorAuthService()

# Session dependency
SessionDep = Annotated[Session, Depends(get_session)]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Get user by email."""
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()
    return result


async def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = await get_user_by_email(session, email)
    
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(session, token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get the current active user (not disabled)."""
    if current_user.is_disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Startup event
@app.on_event("startup")
def on_startup():
    """Create database tables on startup."""
    create_db_and_tables()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "0.3.2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Debug CORS configuration endpoint  
@app.get("/debug/cors")
async def debug_cors():
    """Debug CORS configuration."""
    return {
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "allowed_origins_list": settings.ALLOWED_ORIGINS.split(","),
        "settings_debug": settings.DEBUG
    }


# User registration endpoint
@app.post("/register", response_model=UserPublic)
async def register_user(user_data: UserCreate, session: SessionDep):
    """Register a new user."""
    # Check if user already exists
    existing_user = await get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        role=user_data.role or "researcher",  # Default role
        is_disabled=False
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user


# Login endpoint with 2FA support
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep
):
    """Authenticate user and return JWT tokens."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if 2FA is enabled for this user
    if user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="2FA required",
            headers={"X-Require-2FA": "true"}
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# Login with 2FA endpoint
@app.post("/login-2fa", response_model=Token)
async def login_with_2fa(
    login_data: LoginWith2FARequest,
    session: SessionDep
):
    """Authenticate user with 2FA and return JWT tokens."""
    user = await authenticate_user(session, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Check if 2FA is enabled
    if not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this account"
        )
    
    # Verify TOTP code or backup code
    totp_valid = False
    
    if login_data.totp_code:
        if len(login_data.totp_code) == 6 and login_data.totp_code.isdigit():
            # Regular TOTP code
            if user.totp_secret:
                totp_valid = tfa_service.verify_totp_code(user.totp_secret, login_data.totp_code)
        elif len(login_data.totp_code) == 8:
            # Backup code
            if user.backup_codes:
                totp_valid, updated_backup_codes = tfa_service.verify_backup_code(
                    user.backup_codes, login_data.totp_code
                )
                if totp_valid:
                    # Update backup codes in database
                    user.backup_codes = updated_backup_codes
                    session.add(user)
                    session.commit()
    
    if not totp_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# Get current user endpoint
@app.get("/users/me", response_model=UserPublic)
async def read_users_me(current_user: Annotated[UserInDB, Depends(get_current_active_user)]):
    """Get current authenticated user information."""
    return current_user


# Update user endpoint
@app.patch("/users/me", response_model=UserPublic)
async def update_user_me(
    user_update: UserUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Update current user information."""
    user_data = user_update.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in user_data:
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
    
    # Update user
    for field, value in user_data.items():
        setattr(current_user, field, value)
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user


# Delete user account endpoint
@app.delete("/users/me")
async def delete_user_me(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Delete current user account."""
    session.delete(current_user)
    session.commit()
    
    return {"message": "Account successfully deleted"}


# Admin endpoint to delete any user (requires admin role)
@app.delete("/admin/users/{user_id}")
async def delete_user_by_id(
    user_id: int,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Delete a user by ID (admin only)."""
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete other users"
        )
    
    # Find the user to delete
    statement = select(User).where(User.id == user_id)  
    user_to_delete = session.exec(statement).first()
    
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    session.delete(user_to_delete)
    session.commit()
    
    return {"message": f"User {user_to_delete.email} (ID: {user_id}) successfully deleted"}


# Token validation endpoint (for other services)
@app.post("/validate-token")
async def validate_token(token: str, session: SessionDep):
    """Validate a JWT token and return user info (for service-to-service auth)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role", "researcher")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_email(session, email)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        
        return {
            "valid": True,
            "email": email,
            "role": role,
            "user_id": user.id
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Refresh token endpoint
@app.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_token: str, session: SessionDep):
    """Refresh access token using refresh token."""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if email is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user = await get_user_by_email(session, email)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role},
            expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(data={"sub": user.email})
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# Role-based access validation endpoint
@app.post("/check-permission")
async def check_permission(
    token: str,
    resource: str,
    action: str,
    session: SessionDep
):
    """Check if user has permission for a specific resource and action."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role", "researcher")
        
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_email(session, email)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        
        # Basic RBAC logic (can be extended)
        permissions = {
            "admin": ["*:*"],  # Admin has all permissions
            "researcher": [
                "literature:read", "literature:search", "literature:create",
                "research:read", "research:create", "research:update",
                "planning:read", "planning:create", "planning:update",
                "memory:read", "memory:create", "memory:update",
                "executor:read", "executor:create",
                "writer:read", "writer:create", "writer:update"
            ],
            "collaborator": [
                "literature:read", "research:read", "research:comment",
                "planning:read", "memory:read", "writer:read"
            ]
        }
        
        user_permissions = permissions.get(role, [])
        required_permission = f"{resource}:{action}"
        
        # Check if user has specific permission or wildcard
        has_permission = (
            required_permission in user_permissions or
            "*:*" in user_permissions or
            f"{resource}:*" in user_permissions
        )
        
        return {
            "has_permission": has_permission,
            "email": email,
            "role": role,
            "resource": resource,
            "action": action
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# User profile update endpoint
@app.put("/users/me", response_model=UserPublic)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Update the current user's profile information."""
    
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = await get_user_by_email(session, user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Update user fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user


# Password change endpoint
@app.post("/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Change the current user's password."""
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash and update new password
    new_hashed_password = get_password_hash(password_change.new_password)
    current_user.hashed_password = new_hashed_password
    
    session.add(current_user)
    session.commit()
    
    return {"message": "Password changed successfully"}


# Profile picture upload endpoint
@app.post("/upload-profile-picture")
async def upload_profile_picture(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep,
    file: UploadFile = File(...)
):
    """Upload a profile picture for the current user."""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, GIF, etc.)"
        )
    
    # Validate file size (5MB limit)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 5MB"
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads/profile_pictures")
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create upload directory. Please contact system administrator."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare upload directory: {str(e)}"
        )
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    unique_filename = f"profile_{current_user.id}_{secrets.token_urlsafe(8)}.{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission denied. Unable to save file. Please contact system administrator."
        )
    except OSError as e:
        if e.errno == errno.EROFS:  # Read-only file system
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File system is read-only. Please contact system administrator."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File system error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Update user profile with image URL
    profile_image_url = f"/uploads/profile_pictures/{unique_filename}"
    current_user.profile_image_url = profile_image_url
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return {
        "message": "Profile picture uploaded successfully",
        "profile_image_url": profile_image_url
    }


# Serve uploaded profile pictures
@app.get("/uploads/profile_pictures/{filename}")
async def get_profile_picture(filename: str):
    """Serve uploaded profile pictures."""
    file_path = Path("uploads/profile_pictures") / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile picture not found"
        )
    
    return FileResponse(file_path)


# System Health Models
class ContainerStatus(BaseModel):
    name: str
    status: str  # running, stopped, error
    uptime: str
    port: Optional[str] = None
    health: str  # healthy, unhealthy, starting


class SystemInfo(BaseModel):
    platform: str
    total_containers: int
    running_containers: int
    memory: dict
    disk: dict


class SystemHealthResponse(BaseModel):
    containers: list[ContainerStatus]
    system_info: SystemInfo


# System health endpoint
@app.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Get real-time system health information."""
    
    # Check if user has admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    try:
        import docker
        import os
        from datetime import datetime
        
        # Connect to Docker via the secure socket proxy
        docker_host = os.getenv("DOCKER_HOST", "tcp://docker-socket-proxy:2375")
        client = docker.DockerClient(base_url=docker_host)
        
        # Get all containers
        all_containers = client.containers.list(all=True)
        
        containers = []
        running_count = 0
        
        for container in all_containers:
            status_text = container.status
            if status_text == "running":
                running_count += 1
            
            # Calculate uptime for running containers
            uptime = "N/A"
            if status_text == "running" and container.attrs.get("State", {}).get("StartedAt"):
                started_at = container.attrs["State"]["StartedAt"]
                try:
                    # Parse Docker timestamp format
                    started_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime_delta = datetime.now(started_time.tzinfo) - started_time
                    days = uptime_delta.days
                    hours, remainder = divmod(uptime_delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    if days > 0:
                        uptime = f"{days}d {hours}h {minutes}m"
                    else:
                        uptime = f"{hours}h {minutes}m"
                except:
                    uptime = "Unknown"
            
            # Extract port mapping
            port_info = None
            if container.attrs.get("NetworkSettings", {}).get("Ports"):
                ports = container.attrs["NetworkSettings"]["Ports"]
                for container_port, host_binding in ports.items():
                    if host_binding:
                        port_info = host_binding[0]["HostPort"]
                        break
            
            # Determine health status
            health_status = "healthy"  # Default
            health_check = container.attrs.get("State", {}).get("Health", {})
            if health_check:
                health_status = health_check.get("Status", "healthy").lower()
            elif status_text == "exited":
                health_status = "unhealthy"
            elif status_text == "running":
                health_status = "healthy"
            else:
                health_status = "starting"
            
            containers.append(ContainerStatus(
                name=container.name,
                status=status_text,
                uptime=uptime,
                port=port_info,
                health=health_status
            ))
        
        # Get real system information using psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = SystemInfo(
            platform=f"Docker Platform on {os.uname().sysname}",
            total_containers=len(containers),
            running_containers=running_count,
            memory={
                "used": f"{memory.percent:.1f}%",
                "total": f"{memory.total // (1024**3)}GB"
            },
            disk={
                "used": f"{disk.percent:.1f}%", 
                "total": f"{disk.total // (1024**3)}GB"
            }
        )
        
        return SystemHealthResponse(
            containers=containers,
            system_info=system_info
        )
        
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System health check failed: {str(e)}"
        )


# 2FA Setup endpoint
@app.post("/2fa/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Set up 2FA for the current user."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled for this account"
        )
    
    # Generate new secret and backup codes
    secret = tfa_service.generate_secret()
    backup_codes = tfa_service.generate_backup_codes()
    provisioning_uri = tfa_service.get_provisioning_uri(secret, current_user.email)
    
    # Update user with new secret (but don't enable 2FA yet)
    current_user.totp_secret = secret
    current_user.backup_codes = json.dumps(backup_codes)
    session.add(current_user)
    session.commit()
    
    return Setup2FAResponse(
        secret_key=secret,
        qr_code_url=provisioning_uri,
        backup_codes=backup_codes
    )


# 2FA QR Code endpoint
@app.get("/2fa/qrcode")
async def get_2fa_qrcode(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Get QR code for 2FA setup."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /2fa/setup first."
        )
    
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled for this account"
        )
    
    provisioning_uri = tfa_service.get_provisioning_uri(
        current_user.totp_secret, current_user.email
    )
    qr_buffer = tfa_service.generate_qr_code(provisioning_uri)
    
    return StreamingResponse(
        BytesIO(qr_buffer.getvalue()),
        media_type="image/png",
        headers={"Content-Disposition": "inline; filename=qrcode.png"}
    )


# 2FA Verification and Enable endpoint
@app.post("/2fa/verify")
async def verify_and_enable_2fa(
    verify_data: Verify2FARequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Verify TOTP code and enable 2FA."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled for this account"
        )
    
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /2fa/setup first."
        )
    
    # Verify TOTP code
    if not tfa_service.verify_totp_code(current_user.totp_secret, verify_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    # Enable 2FA
    current_user.is_2fa_enabled = True
    session.add(current_user)
    session.commit()
    
    return {"message": "2FA successfully enabled"}


# 2FA Disable endpoint
@app.post("/2fa/disable")
async def disable_2fa(
    disable_data: Disable2FARequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Disable 2FA for the current user."""
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this account"
        )
    
    # Verify password
    if not verify_password(disable_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Verify TOTP code or backup code
    totp_valid = False
    
    if disable_data.totp_code and current_user.totp_secret:
        totp_valid = tfa_service.verify_totp_code(current_user.totp_secret, disable_data.totp_code)
    elif disable_data.backup_code and current_user.backup_codes:
        totp_valid, _ = tfa_service.verify_backup_code(
            current_user.backup_codes, disable_data.backup_code
        )
    
    if not totp_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code or backup code"
        )
    
    # Disable 2FA and clear secrets
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None
    session.add(current_user)
    session.commit()
    
    return {"message": "2FA successfully disabled"}


# 2FA Status endpoint
@app.get("/2fa/status")
async def get_2fa_status(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Get 2FA status for the current user."""
    return {
        "is_2fa_enabled": current_user.is_2fa_enabled,
        "has_backup_codes": tfa_service.has_remaining_backup_codes(current_user.backup_codes),
        "remaining_backup_codes": tfa_service.count_remaining_backup_codes(current_user.backup_codes)
    }


# Regenerate backup codes endpoint
@app.post("/2fa/backup-codes/regenerate")
async def regenerate_backup_codes(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    session: SessionDep
):
    """Regenerate backup codes for 2FA."""
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this account"
        )
    
    # Generate new backup codes
    new_backup_codes = tfa_service.generate_backup_codes()
    current_user.backup_codes = json.dumps(new_backup_codes)
    session.add(current_user)
    session.commit()
    
    return {
        "message": "Backup codes regenerated successfully",
        "backup_codes": new_backup_codes
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
