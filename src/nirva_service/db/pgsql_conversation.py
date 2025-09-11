"""
Advanced Chat System - Database Models

This module defines the database models for the advanced Nirva chat system,
implementing a single conversation per user with enhanced context awareness.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from .pgsql_object import Base, UUIDBase


class MessageRole(str, Enum):
    """Enum for message roles in conversation"""
    SYSTEM = "system"
    HUMAN = "human" 
    AI = "ai"


class MessageType(str, Enum):
    """Enum for different message types"""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    ACTION = "action"
    SYSTEM_NOTIFICATION = "system_notification"


# Single conversation per user
class UserConversationDB(Base):
    """
    Single conversation thread per user with Nirva.
    Replaces the concept of multiple chat sessions.
    """
    __tablename__ = "user_conversations"
    
    # Primary key is user_id (one conversation per user)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True, index=True
    )
    
    # Conversation metadata
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Chat with Nirva"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    
    # Conversation statistics
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # AI personality settings for this conversation
    personality_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Conversation summary for context (updated periodically)
    conversation_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB")
    messages: Mapped[List["ChatMessageDB"]] = relationship(
        "ChatMessageDB", 
        cascade="all, delete-orphan",
        primaryjoin="UserConversationDB.user_id == foreign(ChatMessageDB.user_id)"
    )
    context: Mapped[Optional["ConversationContextDB"]] = relationship(
        "ConversationContextDB", uselist=False,
        cascade="all, delete-orphan",
        primaryjoin="UserConversationDB.user_id == foreign(ConversationContextDB.user_id)"
    )


# Enhanced message storage
class ChatMessageDB(UUIDBase):
    """
    Enhanced message model with support for different types and rich context.
    """
    __tablename__ = "chat_messages"
    
    # User and conversation association
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    
    # Message content and metadata
    role: Mapped[MessageRole] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(default=MessageType.TEXT, nullable=False)
    
    # Attachments and message metadata (JSON)
    attachments: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, default=list, nullable=True
    )
    message_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Timestamp with timezone
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    
    # Context snapshot at time of message (for AI awareness)
    context_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Performance tracking
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", overlaps="messages")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_chat_messages_user_timestamp", "user_id", "timestamp"),
        Index("idx_chat_messages_user_type", "user_id", "message_type"),
        Index("idx_chat_messages_role_timestamp", "role", "timestamp"),
    )


# Context tracking for AI awareness
class ConversationContextDB(Base):
    """
    Stores conversation context for AI awareness including mental state,
    recent events, and conversation memory.
    """
    __tablename__ = "conversation_context"
    
    # Primary key is user_id (one context per user/conversation)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), primary_key=True, index=True
    )
    
    # Mental state context summary
    mental_state_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Recent events summary for context
    recent_events_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Conversation memory (key topics, important facts, etc.)
    conversation_memory: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # AI personality state
    personality_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, default=dict, nullable=True
    )
    
    # Last update timestamp
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", overlaps="context")


# Message reactions and interactions (future enhancement)
class MessageReactionDB(UUIDBase):
    """
    User reactions to messages (likes, helpful, etc.)
    """
    __tablename__ = "message_reactions"
    
    # Message association
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    
    # Reaction type
    reaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    message: Mapped["ChatMessageDB"] = relationship("ChatMessageDB")
    user: Mapped["UserDB"] = relationship("UserDB")
    
    # Unique constraint on user + message + reaction_type
    __table_args__ = (
        Index("idx_unique_user_message_reaction", "user_id", "message_id", "reaction_type", unique=True),
    )


# Voice message metadata (for voice message type)
class VoiceMessageDB(UUIDBase):
    """
    Extended metadata for voice messages
    """
    __tablename__ = "voice_messages"
    
    # Message association
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id"), nullable=False, index=True, unique=True
    )
    
    # Audio file information
    audio_file_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("audio_files.id"), nullable=True, index=True
    )
    
    # Voice message metadata
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    transcription_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcription_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed, failed
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    message: Mapped["ChatMessageDB"] = relationship("ChatMessageDB")
    audio_file: Mapped["AudioFileDB"] = relationship("AudioFileDB")


# Conversation topics tracking (for better context)
class ConversationTopicDB(UUIDBase):
    """
    Track key topics discussed in conversations for better context retrieval
    """
    __tablename__ = "conversation_topics"
    
    # User association
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    
    # Topic information
    topic_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    topic_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Topic metadata
    first_mentioned: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_mentioned: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    mention_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Topic importance score (calculated)
    importance_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    
    # Related message IDs (for context retrieval)
    related_message_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list, nullable=True
    )
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB")
    
    # Indexes for efficient topic searching
    __table_args__ = (
        Index("idx_user_topic_name", "user_id", "topic_name"),
        Index("idx_user_topic_category", "user_id", "topic_category"),
        Index("idx_topic_importance", "importance_score"),
    )