"""
Mental state models for energy and stress tracking.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal, final
from pydantic import BaseModel, Field

from .registry import register_base_model_class


@final
@register_base_model_class
class MentalStatePoint(BaseModel):
    """Single mental state data point."""
    timestamp: datetime = Field(description="Timestamp of the measurement")
    energy_score: float = Field(ge=0, le=100, description="Energy level from 0-100")
    stress_score: float = Field(ge=0, le=100, description="Stress level from 0-100")
    mood_score: float = Field(ge=0, le=100, description="Mood level from 0-100")
    confidence: float = Field(ge=0, le=1, default=0.5, description="Confidence in the scores")
    data_source: Literal["event", "interpolated", "baseline"] = Field(
        description="Source of the data point"
    )
    event_id: Optional[str] = Field(default=None, description="Associated event ID if applicable")


@final
@register_base_model_class
class DailyMentalStateStats(BaseModel):
    """Daily statistics for mental state."""
    avg_energy: float = Field(description="Average energy for the day")
    avg_stress: float = Field(description="Average stress for the day")
    avg_mood: float = Field(description="Average mood for the day")
    peak_energy_time: str = Field(description="Time of peak energy")
    peak_stress_time: str = Field(description="Time of peak stress")
    peak_mood_time: str = Field(description="Time of peak mood")
    optimal_state_minutes: int = Field(description="Minutes spent in optimal state (high energy, low stress)")
    burnout_risk_minutes: int = Field(description="Minutes spent in burnout risk state (low energy, high stress)")
    recovery_periods: int = Field(description="Number of recovery periods detected")


@final
@register_base_model_class
class MentalStatePattern(BaseModel):
    """Detected patterns in mental state."""
    pattern_type: str = Field(description="Type of pattern detected")
    description: str = Field(description="Description of the pattern")
    frequency: str = Field(description="How often this pattern occurs")
    impact: str = Field(description="Impact on overall wellbeing")


@final
@register_base_model_class
class MentalStateInsights(BaseModel):
    """Complete mental state insights for the UI."""
    current_state: MentalStatePoint = Field(description="Current mental state")
    timeline_24h: List[MentalStatePoint] = Field(description="Last 24 hours of data points")
    timeline_7d: List[MentalStatePoint] = Field(description="7 day trend (hourly aggregates)")
    daily_stats: DailyMentalStateStats = Field(description="Today's statistics")
    patterns: List[MentalStatePattern] = Field(description="Detected patterns")
    recommendations: List[str] = Field(description="Personalized recommendations")
    risk_indicators: Dict[str, Any] = Field(description="Risk indicators and warnings")


@final
@register_base_model_class
class TimeAllocationData(BaseModel):
    """Single activity time allocation data."""
    activity_type: str = Field(description="Type of activity")
    total_hours: float = Field(ge=0, description="Total hours spent on this activity")
    percentage: float = Field(ge=0, le=100, description="Percentage of total awake time")
    average_session_duration: float = Field(ge=0, description="Average duration per session in hours")
    session_count: int = Field(ge=0, description="Number of sessions for this activity")


@final
@register_base_model_class
class TimeAllocationInsights(BaseModel):
    """Insights about time allocation patterns."""
    total_awake_hours: float = Field(description="Total tracked awake hours")
    most_active_category: str = Field(description="Activity with most time allocation")
    productivity_score: float = Field(ge=0, le=100, description="Overall productivity score")
    balance_score: float = Field(ge=0, le=100, description="Work-life balance score")
    top_activities: List[TimeAllocationData] = Field(description="Top activities by time spent")
    recommendations: List[str] = Field(description="Personalized time allocation recommendations")


@final
@register_base_model_class
class TimeAllocationTimeline(BaseModel):
    """Time allocation data over different time periods."""
    date: str = Field(description="Date for this timeline data")
    daily_data: List[TimeAllocationData] = Field(description="Daily activity breakdown")
    insights: TimeAllocationInsights = Field(description="Insights for this period")


@final
@register_base_model_class
class TimeAllocationResponse(BaseModel):
    """Complete time allocation response for the UI."""
    current_insights: TimeAllocationInsights = Field(description="Current period insights")
    day_view: List[TimeAllocationData] = Field(description="Today's time allocation data")
    week_view: List[TimeAllocationTimeline] = Field(description="Week timeline data")
    month_view: List[TimeAllocationTimeline] = Field(description="Month timeline data")
    patterns: List[str] = Field(description="Detected time allocation patterns")