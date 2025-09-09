"""
Mental state calculation service for energy and stress tracking.
"""
import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from statistics import mean
import pytz
from loguru import logger

from ..models.mental_state import (
    MentalStatePoint,
    MentalStateInsights,
    DailyMentalStateStats,
    MentalStatePattern
)
from ..models.prompt import EventAnalysis
from ..db.pgsql_events import get_user_events_by_date_range
from ..db.pgsql_object import MentalStateScoreDB, UserDB
from ..db.pgsql_client import SessionLocal
from ..db.redis_user_context import get_user_context


class MentalStateCalculator:
    """Calculate mental state scores with layered approach."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    def calculate_timeline(
        self, 
        username: str, 
        start_time: datetime,
        interval_minutes: int = 30,
        end_time: Optional[datetime] = None
    ) -> List[MentalStatePoint]:
        """Generate mental state points from start_time to end_time (or now)."""
        points = []
        current_time = start_time
        
        # Default end_time is now if not specified
        if end_time is None:
            end_time = datetime.now(start_time.tzinfo or timezone.utc)
        
        # Don't generate future data
        now = datetime.now(end_time.tzinfo or timezone.utc)
        if end_time > now:
            end_time = now
        
        while current_time <= end_time:
            point = self.calculate_point(username, current_time)
            points.append(point)
            current_time += timedelta(minutes=interval_minutes)
        
        return points
    
    def calculate_point(
        self,
        username: str,
        timestamp: datetime
    ) -> MentalStatePoint:
        """
        Calculate a single mental state point using three-layer approach:
        1. Natural baseline (circadian + weekly patterns)
        2. Event modifications (direct and lingering effects)
        3. Personal adjustments (learned from user's history)
        """
        # Layer 1: Natural baseline
        base_energy, base_stress = self.get_natural_baseline(timestamp)
        
        # Layer 2: Event impacts
        energy_delta, stress_delta, event_id = self.calculate_event_impacts(
            username, timestamp
        )
        
        # Layer 3: Personal patterns (calculated from historical data)
        personal_adj = self.get_personal_adjustment(username, timestamp)
        
        # Combine layers
        final_energy = base_energy + energy_delta + personal_adj['energy']
        final_stress = base_stress + stress_delta + personal_adj['stress']
        
        # Apply interaction effects
        final_energy, final_stress = self.apply_interaction_effects(
            final_energy, final_stress
        )
        
        # Clamp values to valid range
        final_energy = max(0, min(10, final_energy))
        final_stress = max(0, min(10, final_stress))
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            has_event=event_id is not None,
            time_since_event=self._get_time_since_last_event(username, timestamp)
        )
        
        # Determine data source
        if event_id:
            data_source = "event"
        elif abs(energy_delta) > 0.1 or abs(stress_delta) > 0.1:
            data_source = "interpolated"
        else:
            data_source = "baseline"
        
        return MentalStatePoint(
            timestamp=timestamp,
            energy_score=round(final_energy, 1),
            stress_score=round(final_stress, 1),
            confidence=round(confidence, 2),
            data_source=data_source,
            event_id=event_id
        )
    
    def get_natural_baseline(self, timestamp: datetime) -> Tuple[float, float]:
        """Get universal human energy and stress patterns."""
        hour = timestamp.hour + timestamp.minute / 60.0  # Decimal hour
        day_of_week = timestamp.weekday()
        
        # Circadian rhythm for energy (smoother curve)
        energy_curve = {
            0: 3.0,   # Midnight
            3: 2.5,   # Deep sleep
            6: 4.0,   # Wake up
            9: 6.5,   # Morning rise
            11: 7.5,  # Peak morning
            13: 6.0,  # Lunch time
            14: 5.5,  # Post-lunch dip
            16: 6.5,  # Afternoon recovery
            18: 6.0,  # Early evening
            20: 5.0,  # Evening
            21: 4.5,  # Wind down
            23: 3.5   # Prepare for sleep
        }
        
        # Daily stress pattern
        stress_curve = {
            0: 1.5,   # Midnight
            3: 1.0,   # Deep sleep
            6: 2.0,   # Wake up
            9: 4.0,   # Work start
            12: 5.0,  # Midday pressure
            15: 5.5,  # Afternoon peak
            18: 4.0,  # Evening relief
            21: 2.5,  # Relaxation
            23: 1.8   # Prepare for sleep
        }
        
        # Interpolate for exact hour
        base_energy = self._interpolate_curve(energy_curve, hour)
        base_stress = self._interpolate_curve(stress_curve, hour)
        
        # Weekend adjustment
        if day_of_week >= 5:  # Saturday = 5, Sunday = 6
            base_stress *= 0.7  # 30% less stress
            base_energy *= 1.1  # 10% more energy
        
        return base_energy, base_stress
    
    def calculate_event_impacts(
        self, 
        username: str, 
        timestamp: datetime
    ) -> Tuple[float, float, Optional[str]]:
        """Calculate how events affect mental state."""
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        # Get events within influence window (±6 hours)
        start_window = timestamp - timedelta(hours=6)
        end_window = timestamp + timedelta(hours=6)
        
        events = get_user_events_by_date_range(
            username=username,
            start_time=start_window,
            end_time=end_window
        )
        
        energy_delta = 0.0
        stress_delta = 0.0
        current_event_id = None
        
        for event in events:
            if not event.start_timestamp or not event.end_timestamp:
                continue
                
            # Direct impact if during event
            if event.start_timestamp <= timestamp <= event.end_timestamp:
                current_event_id = event.event_id
                # Use actual event scores as deltas from neutral
                energy_delta = (event.energy_level - 5.5)
                stress_delta = (event.stress_level - 5.0)
            
            # Lingering effects after event
            elif event.end_timestamp < timestamp:
                hours_passed = (timestamp - event.end_timestamp).total_seconds() / 3600
                
                # Exponential decay of impact
                decay_factor = math.exp(-0.5 * hours_passed)  # 50% after ~1.4 hours
                
                energy_impact = (event.energy_level - 5.5) * decay_factor
                stress_impact = (event.stress_level - 5.0) * decay_factor
                
                # Stress lingers longer than energy changes
                energy_delta += energy_impact
                stress_delta += stress_impact * 1.3  # Stress decays 30% slower
            
            # Anticipation effects (upcoming events)
            elif event.start_timestamp > timestamp:
                hours_until = (event.start_timestamp - timestamp).total_seconds() / 3600
                if hours_until <= 1:
                    # Anticipation affects stress more than energy
                    if event.activity_type == 'work':
                        stress_delta += 0.5
                    elif event.activity_type == 'social':
                        energy_delta += 0.3
                        if event.interaction_dynamic == 'tense':
                            stress_delta += 0.4
        
        return energy_delta, stress_delta, current_event_id
    
    def get_personal_adjustment(
        self, 
        username: str, 
        timestamp: datetime
    ) -> Dict[str, float]:
        """Calculate personal patterns from historical data."""
        # Get similar times from past 30 days
        historical_points = self._get_historical_similar_times(
            username,
            timestamp.hour,
            'weekday' if timestamp.weekday() < 5 else 'weekend'
        )
        
        if len(historical_points) < 3:  # Need minimum data
            return {'energy': 0, 'stress': 0}
        
        # Calculate how this user differs from baseline
        avg_energy = mean([p.energy_score for p in historical_points])
        avg_stress = mean([p.stress_score for p in historical_points])
        
        expected_energy, expected_stress = self.get_natural_baseline(timestamp)
        
        # Personal deviation from normal patterns (30% weight)
        energy_adjustment = (avg_energy - expected_energy) * 0.3
        stress_adjustment = (avg_stress - expected_stress) * 0.3
        
        return {
            'energy': energy_adjustment,
            'stress': stress_adjustment
        }
    
    def apply_interaction_effects(
        self, 
        energy: float, 
        stress: float
    ) -> Tuple[float, float]:
        """Apply feedback loops between energy and stress."""
        # High stress drains energy
        if stress > 7:
            energy_drain = (stress - 7) * 0.3
            energy -= energy_drain
        
        # Very low energy increases stress vulnerability
        if energy < 3:
            stress_increase = (3 - energy) * 0.2
            stress += stress_increase
        
        # Optimal zone boost (high energy, low stress)
        if energy > 7 and stress < 3:
            energy *= 1.1  # 10% boost
            stress *= 0.9  # 10% reduction
        
        # Danger zone spiral (low energy, high stress)
        if energy < 3 and stress > 7:
            energy *= 0.9  # 10% worse
            stress *= 1.1  # 10% worse
        
        return energy, stress
    
    def calculate_confidence(
        self, 
        has_event: bool, 
        time_since_event: Optional[float]
    ) -> float:
        """Calculate confidence in the mental state scores."""
        if has_event:
            return 0.95  # Very high confidence during events
        
        if time_since_event is not None:
            if time_since_event < 0.5:  # Within 30 minutes
                return 0.85
            elif time_since_event < 2:  # Within 2 hours
                return 0.70
            elif time_since_event < 4:  # Within 4 hours
                return 0.50
        
        return 0.30  # Low confidence for pure baseline
    
    def get_mental_state_insights(
        self,
        username: str,
        date: Optional[datetime] = None,
        timezone_str: str = "UTC"
    ) -> MentalStateInsights:
        """Get complete mental state insights for the UI."""
        # Get user's timezone from Redis if not provided or is default
        if timezone_str == "UTC":
            context = get_user_context(username)
            if context and context.get('timezone'):
                timezone_str = context['timezone']
                logger.info(f"Using timezone from Redis for {username}: {timezone_str}")
        
        # Convert timezone string to timezone object
        try:
            tz = pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {timezone_str}, using UTC")
            tz = pytz.UTC
        
        # Get current time in user's timezone
        now = datetime.now(tz)
        
        # Generate timeline for LAST 24 hours from now (not yesterday!)
        start_time = now - timedelta(hours=24)
        timeline_24h = self.calculate_timeline(
            username, 
            start_time,
            interval_minutes=30,
            end_time=now  # Stop at current time
        )
        
        # Get 7-day trend (but stop at current time)
        timeline_7d = self._get_weekly_trend(username, now)
        
        # Calculate daily stats for today's data
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_points = [p for p in timeline_24h if p.timestamp >= today_start]
        daily_stats = self._calculate_daily_stats(today_points) if today_points else self._get_default_daily_stats()
        
        # Current state is the most recent calculated point (now)
        current_state = self.calculate_point(username, now)
        
        # Generate recommendations based on recent data
        recent_points = timeline_24h[-10:] if len(timeline_24h) >= 10 else timeline_24h
        recommendations = self._generate_recommendations(
            current_state,
            recent_points,
            patterns=self._detect_patterns(timeline_7d)
        )
        
        # Assess risks
        risk_indicators = self._assess_risks(timeline_24h)
        
        return MentalStateInsights(
            current_state=current_state,
            timeline_24h=timeline_24h,
            timeline_7d=timeline_7d,
            daily_stats=daily_stats,
            patterns=self._detect_patterns(timeline_7d),
            recommendations=recommendations,
            risk_indicators=risk_indicators
        )
    
    # Helper methods
    def _interpolate_curve(self, curve: Dict[int, float], hour: float) -> float:
        """Linear interpolation between curve points."""
        sorted_hours = sorted(curve.keys())
        
        # Find surrounding points
        prev_hour = max([h for h in sorted_hours if h <= hour], default=sorted_hours[-1] - 24)
        next_hour = min([h for h in sorted_hours if h > hour], default=sorted_hours[0] + 24)
        
        # Handle wraparound
        if prev_hour > hour:
            prev_hour -= 24
        if next_hour < hour:
            next_hour += 24
        
        # Get values
        prev_val = curve[prev_hour % 24]
        next_val = curve[next_hour % 24]
        
        # Interpolate
        if next_hour == prev_hour:
            return prev_val
        
        alpha = (hour - prev_hour) / (next_hour - prev_hour)
        return prev_val + alpha * (next_val - prev_val)
    
    def _get_time_since_last_event(
        self, 
        username: str, 
        timestamp: datetime
    ) -> Optional[float]:
        """Get hours since the last event ended."""
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            
        events = get_user_events_by_date_range(
            username=username,
            start_time=timestamp - timedelta(days=1),
            end_time=timestamp
        )
        
        last_event_end = None
        for event in events:
            if event.end_timestamp and event.end_timestamp < timestamp:
                if last_event_end is None or event.end_timestamp > last_event_end:
                    last_event_end = event.end_timestamp
        
        if last_event_end:
            return (timestamp - last_event_end).total_seconds() / 3600
        
        return None
    
    def _get_historical_similar_times(
        self,
        username: str,
        hour: int,
        day_type: str
    ) -> List[MentalStatePoint]:
        """Get historical mental state points for similar times."""
        # Query database for historical points
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Get user UUID from username for database query
        from ..db.pgsql_object import UserDB
        user = self.session.query(UserDB).filter(
            UserDB.username == username
        ).first()
        if not user:
            return []
        
        points = self.session.query(MentalStateScoreDB).filter(
            MentalStateScoreDB.user_id == user.id,
            MentalStateScoreDB.timestamp >= thirty_days_ago,
        ).all()
        
        # Filter for similar hour and day type
        similar_points = []
        for point in points:
            point_hour = point.timestamp.hour
            point_day_type = 'weekday' if point.timestamp.weekday() < 5 else 'weekend'
            
            if abs(point_hour - hour) <= 1 and point_day_type == day_type:
                similar_points.append(MentalStatePoint(
                    timestamp=point.timestamp,
                    energy_score=point.energy_score,
                    stress_score=point.stress_score,
                    confidence=point.confidence,
                    data_source=point.data_source,
                    event_id=point.event_id
                ))
        
        return similar_points
    
    def _get_weekly_trend(
        self, 
        username: str, 
        end_date: datetime
    ) -> List[MentalStatePoint]:
        """Get hourly aggregated points for the past week, stopping at current time."""
        points = []
        start_date = end_date - timedelta(days=7)
        current = start_date
        
        # Don't generate future data
        now = datetime.now(end_date.tzinfo or timezone.utc)
        actual_end = min(end_date, now)
        
        while current <= actual_end:
            # Calculate hourly point instead of every 30 min for performance
            point = self.calculate_point(username, current)
            points.append(point)
            current += timedelta(hours=1)
        
        return points
    
    def _get_default_daily_stats(self) -> DailyMentalStateStats:
        """Return default stats when no data is available."""
        return DailyMentalStateStats(
            avg_energy=5.0,
            avg_stress=5.0,
            peak_energy_time="N/A",
            peak_stress_time="N/A",
            optimal_state_minutes=0,
            burnout_risk_minutes=0,
            recovery_periods=0
        )
    
    def _calculate_daily_stats(
        self, 
        points: List[MentalStatePoint]
    ) -> DailyMentalStateStats:
        """Calculate daily statistics from points."""
        if not points:
            return DailyMentalStateStats(
                avg_energy=0,
                avg_stress=0,
                peak_energy_time="00:00",
                peak_stress_time="00:00",
                optimal_state_minutes=0,
                burnout_risk_minutes=0,
                recovery_periods=0
            )
        
        energies = [p.energy_score for p in points]
        stresses = [p.stress_score for p in points]
        
        # Find peaks
        peak_energy_idx = energies.index(max(energies))
        peak_stress_idx = stresses.index(max(stresses))
        
        # Count state minutes (each point represents 30 minutes)
        optimal_count = sum(1 for p in points if p.energy_score > 7 and p.stress_score < 3)
        burnout_count = sum(1 for p in points if p.energy_score < 3 and p.stress_score > 7)
        
        # Detect recovery periods (stress drops by 2+ points)
        recovery_count = 0
        for i in range(1, len(points)):
            if points[i-1].stress_score - points[i].stress_score >= 2:
                recovery_count += 1
        
        return DailyMentalStateStats(
            avg_energy=round(mean(energies), 1),
            avg_stress=round(mean(stresses), 1),
            peak_energy_time=points[peak_energy_idx].timestamp.strftime("%H:%M"),
            peak_stress_time=points[peak_stress_idx].timestamp.strftime("%H:%M"),
            optimal_state_minutes=optimal_count * 30,
            burnout_risk_minutes=burnout_count * 30,
            recovery_periods=recovery_count
        )
    
    def _detect_patterns(
        self, 
        points: List[MentalStatePoint]
    ) -> List[MentalStatePattern]:
        """Detect patterns in mental state data."""
        patterns = []
        
        # Pattern 1: Afternoon energy dip
        afternoon_points = [p for p in points if 13 <= p.timestamp.hour <= 15]
        if afternoon_points:
            avg_afternoon = mean([p.energy_score for p in afternoon_points])
            if avg_afternoon < 5:
                patterns.append(MentalStatePattern(
                    pattern_type="afternoon_dip",
                    description="Consistent energy drop in early afternoon",
                    frequency="Daily",
                    impact="Reduces productivity, may benefit from break or light activity"
                ))
        
        # Pattern 2: Morning stress spike
        morning_points = [p for p in points if 7 <= p.timestamp.hour <= 10]
        if morning_points:
            avg_morning_stress = mean([p.stress_score for p in morning_points])
            if avg_morning_stress > 6:
                patterns.append(MentalStatePattern(
                    pattern_type="morning_stress",
                    description="High stress levels during morning hours",
                    frequency="Most weekdays",
                    impact="May affect entire day's mood and energy"
                ))
        
        # More patterns can be added here...
        
        return patterns
    
    def _generate_recommendations(
        self,
        current: MentalStatePoint,
        recent_trend: List[MentalStatePoint],
        patterns: List[MentalStatePattern]
    ) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []
        
        # Current state recommendations
        if current.energy_score < 3 and current.stress_score > 7:
            recommendations.append("⚠️ High burnout risk detected. Consider taking a break immediately.")
        elif current.energy_score < 4:
            recommendations.append("💡 Low energy detected. A short walk or healthy snack might help.")
        elif current.stress_score > 7:
            recommendations.append("🧘 High stress levels. Try deep breathing or a 5-minute meditation.")
        
        # Trend-based recommendations
        if len(recent_trend) >= 3:
            recent_stress = [p.stress_score for p in recent_trend[-3:]]
            if all(s > 6 for s in recent_stress):
                recommendations.append("📈 Sustained high stress detected. Schedule some recovery time.")
        
        # Pattern-based recommendations
        for pattern in patterns:
            if pattern.pattern_type == "afternoon_dip":
                recommendations.append("🍵 Consider scheduling less demanding tasks for early afternoon.")
            elif pattern.pattern_type == "morning_stress":
                recommendations.append("🌅 Try a calming morning routine to reduce stress buildup.")
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _assess_risks(
        self, 
        points: List[MentalStatePoint]
    ) -> Dict[str, Any]:
        """Assess various risk indicators."""
        if not points:
            return {}
        
        # Count risk states
        burnout_count = sum(1 for p in points if p.energy_score < 3 and p.stress_score > 7)
        high_stress_count = sum(1 for p in points if p.stress_score > 7)
        low_energy_count = sum(1 for p in points if p.energy_score < 3)
        
        return {
            "burnout_risk": "high" if burnout_count > 4 else "medium" if burnout_count > 2 else "low",
            "stress_level": "high" if high_stress_count > 10 else "medium" if high_stress_count > 5 else "low",
            "energy_level": "low" if low_energy_count > 10 else "medium" if low_energy_count > 5 else "good",
            "needs_intervention": burnout_count > 4 or high_stress_count > 15
        }


def check_user_active(username: str) -> bool:
    """Check if user has events in the past 48 hours."""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
        recent_events = get_user_events_by_date_range(
            username=username,
            start_time=cutoff_time,
            end_time=datetime.now(timezone.utc)
        )
        return len(recent_events) > 0
    except Exception as e:
        logger.error(f"Error checking user activity: {e}")
        return False