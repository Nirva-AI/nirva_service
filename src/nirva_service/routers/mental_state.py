"""
Mental state API endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..models.mental_state import MentalStateInsights
from ..services.mental_state_service import MentalStateCalculator
from ..dependencies.auth import get_current_user_id

router = APIRouter(prefix="/api/insights", tags=["mental_state"])


@router.get("/mental-state", response_model=MentalStateInsights)
async def get_mental_state_insights(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    timezone: str = Query("UTC", description="User's timezone"),
    username: str = Depends(get_current_user_id)
) -> MentalStateInsights:
    """
    Get complete mental state insights for the UI.
    
    Returns:
    - Current mental state
    - 24-hour timeline (48 points at 30-min intervals)
    - 7-day trend (hourly aggregates)
    - Daily statistics
    - Detected patterns
    - Personalized recommendations
    - Risk indicators
    """
    try:
        # Parse date if provided
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            target_date = datetime.now()
        
        # Get insights
        calculator = MentalStateCalculator()
        insights = calculator.get_mental_state_insights(
            username=username,
            date=target_date,
            timezone_str=timezone
        )
        
        logger.info(f"Generated mental state insights for user {username}")
        return insights
        
    except Exception as e:
        logger.error(f"Error generating mental state insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))