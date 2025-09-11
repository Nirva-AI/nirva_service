"""
Enhanced Chat Actions - Advanced Nirva Chat System

This module implements the enhanced chat endpoints that use persistent conversation storage
and context awareness, replacing the previous stateless chat system.
"""

import datetime
import uuid
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

import nirva_service.db.redis_user
import nirva_service.db.pgsql_user
import nirva_service.prompts.builtin as builtin_prompt
from nirva_service.models import (
    ChatActionRequest,
    ChatActionResponse,
    ChatMessage,
    MessageRole,
)
from nirva_service.services.langgraph_services.langgraph_models import (
    RequestTaskMessageListType,
)
from nirva_service.services.langgraph_services.langgraph_request_task import (
    LanggraphRequestTask,
)
from nirva_service.db.conversation_manager import conversation_manager
from nirva_service.db.pgsql_conversation import (
    MessageRole as DBMessageRole,
    MessageType as DBMessageType,
)
from nirva_service.services.mental_state_service import MentalStateCalculator
from nirva_service.db.pgsql_events import get_events_in_range

from .app_service_server import AppserviceServerInstance
from .oauth_user import get_authenticated_user

###################################################################################################################################################################
enhanced_chat_router = APIRouter()


###################################################################################################################################################################
def _get_user_id_from_username(username: str) -> UUID:
    """
    Get user UUID from username.
    """
    try:
        user = nirva_service.db.pgsql_user.get_user(username)
        return user.id
    except ValueError as e:
        logger.error(f"User not found: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {username}"
        )


def _convert_api_role_to_db_role(api_role: MessageRole) -> DBMessageRole:
    """
    Convert API message role to database message role.
    """
    if api_role == MessageRole.SYSTEM:
        return DBMessageRole.SYSTEM
    elif api_role == MessageRole.HUMAN:
        return DBMessageRole.HUMAN
    elif api_role == MessageRole.AI:
        return DBMessageRole.AI
    else:
        raise ValueError(f"Unknown message role: {api_role}")


def _build_context_snapshot(
    username: str,
    display_name: str,
    user_id: UUID
) -> Dict[str, Any]:
    """
    Build context snapshot for the message including mental state and recent events.
    """
    current_time = datetime.datetime.now(datetime.timezone.utc)
    context = {
        "username": username,
        "display_name": display_name,
        "timestamp": current_time.isoformat(),
        "mental_state_available": False,
        "recent_events_available": False,
    }
    
    try:
        # Get current mental state
        calculator = MentalStateCalculator()
        
        # Get the latest mental state point (last 2 hours)
        start_time = current_time - datetime.timedelta(hours=2)
        timeline = calculator.calculate_timeline(
            username=username,
            start_time=start_time,
            interval_minutes=30,
            end_time=current_time
        )
        
        if timeline:
            # Get the most recent mental state
            latest_state = timeline[-1]
            context.update({
                "mental_state_available": True,
                "current_energy": latest_state.energy_score,
                "current_stress": latest_state.stress_score,
                "mental_state_confidence": latest_state.confidence,
                "mental_state_source": latest_state.data_source,
                "mental_state_timestamp": latest_state.timestamp.isoformat(),
            })
            
            logger.debug(f"Mental state for {username}: energy={latest_state.energy_score}, stress={latest_state.stress_score}")
        
    except Exception as e:
        logger.warning(f"Failed to get mental state for {username}: {e}")
    
    try:
        # Get recent events (last 24 hours)
        end_time = current_time
        start_time = current_time - datetime.timedelta(hours=24)
        
        recent_events = get_events_in_range(
            username=username,
            start_time=start_time,
            end_time=end_time
        )
        
        if recent_events:
            context.update({
                "recent_events_available": True,
                "recent_events_count": len(recent_events),
                "recent_events": [
                    {
                        "event_type": event.activity_type,
                        "description": event.one_sentence_summary or event.event_summary,
                        "energy_level": event.energy_level,
                        "stress_level": event.stress_level,
                        "timestamp": event.start_timestamp.isoformat() if event.start_timestamp else None,
                    }
                    for event in recent_events[:5]  # Limit to 5 most recent
                ]
            })
            
            logger.debug(f"Found {len(recent_events)} recent events for {username}")
        
    except Exception as e:
        logger.warning(f"Failed to get recent events for {username}: {e}")
    
    return context


