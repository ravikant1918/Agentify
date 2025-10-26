"""
Pydantic schemas for API requests and responses
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict


# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_superuser: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None


# Authentication schemas
class LoginRequest(BaseModel):
    username: str  # Can be username or email
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int = 86400  # 24 hours in seconds


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


# Chat schemas
class ChatThreadCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatThreadUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None


class ChatThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    message_count: int = 0


class ChatMessageCreate(BaseModel):
    role: str  # user, assistant, system, tool
    content: str
    config_metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    thread_id: UUID
    role: str
    content: str
    config_metadata: Dict[str, Any]
    created_at: datetime
    tool_calls: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    response: str
    thread_id: UUID
    message_id: UUID


# MCP Server schemas
class MCPServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    server_type: str  # stdio, sse
    configuration: Dict[str, Any]


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    server_type: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MCPServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    server_type: str
    configuration: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# LLM Configuration schemas
class LLMConfigurationCreate(BaseModel):
    name: str
    provider: str  # azure, openai, google
    model_name: str
    configuration: Dict[str, Any]
    is_default: bool = False


class LLMConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class LLMConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    name: str
    provider: str
    model_name: str
    configuration: Dict[str, Any]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# User Preferences schemas
class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = None  # light, dark, auto
    language: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    theme: str
    language: str
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# API Response schemas
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    database: bool
    redis: Optional[bool] = None
    timestamp: datetime