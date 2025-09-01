"""
Transcription query endpoint for client applications.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from pydantic import BaseModel
from loguru import logger
from sqlalchemy.orm import joinedload

from ...db.pgsql_client import SessionLocal
from ...db.pgsql_object import TranscriptionResultDB, AudioFileDB, AudioBatchDB
from ...utils.username_hash import hash_username
from .oauth_user import get_authenticated_user

# Create router
transcription_router = APIRouter(
    prefix="/api/v1",
    tags=["transcription"]
)


class TranscriptionItem(BaseModel):
    """Single transcription item response."""
    id: Optional[str] = None  # UUID as string
    text: str
    start_time: datetime
    end_time: datetime


class TranscriptionListResponse(BaseModel):
    """Paginated transcription list response."""
    transcriptions: List[TranscriptionItem]
    total: int
    page: int
    page_size: int
    has_more: bool


@transcription_router.get("/transcriptions", response_model=TranscriptionListResponse)
async def get_transcriptions(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    start_date: Optional[datetime] = Query(None, description="Filter transcriptions after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter transcriptions before this date"),
    current_user: str = Depends(get_authenticated_user)
) -> TranscriptionListResponse:
    """
    Get paginated transcription results for the current user.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (default 50, max 100)
        start_date: Optional filter for transcriptions after this date
        end_date: Optional filter for transcriptions before this date
        current_user: Authenticated user from token
    
    Returns:
        Paginated list of transcriptions with text and timestamps
    """
    try:
        db = SessionLocal()
        
        # Check if we should use hashed or unhashed username
        # For now, check both to handle legacy data
        username = current_user  # current_user is already the username string
        username_hash = hash_username(username)
        
        # First check if there are any records with the unhashed username
        unhashed_count = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.username == username
        ).count()
        
        # Use whichever format has data
        if unhashed_count > 0:
            # Use unhashed username (legacy data)
            query = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.username == username
            )
            logger.debug(f"Using unhashed username for query: {username}")
        else:
            # Use hashed username (new format)
            query = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.username == username_hash
            )
            logger.debug(f"Using hashed username for query: {username_hash}")
        
        # Apply date filters if provided
        if start_date:
            query = query.filter(TranscriptionResultDB.start_time >= start_date)
        if end_date:
            query = query.filter(TranscriptionResultDB.end_time <= end_date)
        
        # Order by start time descending (most recent first)
        query = query.order_by(TranscriptionResultDB.start_time.desc())
        
        # Get total count
        total_count = query.count()
        
        # Calculate pagination
        offset = (page - 1) * page_size
        
        # Get paginated results
        transcriptions = query.offset(offset).limit(page_size).all()
        
        # Convert to response format
        items = [
            TranscriptionItem(
                id=str(t.id),
                text=t.transcription_text,
                start_time=t.start_time,
                end_time=t.end_time
            )
            for t in transcriptions
        ]
        
        # Calculate if there are more pages
        has_more = (offset + len(transcriptions)) < total_count
        
        logger.info(
            f"Returned {len(items)} transcriptions for user {username}, "
            f"page {page}/{(total_count + page_size - 1) // page_size}"
        )
        
        return TranscriptionListResponse(
            transcriptions=items,
            total=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error fetching transcriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transcriptions")
    finally:
        db.close()


@transcription_router.get("/transcriptions/latest", response_model=TranscriptionItem)
async def get_latest_transcription(
    current_user: str = Depends(get_authenticated_user)
) -> TranscriptionItem:
    """
    Get the most recent transcription for the current user.
    
    Args:
        current_user: Authenticated user from token
    
    Returns:
        Most recent transcription with text and timestamps
    """
    try:
        db = SessionLocal()
        
        username = current_user  # current_user is already the username string
        username_hash = hash_username(username)
        
        # Check for unhashed username first (legacy data)
        unhashed_latest = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.username == username
        ).first()
        
        if unhashed_latest:
            # Use unhashed username query
            latest = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.username == username
            ).order_by(
                TranscriptionResultDB.start_time.desc()
            ).first()
        else:
            # Use hashed username query
            latest = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.username == username_hash
            ).order_by(
                TranscriptionResultDB.start_time.desc()
            ).first()
        
        if not latest:
            raise HTTPException(status_code=404, detail="No transcriptions found")
        
        logger.info(f"Returned latest transcription for user {username}")
        
        return TranscriptionItem(
            text=latest.transcription_text,
            start_time=latest.start_time,
            end_time=latest.end_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest transcription")
    finally:
        db.close()


@transcription_router.get("/transcriptions/count")
async def get_transcription_count(
    current_user: str = Depends(get_authenticated_user)
) -> dict:
    """
    Get the total count of transcriptions for the current user.
    
    Args:
        current_user: Authenticated user from token
    
    Returns:
        Dictionary with total count
    """
    try:
        db = SessionLocal()
        
        username = current_user  # current_user is already the username string
        username_hash = hash_username(username)
        
        # Check both formats
        unhashed_count = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.username == username
        ).count()
        
        hashed_count = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.username == username_hash
        ).count()
        
        count = unhashed_count if unhashed_count > 0 else hashed_count
        
        logger.info(f"User {username} has {count} transcriptions")
        
        return {"count": count}
        
    except Exception as e:
        logger.error(f"Error counting transcriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to count transcriptions")
    finally:
        db.close()


@transcription_router.get("/transcriptions/{transcription_id}/details")
async def get_transcription_details(
    transcription_id: str = Path(..., description="Transcription ID"),
    current_user: str = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific transcription.
    
    Args:
        transcription_id: UUID of the transcription
        current_user: Authenticated user from token
    
    Returns:
        Detailed transcription data including Deepgram analysis results
    """
    try:
        db = SessionLocal()
        
        username = current_user
        username_hash = hash_username(username)
        
        # Parse UUID
        try:
            trans_uuid = UUID(transcription_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid transcription ID format")
        
        # Try unhashed username first (legacy)
        transcription = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.id == trans_uuid,
            TranscriptionResultDB.username == username
        ).first()
        
        # If not found, try hashed username
        if not transcription:
            transcription = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.id == trans_uuid,
                TranscriptionResultDB.username == username_hash
            ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        # Get associated audio files if batch_id exists
        audio_files = []
        if transcription.batch_id:
            audio_files_db = db.query(AudioFileDB).filter(
                AudioFileDB.batch_id == transcription.batch_id
            ).all()
            
            audio_files = [
                {
                    "id": str(af.id),
                    "s3_key": af.s3_key,
                    "file_size": af.file_size,
                    "duration_seconds": af.duration_seconds,
                    "format": af.format,
                    "num_speech_segments": af.num_speech_segments,
                    "total_speech_duration": af.total_speech_duration,
                    "speech_ratio": af.speech_ratio,
                    "status": af.status,
                    "uploaded_at": af.uploaded_at.isoformat() if af.uploaded_at else None,
                    "processed_at": af.processed_at.isoformat() if af.processed_at else None,
                }
                for af in audio_files_db
            ]
        
        # Build response with all available fields
        response = {
            "id": str(transcription.id),
            "text": transcription.transcription_text,
            "start_time": transcription.start_time.isoformat(),
            "end_time": transcription.end_time.isoformat(),
            "transcription_confidence": transcription.transcription_confidence,
            "transcription_service": transcription.transcription_service,
            "detected_language": transcription.detected_language if hasattr(transcription, 'detected_language') else None,
            "batch_id": str(transcription.batch_id) if transcription.batch_id else None,
            "num_segments": transcription.num_segments,
            "created_at": transcription.created_at.isoformat(),
            "audio_files": audio_files,
        }
        
        # Add new Deepgram fields if they exist
        if hasattr(transcription, 'sentiment_data'):
            response["sentiment_data"] = transcription.sentiment_data
        if hasattr(transcription, 'topics_data'):
            response["topics_data"] = transcription.topics_data
        if hasattr(transcription, 'intents_data'):
            response["intents_data"] = transcription.intents_data
        if hasattr(transcription, 'raw_response'):
            response["raw_response"] = transcription.raw_response
        
        logger.info(f"Returned detailed transcription {transcription_id} for user {username}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transcription details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch transcription details")
    finally:
        db.close()