def _assemble_conversation_history_for_ai(
    conversation_history: List[ChatMessage],
    system_message_content: str,
    max_messages: int = 20
) -> RequestTaskMessageListType:
    """
    Assemble conversation history for AI processing.
    Takes recent messages and adds system message.
    """
    ret_messages: RequestTaskMessageListType = []
    
    # Add system message first
    ret_messages.append(SystemMessage(content=system_message_content))
    
    # Add recent conversation history (limit to avoid context overflow)
    recent_messages = conversation_history[-max_messages:] if len(conversation_history) > max_messages else conversation_history
    
    for msg in recent_messages:
        if msg.role == MessageRole.SYSTEM:
            # Skip additional system messages to avoid duplicates
            continue
        elif msg.role == MessageRole.HUMAN:
            ret_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.AI:
            ret_messages.append(AIMessage(content=msg.content))

    return ret_messages


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@enhanced_chat_router.post(path="/action/chat/v2/", response_model=ChatActionResponse)
async def handle_enhanced_chat_action(
    request_data: ChatActionRequest,
    appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
) -> ChatActionResponse:
    """
    Enhanced chat endpoint with persistent conversation storage and context awareness.
    
    This replaces the v1 chat endpoint with:
    - Persistent conversation storage (single conversation per user)
    - Server-side conversation history management
    - Context awareness (mental state, recent events)
    - Improved error handling and logging
    """
    logger.info(f"/action/chat/v2/: user={authenticated_user}, content_length={len(request_data.human_message.content)}")

    try:
        # Validate input
        if len(request_data.human_message.content.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content cannot be empty",
            )

        # Get user information
        user_id = _get_user_id_from_username(authenticated_user)
        display_name = nirva_service.db.redis_user.get_user_display_name(username=authenticated_user)
        
        if not display_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {authenticated_user} must set a display name before chatting",
            )

        # === STEP 1: Store the human message in persistent storage ===
        logger.debug(f"Storing human message for user {authenticated_user}")
        
        context_snapshot = _build_context_snapshot(authenticated_user, display_name, user_id)
        
        human_message_db = conversation_manager.add_message(
            user_id=user_id,
            role=DBMessageRole.HUMAN,
            content=request_data.human_message.content,
            message_type=DBMessageType.TEXT,
            message_metadata={
                "client_id": request_data.human_message.id,
                "client_timestamp": request_data.human_message.time_stamp,
                "source": "mobile_app"
            },
            context_snapshot=context_snapshot
        )

        # === STEP 2: Get conversation history for AI context ===
        logger.debug(f"Retrieving conversation history for user {authenticated_user}")
        
        # Get recent conversation history (we ignore client-provided history in favor of server truth)
        conversation_messages, total_count = conversation_manager.get_conversation_history(
            user_id=user_id,
            limit=50  # Last 50 messages for context
        )
        
        # Convert to API format for AI processing
        api_messages = conversation_manager.convert_to_api_messages(conversation_messages)
        
        logger.info(f"Using {len(api_messages)} messages from conversation history (total: {total_count})")

        # === STEP 3: Prepare AI request ===
        
        # Build enhanced prompt with user context
        enhanced_prompt = builtin_prompt.user_session_chat_message(
            username=authenticated_user,
            display_name=display_name,
            content=request_data.human_message.content,
            date_time=request_data.human_message.time_stamp,
        )

        # System message with context awareness
        system_message_content = builtin_prompt.user_session_system_message(
            authenticated_user,
            display_name,
            context_snapshot
        )

        # Assemble conversation history for AI
        langchain_messages = _assemble_conversation_history_for_ai(
            api_messages,
            system_message_content,
            max_messages=20  # Limit context to prevent overflow
        )

        # Add current user message
        langchain_messages.append(HumanMessage(content=enhanced_prompt))

        # === STEP 4: Process with AI ===
        logger.debug(f"Processing AI request with {len(langchain_messages)} messages")
        
        request_start_time = datetime.datetime.now(datetime.timezone.utc)
        
        request_task = LanggraphRequestTask(
            username=authenticated_user,
            prompt=enhanced_prompt,
            chat_history=langchain_messages,
        )

        # Process the request
        appservice_server.langgraph_service.chat(request_handlers=[request_task])
        
        if len(request_task._response.messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI did not generate a response",
            )

        # Validate AI response
        if request_task._response.messages[-1].type != "ai":
            logger.error(f"Last message is not AI: {request_task._response.messages[-1]}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid AI response format",
            )

        # Calculate response time
        response_time_ms = int((datetime.datetime.now(datetime.timezone.utc) - request_start_time).total_seconds() * 1000)

        # === STEP 5: Store AI response in persistent storage ===
        logger.debug(f"Storing AI response for user {authenticated_user}")
        
        ai_response_content = request_task.last_response_message_content
        
        ai_message_db = conversation_manager.add_message(
            user_id=user_id,
            role=DBMessageRole.AI,
            content=ai_response_content,
            message_type=DBMessageType.TEXT,
            message_metadata={
                "response_time_ms": response_time_ms,
                "model_used": "gpt-4o-mini",  # TODO: Get from actual request
                "conversation_length": len(langchain_messages),
                "source": "enhanced_chat_v2"
            },
            context_snapshot=context_snapshot,
            response_time_ms=response_time_ms
        )

        # === STEP 6: Log conversation for debugging ===
        if logger.level("DEBUG").no >= logger._core.min_level:
            logger.debug("Full conversation context:")
            for i, msg in enumerate(langchain_messages[-5:]):  # Last 5 messages for context
                logger.debug(f"  [{i}] {msg.__class__.__name__}: {msg.content[:100]}...")

        # === STEP 7: Return response ===
        response = ChatActionResponse(
            ai_message=ChatMessage(
                id=str(ai_message_db.id),
                role=MessageRole.AI,
                content=ai_response_content,
                time_stamp=ai_message_db.timestamp.isoformat(),
            ),
        )

        logger.info(f"Chat completed: user={authenticated_user}, response_time={response_time_ms}ms, human_msg_id={human_message_db.id}, ai_msg_id={ai_message_db.id}")
        
        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Chat request failed for user {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}",
        )


