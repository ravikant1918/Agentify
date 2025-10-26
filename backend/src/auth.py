"""
Authentication and authorization utilities
"""
import os
import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

import jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import User, UserSession

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# JWT Bearer scheme
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

# Simple password hashing using PBKDF2 (more reliable than BCrypt for this case)
def get_password_hash(password: str) -> str:
    """Hash a password using PBKDF2 with SHA256"""
    # Generate a random salt
    salt = secrets.token_bytes(32)
    # Hash the password
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Return salt + hash encoded in base64
    return base64.b64encode(salt + pwdhash).decode('ascii')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Decode the stored hash
        pwdhash_bytes = base64.b64decode(hashed_password.encode('ascii'))
        # Extract salt and hash
        salt = pwdhash_bytes[:32]
        stored_hash = pwdhash_bytes[32:]
        # Hash the plain password with the same salt
        pwdhash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        # Compare hashes
        return pwdhash == stored_hash
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token (longer expiry)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days for refresh token
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")


def hash_token(token: str) -> str:
    """Create a hash of the token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password"""
    # Query user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == username)
        ).where(User.is_active)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        return None
    
    return user


async def create_user_session(
    db: AsyncSession, 
    user: User, 
    token: str, 
    request: Request
) -> UserSession:
    """Create a new user session"""
    token_hash = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    token = credentials.credentials
    
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise AuthenticationError()
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise AuthenticationError()
    
    # Check if session exists and is valid
    token_hash = hash_token(token)
    result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.now(timezone.utc)
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise AuthenticationError("Session not found or expired")
    
    # Get user
    result = await db.execute(
        select(User).where(
            User.id == user_uuid,
            User.is_active
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise AuthenticationError("User not found")
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Get the current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, 
            detail="Not enough permissions"
        )
    return current_user


async def logout_user(
    token: str,
    db: AsyncSession
) -> bool:
    """Logout a user by invalidating their session"""
    token_hash = hash_token(token)
    
    result = await db.execute(
        select(UserSession).where(UserSession.token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    
    if session:
        await db.delete(session)
        await db.commit()
        return True
    
    return False


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """Clean up expired sessions"""
    result = await db.execute(
        select(UserSession).where(
            UserSession.expires_at < datetime.now(timezone.utc)
        )
    )
    expired_sessions = result.scalars().all()
    
    for session in expired_sessions:
        await db.delete(session)
    
    await db.commit()
    return len(expired_sessions)