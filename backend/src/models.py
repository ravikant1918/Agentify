"""
Database models for Agentify application
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import String, Text, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    """User model for authentication and user management"""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    chat_threads: Mapped[List["ChatThread"]] = relationship("ChatThread", back_populates="user", cascade="all, delete-orphan")
    mcp_servers: Mapped[List["MCPServer"]] = relationship("MCPServer", back_populates="user", cascade="all, delete-orphan")
    llm_configurations: Mapped[List["LLMConfiguration"]] = relationship("LLMConfiguration", back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[Optional["UserPreferences"]] = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }


class ChatThread(Base):
    """Chat thread model to organize conversations"""
    __tablename__ = "chat_threads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_threads")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_archived": self.is_archived,
            "message_count": len(self.messages) if hasattr(self, 'messages') else 0
        }


class ChatMessage(Base):
    """Chat message model to store conversation history"""
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("chat_threads.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    config_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tool_calls: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationships
    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "thread_id": str(self.thread_id),
            "role": self.role,
            "content": self.content,
            "metadata": self.config_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id
        }


class MCPServer(Base):
    """MCP Server configuration model"""
    __tablename__ = "mcp_servers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    server_type: Mapped[str] = mapped_column(String(50), nullable=False)  # stdio, sse
    configuration: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="mcp_servers")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description,
            "server_type": self.server_type,
            "configuration": self.configuration,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class LLMConfiguration(Base):
    """LLM Configuration model"""
    __tablename__ = "llm_configurations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # azure, openai, google
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    configuration: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="llm_configurations")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "provider": self.provider,
            "model_name": self.model_name,
            "configuration": self.configuration,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UserSession(Base):
    """User session model for JWT token management"""
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_agent": self.user_agent,
            "ip_address": str(self.ip_address) if self.ip_address else None
        }


class UserPreferences(Base):
    """User preferences model"""
    __tablename__ = "user_preferences"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    theme: Mapped[str] = mapped_column(String(20), default="light")  # light, dark, auto
    language: Mapped[str] = mapped_column(String(10), default="en")
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "theme": self.theme,
            "language": self.language,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Add indexes for better performance
Index("idx_users_username", User.username)
Index("idx_users_email", User.email)
Index("idx_chat_threads_user_id", ChatThread.user_id)
Index("idx_chat_messages_thread_id", ChatMessage.thread_id)
Index("idx_mcp_servers_user_id", MCPServer.user_id)
Index("idx_llm_configurations_user_id", LLMConfiguration.user_id)
Index("idx_user_sessions_user_id", UserSession.user_id)
Index("idx_user_sessions_expires_at", UserSession.expires_at)