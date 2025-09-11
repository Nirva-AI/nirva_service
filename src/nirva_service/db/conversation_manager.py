"""
Conversation Manager - Database utilities for advanced chat system

This module provides high-level database operations for managing conversations,
messages, and context in the advanced Nirva chat system.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
import json

from sqlalchemy import desc, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from loguru import logger

from .pgsql_client import SessionLocal
from .pgsql_conversation import (
    UserConversationDB,
    ChatMessageDB,
    ConversationContextDB,
    MessageRole,
    MessageType,
    VoiceMessageDB,
    ConversationTopicDB
)
from .pgsql_object import UserDB
from ..models.api import ChatMessage, MessageRole as APIMessageRole


class ConversationManager:
    """
    High-level interface for conversation management operations.
    """
    
    def __init__(self):
        pass
    
    def get_or_create_conversation(self, user_id: UUID) -> UserConversationDB:
        """
        Get existing conversation for user or create a new one.
        Each user has exactly one conversation with Nirva.
        """
        with SessionLocal() as db:
            # Try to get existing conversation
            conversation = db.query(UserConversationDB).filter(
                UserConversationDB.user_id == user_id
            ).first()
            
            if conversation:
                return conversation
            
            # Create new conversation
            conversation = UserConversationDB(
                user_id=user_id,
                title="Chat with Nirva",
                total_messages=0,
                personality_settings={},
                conversation_summary=""
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            logger.info(f"Created new conversation for user {user_id}")
            return conversation
    
    def add_message(
        self,
        user_id: UUID,
        role: MessageRole,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        attachments: Optional[List[Dict[str, Any]]] = None,
        message_metadata: Optional[Dict[str, Any]] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[int] = None
    ) -> ChatMessageDB:
        """
        Add a new message to the user's conversation.
        """
        with SessionLocal() as db:
            # Ensure conversation exists in this session
            conversation = db.query(UserConversationDB).filter(
                UserConversationDB.user_id == user_id
            ).first()
            
            if not conversation:
                # Create new conversation in this session
                conversation = UserConversationDB(
                    user_id=user_id,
                    title="Chat with Nirva",
                    total_messages=0,
                    personality_settings={},
                    conversation_summary=""
                )
                db.add(conversation)
                db.flush()  # Ensure it's in the session
            
            # Create new message
            message = ChatMessageDB(
                user_id=user_id,
                role=role,
                content=content,
                message_type=message_type,
                attachments=attachments or [],
                message_metadata=message_metadata or {},
                context_snapshot=context_snapshot or {},
                response_time_ms=response_time_ms
            )
            
            db.add(message)
            
            # Update conversation metadata
            conversation.total_messages += 1
            conversation.last_activity = datetime.now(timezone.utc)
            conversation.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(message)
            
            logger.debug(f"Added {role} message to conversation for user {user_id}")
            return message
    
    def get_conversation_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        message_types: Optional[List[MessageType]] = None
    ) -> Tuple[List[ChatMessageDB], int]:
        """
        Get conversation history for a user with pagination.
        Returns (messages, total_count).
        """
        with SessionLocal() as db:
            query = db.query(ChatMessageDB).filter(
                ChatMessageDB.user_id == user_id
            )
            
            if message_types:
                query = query.filter(ChatMessageDB.message_type.in_(message_types))
            
            # Get total count
            total_count = query.count()
            
            # Get paginated messages (most recent first)
            messages = query.order_by(desc(ChatMessageDB.timestamp)).offset(offset).limit(limit).all()
            
            # Reverse to get chronological order
            messages.reverse()
            
            return messages, total_count
    
    def get_recent_messages(
        self,
        user_id: UUID,
        minutes: int = 60,
        max_messages: int = 20
    ) -> List[ChatMessageDB]:
        """
        Get recent messages within a time window.
        """
        with SessionLocal() as db:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            messages = db.query(ChatMessageDB).filter(
                and_(
                    ChatMessageDB.user_id == user_id,
                    ChatMessageDB.timestamp >= cutoff_time
                )
            ).order_by(ChatMessageDB.timestamp).limit(max_messages).all()
            
            return messages
    
    def update_conversation_context(
        self,
        user_id: UUID,
        mental_state_summary: Optional[Dict[str, Any]] = None,
        recent_events_summary: Optional[Dict[str, Any]] = None,
        conversation_memory: Optional[Dict[str, Any]] = None,
        personality_state: Optional[Dict[str, Any]] = None
    ) -> ConversationContextDB:
        """
        Update or create conversation context for AI awareness.
        """
        with SessionLocal() as db:
            # Try to get existing context
            context = db.query(ConversationContextDB).filter(
                ConversationContextDB.user_id == user_id
            ).first()
            
            if not context:
                # Create new context
                context = ConversationContextDB(
                    user_id=user_id,
                    mental_state_summary={},
                    recent_events_summary={},
                    conversation_memory={},
                    personality_state={}
                )
                db.add(context)
            
            # Update provided fields
            if mental_state_summary is not None:
                context.mental_state_summary = mental_state_summary
            if recent_events_summary is not None:
                context.recent_events_summary = recent_events_summary
            if conversation_memory is not None:
                context.conversation_memory = conversation_memory
            if personality_state is not None:
                context.personality_state = personality_state
            
            context.last_updated = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(context)
            
            return context
    
    def get_conversation_context(self, user_id: UUID) -> Optional[ConversationContextDB]:
        """
        Get current conversation context for a user.
        """
        with SessionLocal() as db:
            return db.query(ConversationContextDB).filter(
                ConversationContextDB.user_id == user_id
            ).first()
    
    def search_messages(
        self,
        user_id: UUID,
        query: str,
        limit: int = 20
    ) -> List[ChatMessageDB]:
        """
        Search messages by content (simple text search for now).
        """
        with SessionLocal() as db:
            messages = db.query(ChatMessageDB).filter(
                and_(
                    ChatMessageDB.user_id == user_id,
                    ChatMessageDB.content.ilike(f"%{query}%")
                )
            ).order_by(desc(ChatMessageDB.timestamp)).limit(limit).all()
            
            return messages
    
    def get_conversation_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get conversation statistics for a user.
        """
        with SessionLocal() as db:
            conversation = db.query(UserConversationDB).filter(
                UserConversationDB.user_id == user_id
            ).first()
            
            if not conversation:
                return {
                    "total_messages": 0,
                    "first_message": None,
                    "last_activity": None,
                    "message_types": {}
                }
            
            # Get message type breakdown
            message_type_stats = db.query(
                ChatMessageDB.message_type,
                func.count(ChatMessageDB.id)
            ).filter(
                ChatMessageDB.user_id == user_id
            ).group_by(ChatMessageDB.message_type).all()
            
            # Get first message timestamp
            first_message = db.query(ChatMessageDB).filter(
                ChatMessageDB.user_id == user_id
            ).order_by(ChatMessageDB.timestamp).first()
            
            return {
                "total_messages": conversation.total_messages,
                "first_message": first_message.timestamp if first_message else None,
                "last_activity": conversation.last_activity,
                "message_types": {msg_type: count for msg_type, count in message_type_stats},
                "created_at": conversation.created_at
            }
    
    def update_conversation_summary(
        self,
        user_id: UUID,
        summary: str
    ) -> None:
        """
        Update the conversation summary for better context.
        """
        with SessionLocal() as db:
            conversation = db.query(UserConversationDB).filter(
                UserConversationDB.user_id == user_id
            ).first()
            
            if conversation:
                conversation.conversation_summary = summary
                conversation.updated_at = datetime.now(timezone.utc)
                db.commit()
                
                logger.debug(f"Updated conversation summary for user {user_id}")
    
    def add_voice_message_metadata(
        self,
        message_id: UUID,
        audio_file_id: Optional[UUID] = None,
        duration_seconds: Optional[float] = None,
        transcription_text: Optional[str] = None,
        transcription_confidence: Optional[float] = None
    ) -> VoiceMessageDB:
        """
        Add voice message metadata for a chat message.
        """
        with SessionLocal() as db:
            voice_message = VoiceMessageDB(
                message_id=message_id,
                audio_file_id=audio_file_id,
                duration_seconds=duration_seconds,
                transcription_text=transcription_text,
                transcription_confidence=transcription_confidence,
                processing_status="completed" if transcription_text else "pending"
            )
            
            db.add(voice_message)
            db.commit()
            db.refresh(voice_message)
            
            return voice_message
    
    def convert_to_api_messages(
        self,
        messages: List[ChatMessageDB]
    ) -> List[ChatMessage]:
        """
        Convert database messages to API message format.
        """
        api_messages = []
        
        for msg in messages:
            # Convert role enum
            if msg.role == MessageRole.SYSTEM:
                api_role = APIMessageRole.SYSTEM
            elif msg.role == MessageRole.HUMAN:
                api_role = APIMessageRole.HUMAN
            elif msg.role == MessageRole.AI:
                api_role = APIMessageRole.AI
            else:
                api_role = APIMessageRole.AI  # Default fallback
            
            api_message = ChatMessage(
                id=str(msg.id),
                role=api_role,
                content=msg.content,
                time_stamp=msg.timestamp.isoformat(),
                tags=msg.message_metadata.get("tags") if msg.message_metadata else None
            )
            
            api_messages.append(api_message)
        
        return api_messages
    
    def cleanup_old_context(self, days: int = 30) -> int:
        """
        Clean up old conversation context to prevent database bloat.
        Returns number of records cleaned up.
        """
        with SessionLocal() as db:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Clean up old context snapshots in messages
            count = db.query(ChatMessageDB).filter(
                ChatMessageDB.timestamp < cutoff_date
            ).update({"context_snapshot": {}})
            
            db.commit()
            
            logger.info(f"Cleaned up context snapshots for {count} messages older than {days} days")
            return count


# Global instance
conversation_manager = ConversationManager()