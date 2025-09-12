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
    
    def _smooth_stress_transition(
        self,
        username: str,
        current_stress: float,
        timestamp: datetime
    ) -> float:
        """Apply smoothing to prevent sharp stress transitions."""
        # Get previous point (30 minutes ago) for comparison
        prev_timestamp = timestamp - timedelta(minutes=30)
        try:
            prev_point = self._get_recent_stress_value(username, prev_timestamp)
            if prev_point is not None:
                # Limit change rate to max 12 points per 30-minute interval
                max_change = 12.0
                stress_delta = current_stress - prev_point
                
                if abs(stress_delta) > max_change:
                    # Apply gradual transition
                    if stress_delta > 0:
                        return prev_point + max_change
                    else:
                        return prev_point - max_change
        except Exception:
            pass  # If we can't get previous data, proceed without smoothing
        
        return current_stress
    
    def _get_recent_stress_value(
        self,
        username: str,
        timestamp: datetime
    ) -> Optional[float]:
        """Get stress value from recent history for smoothing."""
        try:
            # Look for a stored value within 1 hour of the target timestamp
            from ..db.pgsql_object import UserDB
            user = self.session.query(UserDB).filter(
                UserDB.username == username
            ).first()
            if not user:
                return None
            
            # Query for nearby points
            window_start = timestamp - timedelta(minutes=60)
            window_end = timestamp + timedelta(minutes=60)
            
            recent_point = self.session.query(MentalStateScoreDB).filter(
                MentalStateScoreDB.user_id == user.id,
                MentalStateScoreDB.timestamp >= window_start,
                MentalStateScoreDB.timestamp <= window_end
            ).order_by(
                MentalStateScoreDB.timestamp.desc()
            ).first()
            
            return recent_point.stress_score if recent_point else None
        except Exception:
            return None

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
        base_energy, base_stress, base_mood = self.get_natural_baseline(timestamp)
        
        # Layer 2: Event impacts
        energy_delta, stress_delta, mood_delta, event_id = self.calculate_event_impacts(
            username, timestamp
        )
        
        # Layer 3: Personal patterns (calculated from historical data)
        personal_adj = self.get_personal_adjustment(username, timestamp)
        
        # Combine layers
        final_energy = base_energy + energy_delta + personal_adj['energy']
        final_stress = base_stress + stress_delta + personal_adj['stress']
        final_mood = base_mood + mood_delta + personal_adj.get('mood', 0)
        
        # Apply interaction effects
        final_energy, final_stress, final_mood = self.apply_interaction_effects(
            final_energy, final_stress, final_mood
        )
        
        # Apply stress smoothing to prevent sharp transitions
        final_stress = self._smooth_stress_transition(username, final_stress, timestamp)
        
        # Clamp values to valid range (0-100 for all scores)
        final_energy = max(0, min(100, final_energy))
        final_stress = max(8, min(100, final_stress))  # Minimum stress floor of 8
        final_mood = max(0, min(100, final_mood))
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            has_event=event_id is not None,
            time_since_event=self._get_time_since_last_event(username, timestamp)
        )
        
        # Determine data source
        if event_id:
            data_source = "event"
        elif abs(energy_delta) > 0.1 or abs(stress_delta) > 0.1 or abs(mood_delta) > 0.1:
            data_source = "interpolated"
        else:
            data_source = "baseline"
        
        return MentalStatePoint(
            timestamp=timestamp,
            energy_score=round(final_energy, 0),  # 0-100 scale
            stress_score=round(final_stress, 0),  # 0-100 scale
            mood_score=round(final_mood, 0),      # 0-100 scale
            confidence=round(confidence, 2),
            data_source=data_source,
            event_id=event_id
        )
    
    def get_natural_baseline(self, timestamp: datetime) -> Tuple[float, float, float]:
        """Get universal human energy, stress, and mood patterns."""
        hour = timestamp.hour + timestamp.minute / 60.0  # Decimal hour
        day_of_week = timestamp.weekday()
        
        # Circadian rhythm for energy (1-100 scale)
        energy_curve = {
            0: 30,   # Midnight
            3: 25,   # Deep sleep
            6: 40,   # Wake up
            9: 65,   # Morning rise
            11: 75,  # Peak morning
            13: 60,  # Lunch time
            14: 55,  # Post-lunch dip
            16: 65,  # Afternoon recovery
            18: 60,  # Early evening
            20: 50,  # Evening
            21: 45,  # Wind down
            23: 35   # Prepare for sleep
        }
        
        # Daily stress pattern (1-100 scale)
        stress_curve = {
            0: 20,   # Midnight
            3: 10,   # Deep sleep
            6: 25,   # Wake up
            9: 45,   # Work start
            12: 60,  # Midday pressure
            15: 70,  # Afternoon peak
            18: 45,  # Evening relief
            21: 30,  # Relaxation
            23: 20   # Prepare for sleep
        }
        
        # Daily mood pattern (0-100 scale) - correlates with energy but more stable
        mood_curve = {
            0: 45,   # Midnight - moderate
            3: 40,   # Deep sleep - lower but not as low as energy
            6: 50,   # Wake up - neutral
            9: 70,   # Morning optimism
            11: 75,  # Peak morning mood
            13: 65,  # Post-lunch stable
            14: 60,  # Slight afternoon dip
            16: 70,  # Afternoon recovery
            18: 65,  # Early evening satisfaction
            20: 60,  # Evening content
            21: 55,  # Wind down
            23: 50   # Prepare for sleep
        }
        
        # Interpolate for exact hour
        base_energy = self._interpolate_curve(energy_curve, hour)
        base_stress = self._interpolate_curve(stress_curve, hour)
        base_mood = self._interpolate_curve(mood_curve, hour)
        
        # Weekend adjustment
        if day_of_week >= 5:  # Saturday = 5, Sunday = 6
            base_stress *= 0.8  # 20% less stress (more gradual)
            base_energy *= 1.1  # 10% more energy
            base_mood *= 1.15   # 15% better mood on weekends
        
        return base_energy, base_stress, base_mood
    
    def calculate_event_impacts(
        self, 
        username: str, 
        timestamp: datetime
    ) -> Tuple[float, float, float, Optional[str]]:
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
        mood_delta = 0.0
        current_event_id = None
        
        for event in events:
            if not event.start_timestamp or not event.end_timestamp:
                continue
                
            # Direct impact if during event
            if event.start_timestamp <= timestamp <= event.end_timestamp:
                current_event_id = event.event_id
                # Use actual event scores as deltas from neutral (1-100 scale)
                energy_delta = event.energy_level - 55  # Neutral is 55 for energy
                stress_delta = (event.stress_level - 42) * 0.75  # Neutral is 42 for stress, dampened
                mood_delta = event.mood_score - 62  # Neutral is 62 for mood
            
            # Lingering effects after event
            elif event.end_timestamp < timestamp:
                hours_passed = (timestamp - event.end_timestamp).total_seconds() / 3600
                
                # Different decay rates for energy and stress
                energy_decay = math.exp(-0.5 * hours_passed)  # 50% after ~1.4 hours
                stress_decay = math.exp(-0.23 * hours_passed)  # 50% after ~3 hours (gentler)
                
                energy_impact = (event.energy_level - 55) * energy_decay  # 1-100 scale
                stress_impact = (event.stress_level - 42) * 0.75 * stress_decay  # 1-100 scale, dampened
                mood_impact = (event.mood_score - 62) * 0.8 * stress_decay  # 1-100 scale, gentle decay
                
                # Apply impacts
                energy_delta += energy_impact
                stress_delta += stress_impact
                mood_delta += mood_impact
            
            # Anticipation effects (upcoming events)
            elif event.start_timestamp > timestamp:
                hours_until = (event.start_timestamp - timestamp).total_seconds() / 3600
                if hours_until <= 1:
                    # Anticipation affects stress more than energy (1-100 scale)
                    if event.activity_type == 'work':
                        stress_delta += 5  # Add 5 stress points
                        mood_delta -= 2  # Slight mood decrease
                    elif event.activity_type == 'social':
                        energy_delta += 3  # Add 3 energy points
                        mood_delta += 4  # Social anticipation boosts mood
                        if event.interaction_dynamic == 'tense':
                            stress_delta += 4  # Add 4 stress points
                            mood_delta -= 3  # Override positive mood anticipation
        
        return energy_delta, stress_delta, mood_delta, current_event_id
    
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
            return {'energy': 0, 'stress': 0, 'mood': 0}
        
        # Calculate how this user differs from baseline
        avg_energy = mean([p.energy_score for p in historical_points])
        avg_stress = mean([p.stress_score for p in historical_points])
        avg_mood = mean([p.mood_score for p in historical_points])
        
        expected_energy, expected_stress, expected_mood = self.get_natural_baseline(timestamp)
        
        # Personal deviation from normal patterns (30% weight)
        energy_adjustment = (avg_energy - expected_energy) * 0.3
        stress_adjustment = (avg_stress - expected_stress) * 0.3
        mood_adjustment = (avg_mood - expected_mood) * 0.3
        
        return {
            'energy': energy_adjustment,
            'stress': stress_adjustment,
            'mood': mood_adjustment
        }
    
    def apply_interaction_effects(
        self, 
        energy: float, 
        stress: float,
        mood: float
    ) -> Tuple[float, float, float]:
        """Apply feedback loops between energy, stress, and mood."""
        # High stress drains energy and mood (1-100 scale)
        if stress > 70:
            energy_drain = (stress - 70) * 0.3
            mood_drain = (stress - 70) * 0.25  # Stress affects mood but less than energy
            energy -= energy_drain
            mood -= mood_drain
        
        # Very low energy increases stress vulnerability and dampens mood
        if energy < 30:
            stress_increase = (30 - energy) * 0.2
            mood_decrease = (30 - energy) * 0.15
            stress += stress_increase
            mood -= mood_decrease
        
        # Good mood boosts energy and reduces stress
        if mood > 75:
            energy_boost = (mood - 75) * 0.2
            stress_reduction = (mood - 75) * 0.15
            energy += energy_boost
            stress -= stress_reduction
        
        # Poor mood drains energy and increases stress vulnerability
        if mood < 30:
            energy_drain = (30 - mood) * 0.15
            stress_increase = (30 - mood) * 0.1
            energy -= energy_drain
            stress += stress_increase
        
        # Optimal zone boost (high energy, low stress, good mood)
        if energy > 70 and stress < 30 and mood > 65:
            energy *= 1.1  # 10% boost
            stress *= 0.95  # 5% reduction
            mood *= 1.05  # 5% mood boost
        
        # Danger zone spiral (low energy, high stress, poor mood)
        if energy < 30 and stress > 70 and mood < 40:
            energy *= 0.9  # 10% worse
            stress *= 1.1  # 10% worse
            mood *= 0.95  # 5% worse
        
        return energy, stress, mood
    
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
            avg_energy=50.0,  # Neutral on 1-100 scale
            avg_stress=50.0,  # Neutral on 1-100 scale
            avg_mood=65.0,  # Neutral positive mood on 1-100 scale
            peak_energy_time="N/A",
            peak_stress_time="N/A",
            peak_mood_time="N/A",
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
                avg_mood=0,
                peak_energy_time="00:00",
                peak_stress_time="00:00",
                peak_mood_time="00:00",
                optimal_state_minutes=0,
                burnout_risk_minutes=0,
                recovery_periods=0
            )
        
        energies = [p.energy_score for p in points]
        stresses = [p.stress_score for p in points]
        moods = [p.mood_score for p in points]
        
        # Find peaks
        peak_energy_idx = energies.index(max(energies))
        peak_stress_idx = stresses.index(max(stresses))
        peak_mood_idx = moods.index(max(moods))
        
        # Count state minutes (each point represents 30 minutes)
        optimal_count = sum(1 for p in points if p.energy_score > 70 and p.stress_score < 30)
        burnout_count = sum(1 for p in points if p.energy_score < 30 and p.stress_score > 70)
        
        # Detect recovery periods (stress drops by 20+ points)
        recovery_count = 0
        for i in range(1, len(points)):
            if points[i-1].stress_score - points[i].stress_score >= 20:  # Scaled from 2 to 20
                recovery_count += 1
        
        return DailyMentalStateStats(
            avg_energy=round(mean(energies), 1),
            avg_stress=round(mean(stresses), 1),
            avg_mood=round(mean(moods), 1),
            peak_energy_time=points[peak_energy_idx].timestamp.strftime("%H:%M"),
            peak_stress_time=points[peak_stress_idx].timestamp.strftime("%H:%M"),
            peak_mood_time=points[peak_mood_idx].timestamp.strftime("%H:%M"),
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
            if avg_afternoon < 50:  # Scaled from 5 to 50
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
            if avg_morning_stress > 60:  # Scaled from 6 to 60
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
        if current.energy_score < 30 and current.stress_score > 70:
            recommendations.append("⚠️ High burnout risk detected. Consider taking a break immediately.")
        elif current.energy_score < 40:
            recommendations.append("💡 Low energy detected. A short walk or healthy snack might help.")
        elif current.stress_score > 70:
            recommendations.append("🧘 High stress levels. Try deep breathing or a 5-minute meditation.")
        
        # Trend-based recommendations
        if len(recent_trend) >= 3:
            recent_stress = [p.stress_score for p in recent_trend[-3:]]
            if all(s > 60 for s in recent_stress):
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
        burnout_count = sum(1 for p in points if p.energy_score < 30 and p.stress_score > 70)
        high_stress_count = sum(1 for p in points if p.stress_score > 70)
        low_energy_count = sum(1 for p in points if p.energy_score < 30)
        
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