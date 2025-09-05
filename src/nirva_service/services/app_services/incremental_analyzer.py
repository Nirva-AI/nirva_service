import json
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from loguru import logger
from sqlalchemy import and_, or_, func, text

from ...models.prompt import EventAnalysis, OngoingEventOutput, CompletedEventOutput
from ...models.api import IncrementalAnalyzeResponse
from ...db.pgsql_client import SessionLocal
from ...db.pgsql_object import TranscriptionResultDB
from ...db.pgsql_events import get_user_events, save_events
from ..langgraph_services.langgraph_request_task import LanggraphRequestTask
from ..langgraph_services.langgraph_service import LanggraphService


class IncrementalAnalyzer:
    """Incremental event analyzer with ongoing/completed event processing"""
    
    def __init__(self, langgraph_service: LanggraphService, raw_event_gap_minutes: int = 10):
        """
        Initialize the incremental analyzer.
        
        Args:
            langgraph_service: Service for LLM interactions
            raw_event_gap_minutes: Minutes of gap to split events (default: 10)
        """
        self.langgraph_service = langgraph_service
        self.raw_event_gap_seconds = raw_event_gap_minutes * 60
    
    async def process_incremental_transcript(
        self, 
        username: str,
        time_stamp: str,  # This will be deprecated but kept for compatibility
        new_transcript: str
    ) -> IncrementalAnalyzeResponse:
        """
        Process new transcripts incrementally.
        
        Args:
            username: Username
            time_stamp: Date string (for backwards compatibility)
            new_transcript: Concatenated new transcripts with time markers
            
        Returns:
            IncrementalAnalyzeResponse: Processing results
        """
        logger.info(f"Processing incremental transcripts for user {username}")
        
        try:
            # Parse transcripts to extract time information
            transcript_chunks = self._parse_transcript_with_times(new_transcript)
            
            if not transcript_chunks:
                logger.warning("No valid transcript chunks found")
                return IncrementalAnalyzeResponse(
                    updated_events_count=0,
                    new_events_count=0,
                    total_events_count=0,
                    message="No valid transcripts to process"
                )
            
            # Group transcripts into raw events based on time gaps
            raw_event_groups = self._group_into_raw_events(transcript_chunks, username)
            
            # Get existing events for this user (ongoing ones)
            ongoing_events = await self._get_ongoing_events(username)
            
            # Process each raw event group
            processed_events = []
            events_updated = 0
            events_created = 0
            
            for raw_group in raw_event_groups:
                # Check if this group continues an ongoing event
                matching_ongoing = self._find_matching_ongoing_event(
                    raw_group['start_time'], ongoing_events
                )
                
                if matching_ongoing:
                    # Type 3b: Continue ongoing event
                    logger.info(f"Continuing ongoing event {matching_ongoing.event_id}")
                    updated_event = await self._continue_ongoing_event(
                        matching_ongoing, raw_group
                    )
                    processed_events.append(updated_event)
                    events_updated += 1
                    # Remove from ongoing list so it won't be completed
                    ongoing_events = [e for e in ongoing_events if e.event_id != matching_ongoing.event_id]
                else:
                    # Check if there's an ongoing event that should be completed
                    for ongoing in ongoing_events:
                        if self._should_complete_event(ongoing, raw_group['start_time']):
                            # Type 3c: Complete the ongoing event
                            logger.info(f"Completing event {ongoing.event_id}")
                            completed = await self._complete_event(ongoing)
                            processed_events.append(completed)
                    
                    # Type 3a: Create new ongoing event
                    logger.info("Creating new ongoing event")
                    new_event = await self._process_new_ongoing_event(raw_group)
                    processed_events.append(new_event)
                    events_created += 1
            
            # Save all processed events
            await self._save_events(username, processed_events)
            
            # Get total event count for user
            total_events = await self._get_total_event_count(username)
            
            return IncrementalAnalyzeResponse(
                updated_events_count=events_updated,
                new_events_count=events_created,
                total_events_count=total_events,
                message=f"Processed {len(raw_event_groups)} transcript groups"
            )
            
        except Exception as e:
            logger.error(f"Error in incremental analysis: {e}")
            raise
    
    def _parse_transcript_with_times(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Parse transcript with time markers to extract chunks with timestamps.
        Supports both [HH:MM] and [ISO_TIMESTAMP] formats.
        
        Returns:
            List of dicts with 'time', 'text' keys
        """
        import re
        
        chunks = []
        # Pattern to match either [ISO_TIMESTAMP] or [HH:MM] followed by text
        # ISO format: 2025-09-04T23:30:00+00:00
        # Simple time: 23:30
        pattern = r'\[([^\]]+)\]\s*([^\[]+)'
        matches = re.findall(pattern, transcript)
        
        for time_str, text in matches:
            chunks.append({
                'time': time_str,
                'text': text.strip()
            })
        
        return chunks
    
    def _group_into_raw_events(
        self, 
        transcript_chunks: List[Dict[str, Any]], 
        username: str
    ) -> List[Dict[str, Any]]:
        """
        Group transcript chunks into raw events based on time gaps.
        
        Returns:
            List of raw event groups with start_time, end_time, and combined text
        """
        if not transcript_chunks:
            return []
        
        groups = []
        # Parse first timestamp without previous context
        first_time = self._parse_time_string(transcript_chunks[0]['time'])
        current_group = {
            'chunks': [transcript_chunks[0]],
            'start_time': first_time,
            'end_time': first_time
        }
        
        # Keep track of the last parsed time for midnight crossing detection
        last_time = first_time
        
        for chunk in transcript_chunks[1:]:
            # Parse with previous time context to handle midnight crossing
            chunk_time = self._parse_time_string(chunk['time'], last_time)
            time_gap = (chunk_time - current_group['end_time']).total_seconds()
            
            if time_gap > self.raw_event_gap_seconds:
                # Gap too large, finalize current group and start new one
                current_group['text'] = ' '.join([c['text'] for c in current_group['chunks']])
                groups.append(current_group)
                
                current_group = {
                    'chunks': [chunk],
                    'start_time': chunk_time,
                    'end_time': chunk_time
                }
            else:
                # Add to current group
                current_group['chunks'].append(chunk)
                current_group['end_time'] = chunk_time
            
            # Update last_time for next iteration
            last_time = chunk_time
        
        # Add final group
        if current_group['chunks']:
            current_group['text'] = ' '.join([c['text'] for c in current_group['chunks']])
            groups.append(current_group)
        
        return groups
    
    def _parse_time_string(self, time_str: str, previous_time: Optional[datetime] = None) -> datetime:
        """
        Parse time string to datetime. Always returns UTC datetime.
        Handles ISO format timestamps directly.
        """
        from datetime import datetime, timezone
        from dateutil import parser
        
        try:
            # Parse ISO format timestamp (this should be the primary format now)
            parsed = parser.isoparse(time_str)
            
            # Ensure it's timezone-aware (UTC if not specified)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            
            # Convert to UTC if it has a different timezone
            return parsed.astimezone(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to parse timestamp '{time_str}': {e}")
            # Fallback to current time in UTC
            return datetime.now(timezone.utc)
    
    async def _get_ongoing_events(self, username: str) -> List[EventAnalysis]:
        """
        Get ongoing events for a user.
        """
        # Get all events for the user
        all_events = get_user_events(username)
        
        # Filter for ongoing events
        ongoing_events = [
            event for event in all_events 
            if event.event_status == 'ongoing'
        ]
        
        return ongoing_events
    
    def _find_matching_ongoing_event(
        self, 
        new_start_time: datetime, 
        ongoing_events: List[EventAnalysis]
    ) -> Optional[EventAnalysis]:
        """
        Find an ongoing event that should be continued with new content.
        """
        for event in ongoing_events:
            if hasattr(event, 'end_timestamp') and event.end_timestamp:
                gap = (new_start_time - event.end_timestamp).total_seconds()
                if gap <= self.raw_event_gap_seconds:
                    return event
        return None
    
    def _should_complete_event(
        self, 
        ongoing_event: EventAnalysis, 
        new_start_time: datetime
    ) -> bool:
        """
        Check if an ongoing event should be completed.
        """
        if hasattr(ongoing_event, 'end_timestamp') and ongoing_event.end_timestamp:
            gap = (new_start_time - ongoing_event.end_timestamp).total_seconds()
            return gap > self.raw_event_gap_seconds
        return False
    
    async def _process_new_ongoing_event(
        self, 
        raw_group: Dict[str, Any]
    ) -> EventAnalysis:
        """
        Type 3a: Process new ongoing event.
        """
        # Load and format prompt
        with open('src/nirva_service/prompts/process_new_ongoing.md', 'r') as f:
            prompt_template = f.read()
        
        prompt = prompt_template.replace('{transcript}', raw_group.get('text', ''))
        
        # Call LLM
        response = await self._call_llm_structured(prompt, OngoingEventOutput)
        
        # Create EventAnalysis object
        event = EventAnalysis(
            event_id=str(uuid.uuid4()),
            event_title=response.event_title,
            event_summary=response.event_summary,
            event_story=response.event_story,
            event_status='ongoing',
            start_timestamp=raw_group['start_time'],
            end_timestamp=raw_group['end_time'],
            last_processed_at=datetime.utcnow(),
            # Set defaults for required fields
            time_range=f"{raw_group['start_time'].strftime('%H:%M')}-{raw_group['end_time'].strftime('%H:%M')}",
            duration_minutes=int((raw_group['end_time'] - raw_group['start_time']).total_seconds() / 60),
            location='unspecified',
            mood_labels=['neutral'],
            mood_score=7,
            stress_level=5,
            energy_level=7,
            activity_type='unknown',
            people_involved=[],
            interaction_dynamic='solo',
            inferred_impact_on_user_name='neutral',
            topic_labels=['general'],
            one_sentence_summary=response.event_summary,
            first_person_narrative=response.event_story,
            action_item='N/A'
        )
        
        return event
    
    async def _continue_ongoing_event(
        self, 
        ongoing_event: EventAnalysis, 
        raw_group: Dict[str, Any]
    ) -> EventAnalysis:
        """
        Type 3b: Continue an ongoing event with new content.
        """
        # Load and format prompt
        with open('src/nirva_service/prompts/continue_ongoing.md', 'r') as f:
            prompt_template = f.read()
        
        prompt = prompt_template.format(
            previous_title=ongoing_event.event_title or "Ongoing Activity",
            previous_summary=(ongoing_event.event_summary or ongoing_event.one_sentence_summary or "An activity is in progress"),
            previous_story=(ongoing_event.event_story or ongoing_event.first_person_narrative or "Activity details not available"),
            new_transcript=raw_group.get('text', '')
        )
        
        # Call LLM
        response = await self._call_llm_structured(prompt, OngoingEventOutput)
        
        # Update event
        ongoing_event.event_title = response.event_title
        ongoing_event.event_summary = response.event_summary
        ongoing_event.event_story = response.event_story
        ongoing_event.end_timestamp = raw_group['end_time']
        ongoing_event.last_processed_at = datetime.utcnow()
        ongoing_event.one_sentence_summary = response.event_summary
        ongoing_event.first_person_narrative = response.event_story
        
        # Update time range and duration
        if ongoing_event.start_timestamp and ongoing_event.end_timestamp:
            ongoing_event.time_range = f"{ongoing_event.start_timestamp.strftime('%H:%M')}-{ongoing_event.end_timestamp.strftime('%H:%M')}"
            ongoing_event.duration_minutes = int((ongoing_event.end_timestamp - ongoing_event.start_timestamp).total_seconds() / 60)
        
        return ongoing_event
    
    async def _complete_event(
        self, 
        ongoing_event: EventAnalysis,
        new_transcript: Optional[str] = None
    ) -> EventAnalysis:
        """
        Type 3c: Complete an event.
        """
        # Load and format prompt
        with open('src/nirva_service/prompts/process_completed.md', 'r') as f:
            prompt_template = f.read()
        
        # Build previous section if event has data
        previous_section = ""
        if ongoing_event.event_story or ongoing_event.first_person_narrative:
            previous_section = f"""## Previous Event Details
**Title:** {ongoing_event.event_title or "Ongoing Activity"}
**Summary:** {ongoing_event.event_summary or ongoing_event.one_sentence_summary or "An activity in progress"}
**Story:** {ongoing_event.event_story or ongoing_event.first_person_narrative or "Activity details not available"}"""
        
        # Build new section if there's new transcript
        new_section = ""
        if new_transcript:
            new_section = f"""## New Transcript
{new_transcript}"""
        
        # If neither exists, we shouldn't be here
        if not previous_section and not new_section:
            logger.error("Cannot complete event without any content")
            return ongoing_event
        
        prompt = prompt_template.format(
            previous_section=previous_section,
            new_section=new_section
        )
        
        # Call LLM
        response = await self._call_llm_structured(prompt, CompletedEventOutput)
        
        # Update event with completed data
        ongoing_event.event_title = response.event_title
        ongoing_event.event_summary = response.event_summary
        ongoing_event.event_story = response.event_story
        ongoing_event.event_status = 'completed'
        ongoing_event.location = response.location
        ongoing_event.people_involved = response.people_involved
        ongoing_event.activity_type = response.activity_type
        ongoing_event.mood_labels = response.mood_labels
        ongoing_event.mood_score = response.mood_score
        ongoing_event.last_processed_at = datetime.utcnow()
        ongoing_event.one_sentence_summary = response.event_summary
        ongoing_event.first_person_narrative = response.event_story
        
        return ongoing_event
    
    async def _call_llm_structured(
        self, 
        prompt: str, 
        response_model: Any
    ) -> Any:
        """
        Call LLM with structured output using OpenAI's latest structured output API.
        """
        import os
        from openai import AsyncOpenAI
        
        # Create OpenAI client
        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        try:
            # Use the latest structured output API with parse method
            completion = await client.beta.chat.completions.parse(
                model="gpt-4.1",  # Latest model supporting structured outputs
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes transcripts and returns structured data."},
                    {"role": "user", "content": prompt}
                ],
                response_format=response_model,
                temperature=0.1
            )
            
            # Access the parsed response directly
            if completion.choices and completion.choices[0].message.parsed:
                return completion.choices[0].message.parsed
            else:
                raise ValueError("OpenAI returned no parsed content")
                
        except Exception as e:
            logger.error(f"OpenAI structured call failed: {e}")
            # Return a default response based on the model
            if response_model == OngoingEventOutput:
                return OngoingEventOutput(
                    event_title="Activity",
                    event_summary="An activity occurred.",
                    event_story="Something happened during this time period."
                )
            else:
                return CompletedEventOutput(
                    event_title="Completed Activity",
                    event_summary="An activity was completed.",
                    event_story="This activity took place and has now concluded.",
                    location="unspecified",
                    people_involved=[],
                    activity_type="unknown",
                    mood_labels=["neutral"],
                    mood_score=5
                )
    
    async def _save_events(self, username: str, events: List[EventAnalysis]):
        """
        Save events directly to the events table.
        """
        if not events:
            return
        
        # Save events using the new events table
        saved_count = save_events(username, events)
        logger.info(f"Saved {saved_count} events for user {username}")
    
    async def _get_total_event_count(self, username: str) -> int:
        """
        Get total event count for a user.
        """
        events = get_user_events(username)
        return len(events)