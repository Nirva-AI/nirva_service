"""
Voice Chat Actions - Voice Message and Call Endpoints

This module implements voice message endpoints that integrate with the enhanced chat system,
supporting both standalone voice messages and real-time voice calls.
"""

import datetime
import uuid
from typing import List, Optional, Dict, Any
from uuid import UUID
import io

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
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
from nirva_service.services.audio_processing.deepgram_service import get_deepgram_service
from nirva_service.services.conversation_context_manager import conversation_context_manager

from .app_service_server import AppserviceServerInstance
from .oauth_user import get_authenticated_user

###################################################################################################################################################################
voice_chat_router = APIRouter()


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


def _build_voice_context_snapshot(
    username: str,
    display_name: str,
    user_id: UUID,
    voice_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build context snapshot for voice messages including mental state and voice analysis.
    """
    current_time = datetime.datetime.now(datetime.timezone.utc)
    context = {
        "username": username,
        "display_name": display_name,
        "timestamp": current_time.isoformat(),
        "mental_state_available": False,
        "recent_events_available": False,
        "voice_message": True,
    }
    
    # Add voice analysis if available
    if voice_analysis:
        context["voice_analysis"] = voice_analysis
    
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


###################################################################################################################################################################
###################################################################################################################################################################
###################################################################################################################################################################
@voice_chat_router.post(path="/voice/message/", response_model=ChatActionResponse)
async def handle_voice_message(
    appservice_server: AppserviceServerInstance,
    authenticated_user: str = Depends(get_authenticated_user),
    audio_file: UploadFile = File(...),
    call_type: str = Form(default="voice_message"),
    call_session_id: Optional[str] = Form(default=None),
) -> ChatActionResponse:
    """
    Handle voice message upload with transcription and AI response.
    
    This endpoint:
    1. Accepts audio file upload
    2. Transcribes audio using Deepgram
    3. Processes with enhanced chat brain (same as text chat)
    4. Returns AI response
    5. Stores both voice message and AI response in conversation
    """
    logger.info(f"/voice/message/: user={authenticated_user}, file={audio_file.filename}, call_type={call_type}")

    try:
        # Validate input
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an audio file",
            )

        # Get user information
        user_id = _get_user_id_from_username(authenticated_user)
        display_name = nirva_service.db.redis_user.get_user_display_name(username=authenticated_user)
        
        if not display_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {authenticated_user} must set a display name before using voice chat",
            )

        # === STEP 1: Transcribe audio ===
        logger.debug(f"Transcribing audio for user {authenticated_user}")
        
        # Read audio file
        audio_content = await audio_file.read()
        
        # Get Deepgram service and transcribe
        deepgram_service = get_deepgram_service()
        transcription_result = await deepgram_service.transcribe_audio(audio_content)
        
        transcription_text = transcription_result.get('transcription', '')
        confidence = transcription_result.get('confidence', 0.0)
        voice_analysis = {
            "sentiment_data": transcription_result.get('sentiment_data'),
            "topics_data": transcription_result.get('topics_data'),
            "intents_data": transcription_result.get('intents_data'),
            "detected_language": transcription_result.get('language', 'en'),
            "confidence": confidence
        }
        
        if not transcription_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not transcribe audio - no speech detected",
            )

        logger.info(f"Transcription: '{transcription_text[:100]}...' (confidence: {confidence:.2f})")

        # === STEP 2: Store voice message ===
        logger.debug(f"Storing voice message for user {authenticated_user}")
        
        # Build context snapshot with voice analysis
        context_snapshot = _build_voice_context_snapshot(
            authenticated_user, 
            display_name, 
            user_id,
            voice_analysis
        )
        
        # Parse call_session_id if provided
        parsed_call_session_id = None
        if call_session_id:
            try:
                parsed_call_session_id = UUID(call_session_id)
            except ValueError:
                logger.warning(f"Invalid call_session_id format: {call_session_id}")

        # Store voice message
        human_message_db, voice_message_db = conversation_manager.add_voice_message(
            user_id=user_id,
            role=DBMessageRole.HUMAN,
            content=transcription_text,
            call_type=call_type,
            call_session_id=parsed_call_session_id,
            duration_seconds=voice_analysis.get('duration_seconds'),
            transcription_text=transcription_text,
            transcription_confidence=confidence,
            real_time_processing=False,
            voice_analysis=voice_analysis,
            message_metadata={
                "original_filename": audio_file.filename,
                "audio_content_type": audio_file.content_type,
                "source": "voice_message_upload"
            },
            context_snapshot=context_snapshot
        )

        # === STEP 3: Get conversation history for AI context ===
        logger.debug(f"Retrieving conversation history for user {authenticated_user}")
        
        # Get recent conversation history
        conversation_messages, total_count = conversation_manager.get_conversation_history(
            user_id=user_id,
            limit=50  # Last 50 messages for context
        )
        
        # Convert to API format for AI processing
        api_messages = conversation_manager.convert_to_api_messages(conversation_messages)
        
        logger.info(f"Using {len(api_messages)} messages from conversation history (total: {total_count})")

        # === STEP 4: Process with AI ===
        logger.debug(f"Processing AI request for voice message")
        
        # === STEP 4.1: Get enhanced context from conversation memory ===
        enhanced_context = conversation_context_manager.get_enhanced_context_for_ai(user_id)
        
        # Merge enhanced context into context snapshot
        context_snapshot.update({
            "conversation_memory": enhanced_context.get("conversation_memory", {}),
            "personality_insights": enhanced_context.get("personality_insights", {}),
            "context_available": enhanced_context.get("context_available", {})
        })
        
        # Build enhanced prompt with voice context
        enhanced_prompt = builtin_prompt.user_session_chat_message(
            username=authenticated_user,
            display_name=display_name,
            content=f"[Voice Message] {transcription_text}",
            date_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        # System message with context awareness
        system_message_content = builtin_prompt.user_session_system_message(
            authenticated_user,
            display_name,
            context_snapshot
        )

        # Assemble conversation history for AI
        from nirva_service.services.app_services.enhanced_chat_actions import _assemble_conversation_history_for_ai
        langchain_messages = _assemble_conversation_history_for_ai(
            api_messages,
            system_message_content,
            max_messages=20  # Limit context to prevent overflow
        )

        # Add current voice message
        from langchain_core.messages import HumanMessage
        langchain_messages.append(HumanMessage(content=enhanced_prompt))

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

        # === STEP 5: Store AI response ===
        logger.debug(f"Storing AI response for user {authenticated_user}")
        
        ai_response_content = request_task.last_response_message_content
        
        ai_message_db = conversation_manager.add_message(
            user_id=user_id,
            role=DBMessageRole.AI,
            content=ai_response_content,
            message_type=DBMessageType.TEXT,
            message_metadata={
                "response_time_ms": response_time_ms,
                "model_used": "gpt-4o-mini",
                "conversation_length": len(langchain_messages),
                "source": "voice_message_response",
                "responding_to_voice": True,
                "voice_message_id": str(voice_message_db.id)
            },
            context_snapshot=context_snapshot,
            response_time_ms=response_time_ms
        )

        # === STEP 6: Update conversation memory (async for performance) ===
        logger.debug(f"Scheduling conversation memory update for user {authenticated_user}")
        
        try:
            # Get the latest messages for context learning (voice message + AI response)
            latest_messages = [
                ChatMessage(
                    id=str(human_message_db.id),
                    role=MessageRole.HUMAN,
                    content=f"[Voice Message] {transcription_text}",
                    time_stamp=human_message_db.timestamp.isoformat()
                ),
                ChatMessage(
                    id=str(ai_message_db.id),
                    role=MessageRole.AI,
                    content=ai_response_content,
                    time_stamp=ai_message_db.timestamp.isoformat()
                )
            ]
            
            # Schedule memory update as background task (don't block response)
            import threading
            def update_memory():
                try:
                    conversation_context_manager.update_conversation_memory(
                        user_id=user_id,
                        new_messages=latest_messages,
                        ai_response=ai_response_content
                    )
                except Exception as e:
                    logger.warning(f"Background memory update failed for {authenticated_user}: {e}")
            
            # Run in background thread to avoid blocking response
            threading.Thread(target=update_memory, daemon=True).start()
            
        except Exception as e:
            logger.warning(f"Failed to schedule conversation memory update for {authenticated_user}: {e}")

        # === STEP 7: Return response ===
        response = ChatActionResponse(
            ai_message=ChatMessage(
                id=str(ai_message_db.id),
                role=MessageRole.AI,
                content=ai_response_content,
                time_stamp=ai_message_db.timestamp.isoformat(),
            ),
        )

        logger.info(f"Voice message completed: user={authenticated_user}, response_time={response_time_ms}ms, voice_msg_id={voice_message_db.id}, ai_msg_id={ai_message_db.id}")
        
        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Voice message processing failed for user {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice message processing failed: {str(e)}",
        )


###################################################################################################################################################################
@voice_chat_router.get(path="/voice/history/")
async def get_voice_conversation_history(
    limit: int = 20,
    offset: int = 0,
    call_type: Optional[str] = None,
    authenticated_user: str = Depends(get_authenticated_user),
):
    """
    Get voice message history for the authenticated user.
    Optionally filter by call_type (voice_message, live_call, call_segment).
    """
    try:
        user_id = _get_user_id_from_username(authenticated_user)
        
        # Get conversation history filtered by voice messages
        from nirva_service.db.pgsql_conversation import MessageType
        messages, total_count = conversation_manager.get_conversation_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            message_types=[MessageType.VOICE]
        )
        
        # TODO: Add call_type filtering if needed
        
        api_messages = conversation_manager.convert_to_api_messages(messages)
        
        return {
            "voice_messages": api_messages,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(messages)) < total_count,
            "call_type_filter": call_type
        }
        
    except Exception as e:
        logger.error(f"Failed to get voice conversation history for {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve voice conversation history: {str(e)}"
        )


###################################################################################################################################################################
@voice_chat_router.get(path="/voice/sessions/")
async def get_voice_call_sessions(
    limit: int = 10,
    authenticated_user: str = Depends(get_authenticated_user),
):
    """
    Get voice call sessions for the authenticated user.
    Groups voice messages by call_session_id.
    """
    try:
        user_id = _get_user_id_from_username(authenticated_user)
        
        # TODO: Implement call session grouping
        # For now, return placeholder
        
        return {
            "call_sessions": [],
            "total_sessions": 0,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get voice call sessions for {authenticated_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve voice call sessions: {str(e)}"
        )