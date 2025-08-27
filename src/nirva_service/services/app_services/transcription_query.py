"""
Transcription query endpoint for client applications.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from loguru import logger

from ...db.pgsql_client import SessionLocal
from ...db.pgsql_object import TranscriptionResultDB
from ...utils.username_hash import hash_username
from .oauth_user import get_authenticated_user

# Create router
transcription_router = APIRouter(
    prefix="/api/v1",
    tags=["transcription"]
)


class TranscriptionItem(BaseModel):
    """Single transcription item response."""
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
        
        # Hash the username to match what's stored in the database
        # The audio processor stores hashed usernames from S3 paths
        username = current_user  # current_user is already the username string
        username_hash = hash_username(username)
        
        # Base query - filter by hashed username
        query = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.username == username_hash
        )
        
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
        
        # Get the most recent transcription
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
        
        count = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.username == username_hash
        ).count()
        
        logger.info(f"User {username} has {count} transcriptions")
        
        return {"count": count}
        
    except Exception as e:
        logger.error(f"Error counting transcriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to count transcriptions")
    finally:
        db.close()