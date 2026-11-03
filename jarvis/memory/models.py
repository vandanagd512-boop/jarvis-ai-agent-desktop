"""SQLAlchemy database models for JARVIS memory and persistence."""

from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Conversation(Base):
    """Represents a conversational session."""
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Represents an individual message in a conversation."""
    __tablename__ = "messages"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system", "tool"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    tool_calls_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="messages")


class UserFact(Base):
    """Long-term learned facts, habits, and user preferences."""
    __tablename__ = "user_facts"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(50), nullable=False, default="general", index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Contact(Base):
    """User contacts book for direct calling and texting."""
    __tablename__ = "contacts"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(50), nullable=False)
    email = Column(String(150), default="", nullable=False)
    relationship = Column(String(50), default="friend", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Note(Base):
    """Productivity note created by user or JARVIS."""
    __tablename__ = "notes"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(255), default="", nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Reminder(Base):
    """Scheduled reminders and calendar tasks."""
    __tablename__ = "reminders"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, default="", nullable=False)
    due_at = Column(DateTime, nullable=False, index=True)
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    recurrence = Column(String(50), default="none", nullable=False)  # "none", "daily", "weekly", "monthly"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ExecutionAuditLog(Base):
    """Audit log of all tool and system automations executed by JARVIS."""
    __tablename__ = "execution_audit_logs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_name = Column(String(100), nullable=False, index=True)
    parameters_json = Column(Text, default="", nullable=False)
    status = Column(String(20), nullable=False)  # "success", "error", "cancelled"
    result_preview = Column(Text, default="", nullable=False)
    duration_ms = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
