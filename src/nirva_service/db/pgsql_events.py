"""
Database operations for events table.
Replaces the old journal_files operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import desc, and_, or_
from loguru import logger

from .pgsql_client import SessionLocal
from .pgsql_object import EventDB, UserDB, TranscriptionResultDB
from ..models.prompt import EventAnalysis


def event_to_model(event_db: EventDB, include_transcriptions: bool = True) -> EventAnalysis:
    """Convert EventDB to EventAnalysis model."""
    event = EventAnalysis(
        event_id=event_db.event_id,
        event_title=event_db.event_title,
        event_summary=event_db.event_summary,
        event_story=event_db.event_story,
        event_status=event_db.event_status,
        start_timestamp=event_db.start_timestamp,
        end_timestamp=event_db.end_timestamp,
        last_processed_at=event_db.last_processed_at,
        time_range=event_db.time_range,
        duration_minutes=event_db.duration_minutes,
        location=event_db.location,
        mood_labels=event_db.mood_labels,
        mood_score=event_db.mood_score,
        stress_level=event_db.stress_level,
        energy_level=event_db.energy_level,
        activity_type=event_db.activity_type,
        people_involved=event_db.people_involved,
        interaction_dynamic=event_db.interaction_dynamic,
        inferred_impact_on_user_name=event_db.inferred_impact_on_user_name,
        topic_labels=event_db.topic_labels,
        one_sentence_summary=event_db.one_sentence_summary,
        first_person_narrative=event_db.first_person_narrative,
        action_item=event_db.action_item,
    )
    
    # Include transcriptions if requested
    if include_transcriptions:
        event.transcriptions = get_event_transcriptions(event_db.event_id)
    
    return event


def model_to_event(event: EventAnalysis, username: str, user_id: str) -> dict:
    """Convert EventAnalysis to dict for EventDB creation."""
    return {
        "user_id": user_id,
        "username": username,
        "event_id": event.event_id,
        "event_title": event.event_title,
        "event_summary": event.event_summary or event.one_sentence_summary,
        "event_story": event.event_story or event.first_person_narrative,
        "event_status": event.event_status or "completed",
        "start_timestamp": event.start_timestamp,
        "end_timestamp": event.end_timestamp,
        "last_processed_at": event.last_processed_at,
        "time_range": event.time_range,
        "duration_minutes": event.duration_minutes,
        "location": event.location,
        "mood_labels": event.mood_labels,
        "mood_score": event.mood_score,
        "stress_level": event.stress_level,
        "energy_level": event.energy_level,
        "activity_type": event.activity_type,
        "people_involved": event.people_involved,
        "interaction_dynamic": event.interaction_dynamic,
        "inferred_impact_on_user_name": event.inferred_impact_on_user_name,
        "topic_labels": event.topic_labels,
        "one_sentence_summary": event.one_sentence_summary,
        "first_person_narrative": event.first_person_narrative,
        "action_item": event.action_item,
    }


def get_user_events(username: str) -> List[EventAnalysis]:
    """Get all events for a user (excluding dropped events)."""
    db = SessionLocal()
    try:
        events = db.query(EventDB).filter(
            and_(
                EventDB.username == username,
                EventDB.event_status != "dropped"  # Exclude dropped events
            )
        ).order_by(
            desc(EventDB.start_timestamp)
        ).all()
        return [event_to_model(event) for event in events]
    finally:
        db.close()


def get_event_by_id(event_id: str) -> Optional[EventAnalysis]:
    """Get a specific event by ID."""
    db = SessionLocal()
    try:
        event = db.query(EventDB).filter_by(event_id=event_id).first()
        return event_to_model(event) if event else None
    finally:
        db.close()


def save_events(username: str, events: List[EventAnalysis]) -> int:
    """
    Save or update multiple events for a user.
    Returns number of events saved/updated.
    """
    if not events:
        return 0
    
    db = SessionLocal()
    try:
        # Get user_id
        user = db.query(UserDB).filter_by(username=username).first()
        if not user:
            logger.error(f"User not found: {username}")
            return 0
        
        user_id = str(user.id)
        saved_count = 0
        
        for event in events:
            # Check if event exists
            existing = db.query(EventDB).filter_by(event_id=event.event_id).first()
            
            if existing:
                # Update existing event
                for key, value in model_to_event(event, username, user_id).items():
                    if key not in ["user_id", "username", "event_id"]:  # Don't update IDs
                        setattr(existing, key, value)
                logger.info(f"Updated event {event.event_id} for user {username}")
            else:
                # Create new event
                new_event = EventDB(**model_to_event(event, username, user_id))
                db.add(new_event)
                logger.info(f"Created new event {event.event_id} for user {username}")
            
            saved_count += 1
        
        db.commit()
        logger.info(f"Saved/updated {saved_count} events for user {username}")
        return saved_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving events for {username}: {e}")
        raise
    finally:
        db.close()


def delete_event(event_id: str) -> bool:
    """Delete a specific event."""
    db = SessionLocal()
    try:
        event = db.query(EventDB).filter_by(event_id=event_id).first()
        if event:
            db.delete(event)
            db.commit()
            logger.info(f"Deleted event {event_id}")
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting event {event_id}: {e}")
        return False
    finally:
        db.close()


def delete_user_events(username: str) -> int:
    """Delete all events for a user. Returns count of deleted events."""
    db = SessionLocal()
    try:
        count = db.query(EventDB).filter_by(username=username).delete()
        db.commit()
        logger.info(f"Deleted {count} events for user {username}")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting events for {username}: {e}")
        return 0
    finally:
        db.close()


def get_ongoing_events(username: Optional[str] = None) -> List[EventAnalysis]:
    """
    Get all ongoing events, optionally filtered by username.
    
    Args:
        username: Optional username to filter by
        
    Returns:
        List of ongoing events as EventAnalysis objects
    """
    db = SessionLocal()
    try:
        query = db.query(EventDB).filter(EventDB.event_status == "ongoing")
        
        if username:
            query = query.filter(EventDB.username == username)
            
        events = query.order_by(EventDB.updated_at.desc()).all()
        return [event_to_model(event) for event in events]
    finally:
        db.close()


def get_events_in_range(
    username: str, 
    start_time: datetime, 
    end_time: datetime
) -> List[EventAnalysis]:
    """Get events within a time range (excluding dropped events)."""
    db = SessionLocal()
    try:
        events = db.query(EventDB).filter(
            and_(
                EventDB.username == username,
                EventDB.start_timestamp >= start_time,
                EventDB.start_timestamp <= end_time,
                EventDB.event_status != "dropped"  # Exclude dropped events
            )
        ).order_by(EventDB.start_timestamp).all()
        return [event_to_model(event) for event in events]
    finally:
        db.close()


# Alias for compatibility with mental_state_service
get_user_events_by_date_range = get_events_in_range


def get_event_transcriptions(event_id: str) -> List[Dict[str, Any]]:
    """Get transcriptions that overlap with an event's time range."""
    db = SessionLocal()
    try:
        # Get the event first
        event = db.query(EventDB).filter_by(event_id=event_id).first()
        if not event:
            return []
        
        # Find transcriptions that overlap with the event's time range
        # A transcription overlaps if:
        # - It starts before the event ends AND
        # - It ends after the event starts
        transcriptions = db.query(TranscriptionResultDB).filter(
            and_(
                TranscriptionResultDB.username == event.username,
                TranscriptionResultDB.start_time < event.end_timestamp,
                TranscriptionResultDB.end_time > event.start_timestamp
            )
        ).order_by(TranscriptionResultDB.start_time).all()
        
        # Convert to dictionaries for JSON serialization
        result = []
        for trans in transcriptions:
            # Calculate duration from start/end times
            duration_seconds = (trans.end_time - trans.start_time).total_seconds()
            
            result.append({
                "id": str(trans.id),
                "transcription_text": trans.transcription_text,
                "start_time": trans.start_time.isoformat(),
                "end_time": trans.end_time.isoformat(),
                "duration_seconds": duration_seconds,
                "transcription_service": trans.transcription_service,
                "detected_language": trans.detected_language,
                "created_at": trans.created_at.isoformat()
            })
        
        return result
    finally:
        db.close()