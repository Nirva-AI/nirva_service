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