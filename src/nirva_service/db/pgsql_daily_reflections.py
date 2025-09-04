"""
Database operations for daily reflections table.
"""

from typing import Optional
from datetime import datetime
from loguru import logger
import json

from .pgsql_client import SessionLocal
from .pgsql_object import DailyReflectionDB, UserDB
from ..models.prompt import DailyReflection


def get_daily_reflection(username: str, reflection_date: str) -> Optional[DailyReflection]:
    """
    Get a daily reflection for a user on a specific date.
    
    Args:
        username: User's username
        reflection_date: Date string (e.g., "2025-09-04")
        
    Returns:
        DailyReflection model or None
    """
    db = SessionLocal()
    try:
        reflection_db = db.query(DailyReflectionDB).filter_by(
            username=username,
            reflection_date=reflection_date
        ).first()
        
        if reflection_db:
            return DailyReflection.model_validate(reflection_db.reflection_json)
        return None
    finally:
        db.close()


def save_daily_reflection(
    username: str, 
    reflection_date: str, 
    reflection: DailyReflection
) -> bool:
    """
    Save or update a daily reflection.
    
    Args:
        username: User's username
        reflection_date: Date string (e.g., "2025-09-04")
        reflection: DailyReflection model
        
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    try:
        # Get user_id
        user = db.query(UserDB).filter_by(username=username).first()
        if not user:
            logger.error(f"User not found: {username}")
            return False
        
        # Check if reflection exists
        existing = db.query(DailyReflectionDB).filter_by(
            username=username,
            reflection_date=reflection_date
        ).first()
        
        reflection_dict = reflection.model_dump()
        
        if existing:
            # Update existing reflection
            existing.reflection_json = reflection_dict
            logger.info(f"Updated reflection for {username} on {reflection_date}")
        else:
            # Create new reflection
            new_reflection = DailyReflectionDB(
                user_id=user.id,
                username=username,
                reflection_date=reflection_date,
                reflection_json=reflection_dict
            )
            db.add(new_reflection)
            logger.info(f"Created new reflection for {username} on {reflection_date}")
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving reflection for {username}: {e}")
        return False
    finally:
        db.close()


def get_or_create_default_reflection(username: str, reflection_date: str) -> DailyReflection:
    """
    Get existing reflection or create a default one.
    
    Args:
        username: User's username
        reflection_date: Date string
        
    Returns:
        DailyReflection model
    """
    # Try to get existing
    existing = get_daily_reflection(username, reflection_date)
    if existing:
        return existing
    
    # Create default
    from ..models.prompt import (
        DailyReflection, Gratitude, ChallengesAndGrowth,
        LearningAndInsights, ConnectionsAndRelationships, LookingForward
    )
    
    default_reflection = DailyReflection(
        reflection_summary="Daily activities and experiences",
        gratitude=Gratitude(
            gratitude_summary=["Daily experiences"],
            gratitude_details="Grateful for the day's experiences",
            win_summary=["Completed activities"],
            win_details="Successfully navigated the day",
            feel_alive_moments="Moments of connection and activity"
        ),
        challenges_and_growth=ChallengesAndGrowth(
            growth_summary=["Personal development"],
            obstacles_faced="Daily challenges",
            unfinished_intentions="Tasks to complete",
            contributing_factors="Time and circumstances"
        ),
        learning_and_insights=LearningAndInsights(
            new_knowledge="Daily learnings",
            self_discovery="Personal insights",
            insights_about_others="Social observations",
            broader_lessons="Life lessons"
        ),
        connections_and_relationships=ConnectionsAndRelationships(
            meaningful_interactions="Social interactions",
            notable_about_people="People in my life",
            follow_up_needed="Future connections"
        ),
        looking_forward=LookingForward(
            do_differently_tomorrow="Areas for improvement",
            continue_what_worked="Successful practices",
            top_3_priorities_tomorrow=["Priority 1", "Priority 2", "Priority 3"]
        )
    )
    
    # Save the default reflection
    save_daily_reflection(username, reflection_date, default_reflection)
    return default_reflection