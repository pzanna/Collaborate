"""
Eunice Authentication Service

This service handles user authentication, JWT token management, and RBAC.
Part of the Eunice Research Platform microservices architecture.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from jose import JWTError, jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, SQLModel, create_engine, select

from .models import User, UserCreate, UserInDB, UserPublic, UserUpdate, Token, TokenData
from .database import get_session, create_db_and_tables
from .config import get_settings

# Initialize settings
settings = get_settings()

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
    allow_origins=["http://localhost:3000", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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


async def get_user_by_email(session: Session, email: str) -> Optional[UserInDB]:
    """Get user by email."""
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()
    return result


async def get_user_by_username(session: Session, username: str) -> Optional[UserInDB]:
    """Get user by username."""
    statement = select(User).where(User.username == username)
    result = session.exec(statement).first()
    return result


async def authenticate_user(session: Session, username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user with username/email and password."""
    # Try to get user by username first
    user = await get_user_by_username(session, username)
    
    # If not found, try by email
    if not user:
        user = await get_user_by_email(session, username)
    
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> UserInDB:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(session, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: Annotated[UserInDB, Depends(get_current_user)]) -> UserInDB:
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
    
    existing_username = await get_user_by_username(session, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role or "researcher",  # Default role
        is_disabled=False
    )
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    return db_user


# Login endpoint
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
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
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


# Token validation endpoint (for other services)
@app.post("/validate-token")
async def validate_token(token: str, session: SessionDep):
    """Validate a JWT token and return user info (for service-to-service auth)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role", "researcher")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_username(session, username)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        
        return {
            "valid": True,
            "username": username,
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
        username = payload.get("sub")
        token_type = payload.get("type")
        
        if username is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user = await get_user_by_username(session, username)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=401, detail="User not found or disabled")
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(data={"sub": user.username})
        
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
        username = payload.get("sub")
        role = payload.get("role", "researcher")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_username(session, username)
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
            "username": username,
            "role": role,
            "resource": resource,
            "action": action
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