###################################################################################################################################################################
# Additional endpoints for conversation management
###################################################################################################################################################################

@enhanced_chat_router.get(path="/conversation/history/")
async def get_conversation_history(
    limit: int = 50,
    offset: int = 0,
    authenticated_user: str = Depends(get_authenticated_user),
):
    """
    Get conversation history for the authenticated user.
    """
    try:
        user_id = _get_user_id_from_username(authenticated_user)
        
        messages, total_count = conversation_manager.get_conversation_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        api_messages = conversation_manager.convert_to_api_messages(messages)
        
        return {
            "messages": api_messages,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(messages)) < total_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get conversation history for {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@enhanced_chat_router.get(path="/conversation/stats/")
async def get_conversation_stats(
    authenticated_user: str = Depends(get_authenticated_user),
):
    """
    Get conversation statistics for the authenticated user.
    """
    try:
        user_id = _get_user_id_from_username(authenticated_user)
        stats = conversation_manager.get_conversation_stats(user_id)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get conversation stats for {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation statistics: {str(e)}"
        )


@enhanced_chat_router.post(path="/conversation/search/")
async def search_conversation(
    query: str,
    limit: int = 20,
    authenticated_user: str = Depends(get_authenticated_user),
):
    """
    Search conversation history for the authenticated user.
    """
    try:
        if len(query.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query cannot be empty"
            )
            
        user_id = _get_user_id_from_username(authenticated_user)
        
        messages = conversation_manager.search_messages(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        api_messages = conversation_manager.convert_to_api_messages(messages)
        
        return {
            "messages": api_messages,
            "query": query,
            "result_count": len(api_messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search conversation for {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search conversation: {str(e)}"
        )