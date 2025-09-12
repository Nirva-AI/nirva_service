"""
Time allocation calculation service based on event analysis data.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
from loguru import logger

from ..models.mental_state import (
    TimeAllocationData,
    TimeAllocationInsights,
    TimeAllocationTimeline,
    TimeAllocationResponse
)
from ..db.pgsql_events import get_user_events_by_date_range
from ..db.pgsql_client import SessionLocal


class TimeAllocationCalculator:
    """Calculate time allocation insights from user events."""
    
    # Activity categories mapping to standardize variations
    ACTIVITY_CATEGORIES = {
        'work': 'Work',
        'exercise': 'Exercise',
        'social': 'Social',
        'learning': 'Learning',
        'self-care': 'Self-care',
        'chores': 'Chores',
        'commute': 'Commute',
        'meal': 'Meal',
        'leisure': 'Leisure',
        'unknown': 'Others'
    }
    
    def __init__(self):
        self.session = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    def get_time_allocation_insights(
        self, 
        username: str, 
        date: Optional[str] = None,
        timezone_str: str = "UTC"
    ) -> TimeAllocationResponse:
        """Get complete time allocation insights for all time periods."""
        
        # Parse target date
        if date:
            target_date = datetime.fromisoformat(date).date()
        else:
            target_date = datetime.now().date()
        
        # Calculate different time periods
        day_data = self._get_daily_allocation(username, target_date, timezone_str)
        week_data = self._get_weekly_allocation(username, target_date, timezone_str)
        month_data = self._get_monthly_allocation(username, target_date, timezone_str)
        
        # Get current insights (today's data)
        current_insights = self._calculate_insights(day_data, target_date.isoformat())
        
        # Detect patterns
        patterns = self._detect_patterns(day_data, week_data)
        
        return TimeAllocationResponse(
            current_insights=current_insights,
            day_view=day_data,
            week_view=week_data,
            month_view=month_data,
            patterns=patterns
        )
    
    def _get_daily_allocation(
        self, 
        username: str, 
        date: datetime.date, 
        timezone_str: str
    ) -> List[TimeAllocationData]:
        """Get time allocation for a specific day."""
        
        # Get start and end of day
        start_time = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_time = start_time + timedelta(days=1)
        
        # Fetch events for the day
        events = get_user_events_by_date_range(username, start_time, end_time)
        
        return self._calculate_allocation_data(events)
    
    def _get_weekly_allocation(
        self, 
        username: str, 
        end_date: datetime.date, 
        timezone_str: str
    ) -> List[TimeAllocationTimeline]:
        """Get time allocation for the past 7 days."""
        
        weekly_data = []
        
        for i in range(7):
            current_date = end_date - timedelta(days=i)
            daily_data = self._get_daily_allocation(username, current_date, timezone_str)
            insights = self._calculate_insights(daily_data, current_date.isoformat())
            
            weekly_data.append(TimeAllocationTimeline(
                date=current_date.isoformat(),
                daily_data=daily_data,
                insights=insights
            ))
        
        return list(reversed(weekly_data))  # Chronological order
    
    def _get_monthly_allocation(
        self, 
        username: str, 
        end_date: datetime.date, 
        timezone_str: str
    ) -> List[TimeAllocationTimeline]:
        """Get time allocation for the past 30 days (weekly aggregates)."""
        
        monthly_data = []
        
        # Get data in weekly chunks over the last 30 days
        for week in range(4):
            week_end = end_date - timedelta(days=week * 7)
            week_start = week_end - timedelta(days=6)
            
            # Aggregate week data
            week_allocation = defaultdict(lambda: {'total_minutes': 0, 'session_count': 0})
            
            for day_offset in range(7):
                current_date = week_start + timedelta(days=day_offset)
                if current_date > end_date:
                    continue
                    
                daily_data = self._get_daily_allocation(username, current_date, timezone_str)
                
                for activity_data in daily_data:
                    week_allocation[activity_data.activity_type]['total_minutes'] += activity_data.total_hours * 60
                    week_allocation[activity_data.activity_type]['session_count'] += activity_data.session_count
            
            # Convert to TimeAllocationData
            week_data_list = []
            total_minutes = sum(data['total_minutes'] for data in week_allocation.values())
            
            for activity_type, data in week_allocation.items():
                if data['total_minutes'] > 0:
                    hours = data['total_minutes'] / 60
                    percentage = (data['total_minutes'] / total_minutes * 100) if total_minutes > 0 else 0
                    avg_duration = hours / data['session_count'] if data['session_count'] > 0 else 0
                    
                    week_data_list.append(TimeAllocationData(
                        activity_type=activity_type,
                        total_hours=hours,
                        percentage=percentage,
                        average_session_duration=avg_duration,
                        session_count=data['session_count']
                    ))
            
            insights = self._calculate_insights(week_data_list, f"{week_start.isoformat()}_to_{week_end.isoformat()}")
            
            monthly_data.append(TimeAllocationTimeline(
                date=week_end.isoformat(),
                daily_data=week_data_list,
                insights=insights
            ))
        
        return list(reversed(monthly_data))  # Chronological order
    
    def _calculate_allocation_data(self, events) -> List[TimeAllocationData]:
        """Calculate time allocation data from events."""
        
        activity_stats = defaultdict(lambda: {'total_minutes': 0, 'session_count': 0})
        
        # Aggregate event data by activity type
        for event in events:
            activity_type = self.ACTIVITY_CATEGORIES.get(
                event.activity_type.lower(), 
                'Others'
            )
            
            activity_stats[activity_type]['total_minutes'] += event.duration_minutes
            activity_stats[activity_type]['session_count'] += 1
        
        # Calculate totals
        total_minutes = sum(data['total_minutes'] for data in activity_stats.values())
        
        # Convert to TimeAllocationData objects
        allocation_data = []
        
        for activity_type, data in activity_stats.items():
            if data['total_minutes'] > 0:
                hours = data['total_minutes'] / 60
                percentage = (data['total_minutes'] / total_minutes * 100) if total_minutes > 0 else 0
                avg_duration = hours / data['session_count'] if data['session_count'] > 0 else 0
                
                allocation_data.append(TimeAllocationData(
                    activity_type=activity_type,
                    total_hours=hours,
                    percentage=percentage,
                    average_session_duration=avg_duration,
                    session_count=data['session_count']
                ))
        
        # Sort by total hours (descending)
        allocation_data.sort(key=lambda x: x.total_hours, reverse=True)
        
        return allocation_data
    
    def _calculate_insights(
        self, 
        allocation_data: List[TimeAllocationData], 
        date_label: str
    ) -> TimeAllocationInsights:
        """Calculate insights from allocation data."""
        
        if not allocation_data:
            return TimeAllocationInsights(
                total_awake_hours=0,
                most_active_category="N/A",
                productivity_score=0,
                balance_score=0,
                top_activities=[],
                recommendations=["No activity data available for this period."]
            )
        
        # Calculate totals
        total_hours = sum(activity.total_hours for activity in allocation_data)
        most_active = allocation_data[0].activity_type if allocation_data else "N/A"
        
        # Calculate productivity score (work + learning activities)
        productive_hours = sum(
            activity.total_hours 
            for activity in allocation_data 
            if activity.activity_type.lower() in ['work', 'learning']
        )
        productivity_score = min((productive_hours / max(total_hours, 1)) * 100, 100)
        
        # Calculate balance score (variety of activities)
        activity_count = len(allocation_data)
        max_single_activity_percentage = max(
            activity.percentage for activity in allocation_data
        ) if allocation_data else 0
        
        # Better balance = more activities, less dominance of single activity
        variety_score = min((activity_count / 6) * 50, 50)  # Up to 50 for having 6+ activities
        dominance_penalty = max_single_activity_percentage * 0.5  # Penalty for over-dominance
        balance_score = max(variety_score - dominance_penalty + 50, 0)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(allocation_data, productivity_score, balance_score)
        
        return TimeAllocationInsights(
            total_awake_hours=total_hours,
            most_active_category=most_active,
            productivity_score=productivity_score,
            balance_score=min(balance_score, 100),
            top_activities=allocation_data[:6],  # Top 6 activities
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self, 
        allocation_data: List[TimeAllocationData], 
        productivity_score: float, 
        balance_score: float
    ) -> List[str]:
        """Generate personalized recommendations based on time allocation patterns."""
        
        recommendations = []
        
        if not allocation_data:
            return ["Track more activities to get personalized recommendations."]
        
        # Check work-life balance
        work_percentage = sum(
            activity.percentage 
            for activity in allocation_data 
            if activity.activity_type.lower() == 'work'
        )
        
        if work_percentage > 60:
            recommendations.append("Consider reducing work hours and increasing time for personal activities.")
        elif work_percentage < 20:
            recommendations.append("You might benefit from dedicating more focused time to productive work.")
        
        # Check self-care
        self_care_hours = sum(
            activity.total_hours 
            for activity in allocation_data 
            if activity.activity_type.lower() in ['self-care', 'exercise']
        )
        
        if self_care_hours < 1:
            recommendations.append("Try to dedicate at least 1 hour daily to self-care and exercise.")
        
        # Check social activities
        social_hours = sum(
            activity.total_hours 
            for activity in allocation_data 
            if activity.activity_type.lower() == 'social'
        )
        
        if social_hours < 0.5:
            recommendations.append("Consider scheduling more time for social interactions and relationships.")
        
        # Check learning
        learning_hours = sum(
            activity.total_hours 
            for activity in allocation_data 
            if activity.activity_type.lower() == 'learning'
        )
        
        if learning_hours < 0.5:
            recommendations.append("Allocate some time for learning new skills or hobbies for personal growth.")
        
        # Balance-based recommendations
        if balance_score < 30:
            recommendations.append("Try to diversify your activities throughout the day for better life balance.")
        
        # Productivity-based recommendations
        if productivity_score > 80:
            recommendations.append("Great productivity! Consider maintaining this balance while ensuring adequate rest.")
        elif productivity_score < 40:
            recommendations.append("Consider dedicating more time to focused, productive activities.")
        
        return recommendations[:4]  # Limit to top 4 recommendations
    
    def _detect_patterns(
        self, 
        day_data: List[TimeAllocationData], 
        week_data: List[TimeAllocationTimeline]
    ) -> List[str]:
        """Detect patterns in time allocation."""
        
        patterns = []
        
        # Check consistency patterns
        if len(week_data) >= 3:
            work_hours_variance = self._calculate_activity_variance(week_data, 'Work')
            if work_hours_variance < 1:
                patterns.append("You maintain consistent work hours throughout the week.")
            elif work_hours_variance > 3:
                patterns.append("Your work hours vary significantly day to day.")
        
        # Check weekend vs weekday patterns
        if len(week_data) == 7:
            weekday_work = self._get_weekday_average(week_data[:5], 'Work')  # Mon-Fri
            weekend_work = self._get_weekday_average(week_data[5:], 'Work')  # Sat-Sun
            
            if weekend_work > weekday_work * 0.5:
                patterns.append("You tend to work on weekends as much as weekdays.")
            elif weekend_work < weekday_work * 0.2:
                patterns.append("You maintain good work-life boundaries on weekends.")
        
        return patterns
    
    def _calculate_activity_variance(
        self, 
        timeline_data: List[TimeAllocationTimeline], 
        activity_type: str
    ) -> float:
        """Calculate variance in hours for a specific activity."""
        
        hours_list = []
        for timeline in timeline_data:
            activity_hours = sum(
                activity.total_hours 
                for activity in timeline.daily_data 
                if activity.activity_type == activity_type
            )
            hours_list.append(activity_hours)
        
        if len(hours_list) < 2:
            return 0
        
        mean_hours = sum(hours_list) / len(hours_list)
        variance = sum((x - mean_hours) ** 2 for x in hours_list) / len(hours_list)
        return variance ** 0.5  # Return standard deviation
    
    def _get_weekday_average(
        self, 
        timeline_data: List[TimeAllocationTimeline], 
        activity_type: str
    ) -> float:
        """Get average hours for an activity over given days."""
        
        total_hours = 0
        day_count = len(timeline_data)
        
        for timeline in timeline_data:
            activity_hours = sum(
                activity.total_hours 
                for activity in timeline.daily_data 
                if activity.activity_type == activity_type
            )
            total_hours += activity_hours
        
        return total_hours / day_count if day_count > 0 else 0