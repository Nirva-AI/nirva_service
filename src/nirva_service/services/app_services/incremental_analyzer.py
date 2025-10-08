import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import and_, func, or_, text

from ...db.pgsql_client import SessionLocal
from ...db.pgsql_events import get_user_events, save_events
from ...db.pgsql_object import TranscriptionResultDB
from ...models.api import IncrementalAnalyzeResponse
from ...models.prompt import CompletedEventOutput, EventAnalysis, OngoingEventOutput
from ...services.llm_context_helper import inject_user_context
from ..langgraph_services.langgraph_request_task import LanggraphRequestTask
from ..langgraph_services.langgraph_service import LanggraphService


class IncrementalAnalyzer:
    """Incremental event analyzer with ongoing/completed event processing"""

    def __init__(
        self, langgraph_service: LanggraphService, raw_event_gap_minutes: int = 10
    ):
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
        new_transcript: str,
    ) -> IncrementalAnalyzeResponse:
        """
        Process new transcripts incrementally with enhanced delayed transcription handling.

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
                    message="No valid transcripts to process",
                )

            # Group transcripts into raw events based on time gaps
            raw_event_groups = self._group_into_raw_events(transcript_chunks, username)
            
            logger.info(f"📋 GROUPING_RESULT: {len(transcript_chunks)} individual transcripts → {len(raw_event_groups)} groups for processing")

            # Check if any transcript groups fall into gaps between existing events (delayed transcriptions)
            reanalysis_range = await self._detect_reanalysis_range(username, raw_event_groups)
            
            if reanalysis_range:
                logger.info(f"🔄 REANALYSIS_DETECTED: Range {reanalysis_range['start_time']} to {reanalysis_range['end_time']} needs re-processing")
                return await self._reprocess_time_range(username, reanalysis_range)

            # Get existing events for this user (ongoing ones)
            ongoing_events = await self._get_ongoing_events(username)

            # Process each raw event group
            processed_events = []
            events_updated = 0
            events_created = 0

            # First, complete any existing ongoing events that should be completed
            completed_ongoing_ids = set()
            for ongoing in ongoing_events:
                if len(raw_event_groups) > 0 and self._should_complete_event(ongoing, raw_event_groups[0]["start_time"]):
                    logger.info(f"Completing existing ongoing event {ongoing.event_id}")
                    completed = await self._complete_event(ongoing, username=username)
                    if completed:
                        processed_events.append(completed)
                        completed_ongoing_ids.add(ongoing.event_id)
                        if completed.event_status == "dropped":
                            logger.info(f"Event {ongoing.event_id} dropped locally")
                    else:
                        logger.info(f"Skipping event {ongoing.event_id} - dropped locally")
                        completed_ongoing_ids.add(ongoing.event_id)

            # Remove completed events from ongoing list
            ongoing_events = [e for e in ongoing_events if e.event_id not in completed_ongoing_ids]

            for i, raw_group in enumerate(raw_event_groups):
                is_last_group = (i == len(raw_event_groups) - 1)
                current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
                
                # Check if this group continues an existing ongoing event
                matching_ongoing = self._find_matching_ongoing_event(
                    raw_group["start_time"], ongoing_events
                )

                if matching_ongoing:
                    # Continue ongoing event
                    logger.info(f"Continuing ongoing event {matching_ongoing.event_id}")
                    updated_event = await self._continue_ongoing_event(
                        matching_ongoing, raw_group, username
                    )
                    
                    # Decide if this should now be completed
                    time_since_end = (current_time - raw_group["end_time"]).total_seconds()
                    if not is_last_group or time_since_end > self.raw_event_gap_seconds:
                        # This is not the last group, or it's old - complete it
                        logger.info(f"Completing continued event {updated_event.event_id} (not recent)")
                        completed = await self._complete_event(updated_event, username=username)
                        if completed:
                            processed_events.append(completed)
                            if completed.event_status == "dropped":
                                logger.info(f"Continued event {updated_event.event_id} dropped locally")
                        else:
                            logger.info(f"Skipping continued event {updated_event.event_id} - dropped locally")
                    else:
                        # Keep as ongoing (last group and recent)
                        processed_events.append(updated_event)
                        events_updated += 1
                    
                    # Remove from ongoing list
                    ongoing_events = [e for e in ongoing_events if e.event_id != matching_ongoing.event_id]
                else:
                    # Create new event - decide if ongoing or completed immediately
                    time_since_end = (current_time - raw_group["end_time"]).total_seconds()
                    
                    if not is_last_group or time_since_end > self.raw_event_gap_seconds:
                        # Not the last group, or it's old - create as completed
                        logger.info(f"Creating completed event (not recent)")
                        completed_event = await self._create_completed_event(raw_group, username)
                        if completed_event:
                            processed_events.append(completed_event)
                            events_created += 1
                            if completed_event.event_status == "dropped":
                                logger.info(f"New event dropped locally during creation")
                    else:
                        # Last group and recent - create as ongoing
                        logger.info("Creating new ongoing event (recent)")
                        new_event = await self._process_new_ongoing_event(raw_group, username)
                        processed_events.append(new_event)
                        events_created += 1

            # After processing all groups, complete any remaining ongoing events that weren't matched
            # This ensures bulk processing completes events within the same batch
            for ongoing in ongoing_events:
                logger.info(f"Completing remaining ongoing event {ongoing.event_id} (end of batch)")
                completed = await self._complete_event(ongoing, username=username)
                if completed:
                    processed_events.append(completed)
                    if completed.event_status == "dropped":
                        logger.info(f"Remaining event {ongoing.event_id} dropped locally")
                else:
                    # Event was dropped - skip it
                    logger.info(f"Skipping remaining event {ongoing.event_id} - dropped locally")

            # Save all processed events
            await self._save_events(username, processed_events)

            # Get total event count for user
            total_events = await self._get_total_event_count(username)

            return IncrementalAnalyzeResponse(
                updated_events_count=events_updated,
                new_events_count=events_created,
                total_events_count=total_events,
                message=f"Processed {len(raw_event_groups)} transcript groups",
            )

        except Exception as e:
            logger.error(f"Error in incremental analysis: {e}")
            raise

    def _parse_transcript_with_times(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Parse transcript with time markers to extract chunks with timestamps.
        Supports:
        - [START_ISO|END_ISO] for full timestamp ranges
        - [ISO_TIMESTAMP] for single timestamps
        - [HH:MM] for simple times

        Returns:
            List of dicts with 'start_time', 'end_time', 'text' keys
        """
        import re

        chunks = []
        # Pattern to match timestamps in brackets followed by text
        pattern = r"\[([^\]]+)\]\s*([^\[]+)"
        matches = re.findall(pattern, transcript)

        for time_str, text in matches:
            # Check if this is a range format (start|end)
            if "|" in time_str:
                start_str, end_str = time_str.split("|", 1)
                chunks.append(
                    {
                        "start_time": start_str.strip(),
                        "end_time": end_str.strip(),
                        "text": text.strip(),
                    }
                )
            else:
                # Single timestamp - use it for both start and end (legacy format)
                chunks.append(
                    {
                        "start_time": time_str.strip(),
                        "end_time": time_str.strip(),
                        "text": text.strip(),
                    }
                )

        return chunks

    def _group_into_raw_events(
        self, transcript_chunks: List[Dict[str, Any]], username: str
    ) -> List[Dict[str, Any]]:
        """
        Group transcript chunks into raw events based on time gaps.

        Returns:
            List of raw event groups with start_time, end_time, and combined text
        """
        if not transcript_chunks:
            return []

        groups: List[Dict[str, Any]] = []
        # Parse first chunk's timestamps
        first_chunk = transcript_chunks[0]
        first_start = self._parse_time_string(first_chunk["start_time"])
        first_end = self._parse_time_string(first_chunk["end_time"])

        current_group: Dict[str, Any] = {
            "chunks": [first_chunk],
            "start_time": first_start,
            "end_time": first_end,  # Use actual end time from transcript
        }

        # Keep track of the last parsed time for midnight crossing detection
        last_time = first_end

        for chunk in transcript_chunks[1:]:
            # Parse with previous time context to handle midnight crossing
            chunk_start = self._parse_time_string(chunk["start_time"], last_time)
            chunk_end = self._parse_time_string(chunk["end_time"], last_time)
            time_gap = (chunk_start - current_group["end_time"]).total_seconds()

            if time_gap > self.raw_event_gap_seconds:
                # Gap too large, finalize current group and start new one
                current_group["text"] = " ".join(
                    [c["text"] for c in current_group["chunks"]]
                )
                groups.append(current_group)

                current_group = {
                    "chunks": [chunk],
                    "start_time": chunk_start,
                    "end_time": chunk_end,  # Use actual end time
                }
            else:
                # Add to current group
                current_group["chunks"].append(chunk)
                current_group[
                    "end_time"
                ] = chunk_end  # Extend to include this chunk's end

            # Update last_time for next iteration
            last_time = chunk_end

        # Add final group
        if current_group["chunks"]:
            current_group["text"] = " ".join(
                [c["text"] for c in current_group["chunks"]]
            )
            groups.append(current_group)

        return groups

    def _parse_time_string(
        self, time_str: str, previous_time: Optional[datetime] = None
    ) -> datetime:
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
            event for event in all_events if event.event_status == "ongoing"
        ]

        return ongoing_events

    def _find_matching_ongoing_event(
        self, new_start_time: datetime, ongoing_events: List[EventAnalysis]
    ) -> Optional[EventAnalysis]:
        """
        Find an ongoing event that should be continued with new content.
        """
        for event in ongoing_events:
            if hasattr(event, "end_timestamp") and event.end_timestamp:
                # Ensure both timestamps are timezone-aware for comparison
                event_end = event.end_timestamp
                if event_end.tzinfo is None:
                    event_end = event_end.replace(tzinfo=timezone.utc)
                if new_start_time.tzinfo is None:
                    new_start_time = new_start_time.replace(tzinfo=timezone.utc)
                    
                gap = (new_start_time - event_end).total_seconds()
                if gap <= self.raw_event_gap_seconds:
                    return event
        return None

    def _should_complete_event(
        self, ongoing_event: EventAnalysis, new_start_time: datetime
    ) -> bool:
        """
        Check if an ongoing event should be completed.
        """
        if hasattr(ongoing_event, "end_timestamp") and ongoing_event.end_timestamp:
            # Ensure both timestamps are timezone-aware for comparison
            event_end = ongoing_event.end_timestamp
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)
            if new_start_time.tzinfo is None:
                new_start_time = new_start_time.replace(tzinfo=timezone.utc)
                
            gap = (new_start_time - event_end).total_seconds()
            return gap > self.raw_event_gap_seconds
        return False

    async def _process_new_ongoing_event(
        self, raw_group: Dict[str, Any], username: str
    ) -> EventAnalysis:
        """
        Type 3a: Process new ongoing event.
        """
        # Load and format prompt
        with open("src/nirva_service/prompts/process_new_ongoing.md", "r") as f:
            prompt_template = f.read()

        prompt = prompt_template.replace("{transcript}", raw_group.get("text", ""))

        # Call LLM
        response = await self._call_llm_structured(prompt, OngoingEventOutput, username)

        # Create EventAnalysis object
        event = EventAnalysis(
            event_id=str(uuid.uuid4()),
            event_title=response.event_title,
            event_summary=response.event_summary,
            event_story=response.event_story,
            event_status="ongoing",
            start_timestamp=raw_group["start_time"],
            end_timestamp=raw_group["end_time"],
            last_processed_at=datetime.utcnow(),
            # Set defaults for required fields
            time_range=f"{raw_group['start_time'].strftime('%H:%M')}-{raw_group['end_time'].strftime('%H:%M')}",
            duration_minutes=int(
                (raw_group["end_time"] - raw_group["start_time"]).total_seconds() / 60
            ),
            location="unspecified",
            mood_labels=["neutral"],
            mood_score=50,  # Neutral on 1-100 scale
            stress_level=50,  # Neutral on 1-100 scale
            energy_level=50,  # Neutral on 1-100 scale
            activity_type="unknown",
            people_involved=[],
            interaction_dynamic="solo",
            inferred_impact_on_user_name="neutral",
            topic_labels=["general"],
            one_sentence_summary=response.event_summary,
            first_person_narrative=response.event_story,
            action_item="N/A",
        )

        return event

    async def _continue_ongoing_event(
        self, ongoing_event: EventAnalysis, raw_group: Dict[str, Any], username: str
    ) -> EventAnalysis:
        """
        Type 3b: Continue an ongoing event with new content.
        """
        # Load and format prompt
        with open("src/nirva_service/prompts/continue_ongoing.md", "r") as f:
            prompt_template = f.read()

        prompt = prompt_template.format(
            previous_title=ongoing_event.event_title or "Ongoing Activity",
            previous_summary=(
                ongoing_event.event_summary
                or ongoing_event.one_sentence_summary
                or "An activity is in progress"
            ),
            previous_story=(
                ongoing_event.event_story
                or ongoing_event.first_person_narrative
                or "Activity details not available"
            ),
            new_transcript=raw_group.get("text", ""),
        )

        # Call LLM
        response = await self._call_llm_structured(prompt, OngoingEventOutput, username)

        # Update event
        ongoing_event.event_title = response.event_title
        ongoing_event.event_summary = response.event_summary
        ongoing_event.event_story = response.event_story
        ongoing_event.end_timestamp = raw_group["end_time"]
        ongoing_event.last_processed_at = datetime.utcnow()
        ongoing_event.one_sentence_summary = response.event_summary
        ongoing_event.first_person_narrative = response.event_story

        # Update time range and duration
        if ongoing_event.start_timestamp and ongoing_event.end_timestamp:
            ongoing_event.time_range = f"{ongoing_event.start_timestamp.strftime('%H:%M')}-{ongoing_event.end_timestamp.strftime('%H:%M')}"
            ongoing_event.duration_minutes = int(
                (
                    ongoing_event.end_timestamp - ongoing_event.start_timestamp
                ).total_seconds()
                / 60
            )

        return ongoing_event

    async def _complete_event(
        self, ongoing_event: EventAnalysis, new_transcript: Optional[str] = None,
        username: str = "unknown"
    ) -> Optional[EventAnalysis]:
        """
        Type 3c: Complete an event.
        Returns None if event should be dropped.
        """
        # Pre-filter: Check actual transcript content volume only
        transcript_text = new_transcript or ""
        
        # Also check if ongoing_event has stored transcriptions
        if hasattr(ongoing_event, 'transcriptions') and ongoing_event.transcriptions:
            for trans in ongoing_event.transcriptions:
                if isinstance(trans, dict) and 'text' in trans:
                    transcript_text += " " + trans.get('text', '')
        
        # Count words in actual transcriptions only
        word_count = len(transcript_text.split())
        
        # Count transcript segments
        segment_count = 0
        if new_transcript:
            segment_count += 1  # Current new transcript
        if hasattr(ongoing_event, 'transcriptions') and ongoing_event.transcriptions:
            segment_count += len(ongoing_event.transcriptions)
        
        # Track if this should be dropped locally
        should_drop_locally = word_count < 20 and segment_count < 3
        
        if should_drop_locally:
            logger.info(f"❌ LOCAL_FILTER_DROP: Ongoing event {ongoing_event.event_id} will be dropped locally (words={word_count}, segments={segment_count})")
        else:
            logger.info(f"✅ LOCAL_FILTER_PASS: Ongoing event {ongoing_event.event_id} passed local filter (words={word_count}, segments={segment_count}), sending to LLM")
        
        # Load and format prompt
        with open("src/nirva_service/prompts/process_completed.md", "r") as f:
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
            previous_section=previous_section, new_section=new_section
        )

        # Call LLM
        logger.info(f"🤖 Sending ongoing event {ongoing_event.event_id} to LLM for completion...")
        response = await self._call_llm_structured(prompt, CompletedEventOutput, username)
        
        logger.info(f"✅ LLM_ACCEPT: Ongoing event {ongoing_event.event_id} accepted by LLM, completing event")

        # Update event with completed data
        ongoing_event.event_title = response.event_title
        ongoing_event.event_summary = response.event_summary
        ongoing_event.event_story = response.event_story
        ongoing_event.event_status = "dropped" if should_drop_locally else "completed"
        ongoing_event.location = response.location
        ongoing_event.people_involved = response.people_involved
        ongoing_event.activity_type = response.activity_type
        ongoing_event.mood_labels = response.mood_labels
        ongoing_event.mood_score = response.mood_score
        ongoing_event.stress_level = response.stress_level
        ongoing_event.energy_level = response.energy_level
        ongoing_event.interaction_dynamic = response.interaction_dynamic
        ongoing_event.inferred_impact_on_user_name = (
            response.inferred_impact_on_user_name
        )
        ongoing_event.topic_labels = response.topic_labels
        ongoing_event.action_item = response.action_item
        ongoing_event.last_processed_at = datetime.utcnow()
        ongoing_event.one_sentence_summary = response.event_summary
        ongoing_event.first_person_narrative = response.event_story

        return ongoing_event

    async def _create_completed_event(
        self, raw_group: Dict[str, Any], username: str
    ) -> Optional[EventAnalysis]:
        """
        Create a completed event directly from raw transcript group.
        This bypasses the ongoing stage and uses the completion prompt immediately.
        """
        transcript_text = raw_group.get("text", "")
        
        # Pre-filter: Check transcript content volume
        word_count = len(transcript_text.split())
        chunks_count = len(raw_group.get("chunks", []))
        time_range = f"{raw_group['start_time'].strftime('%H:%M:%S')}-{raw_group['end_time'].strftime('%H:%M:%S')}"
        
        logger.info(f"📊 Processing transcript group: {time_range}, {chunks_count} chunks, {word_count} words")
        logger.debug(f"📝 Transcript preview: {transcript_text[:100]}...")
        
        # Track if this should be dropped locally
        should_drop_locally = word_count < 20
        
        if should_drop_locally:
            logger.info(f"❌ LOCAL_FILTER_DROP: Group {time_range} will be dropped locally (words={word_count} < 20)")
        else:
            logger.info(f"✅ LOCAL_FILTER_PASS: Group {time_range} passed local filter, sending to LLM")
        
        # Load completion prompt template
        with open("src/nirva_service/prompts/process_completed.md", "r") as f:
            prompt_template = f.read()
        
        # Build prompt with transcript as new section
        new_section = f"""## New Transcript
{transcript_text}"""
        
        prompt = prompt_template.format(
            previous_section="", 
            new_section=new_section
        )
        
        # Inject user context
        prompt = inject_user_context(prompt, username)
        
        # Log the final prompt being sent to LLM for debugging
        logger.info(f"🔍 PROMPT_DEBUG: Final prompt for group {time_range} (first 300 chars):")
        logger.info(f"📄 PROMPT_DEBUG: {prompt[:300]}...")
        
        # Call LLM for completion analysis
        logger.info(f"🤖 Sending group {time_range} to LLM for analysis...")
        response = await self._call_llm_structured(prompt, CompletedEventOutput, username)
        
        logger.info(f"✅ LLM_ACCEPT: Group {time_range} accepted by LLM, creating event")
        
        # Create completed EventAnalysis object
        event = EventAnalysis(
            event_id=str(uuid.uuid4()),
            event_title=response.event_title,
            event_summary=response.event_summary,
            event_story=response.event_story,
            event_status="dropped" if should_drop_locally else "completed",
            start_timestamp=raw_group["start_time"],
            end_timestamp=raw_group["end_time"],
            last_processed_at=datetime.utcnow(),
            time_range=f"{raw_group['start_time'].strftime('%H:%M')}-{raw_group['end_time'].strftime('%H:%M')}",
            duration_minutes=int(
                (raw_group["end_time"] - raw_group["start_time"]).total_seconds() / 60
            ),
            location=response.location,
            mood_labels=response.mood_labels,
            mood_score=response.mood_score,
            stress_level=response.stress_level,
            energy_level=response.energy_level,
            activity_type=response.activity_type,
            people_involved=response.people_involved,
            interaction_dynamic=response.interaction_dynamic,
            inferred_impact_on_user_name=response.inferred_impact_on_user_name,
            topic_labels=response.topic_labels,
            one_sentence_summary=response.event_summary,
            first_person_narrative=response.event_story,
            action_item=response.action_item,
        )
        
        return event

    async def _call_llm_structured(self, prompt: str, response_model: Any, username: str) -> Any:
        """
        Call LLM with structured output using OpenAI's latest structured output API.
        """
        import os

        from openai import AsyncOpenAI

        # Create OpenAI client
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        try:
            # Prepare enhanced prompt with user context
            enhanced_prompt = inject_user_context(prompt, username)
            
            # Log the full prompt being sent to LLM for debugging
            logger.info(f"🔍 LLM_PROMPT_DEBUG: Sending prompt to {response_model.__name__} (first 400 chars):")
            logger.info(f"📄 LLM_PROMPT_DEBUG: {enhanced_prompt[:400]}...")
            
            # Use the latest structured output API with parse method
            completion = await client.beta.chat.completions.parse(
                model="gpt-4.1",  # Latest model supporting structured outputs
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that analyzes transcripts and returns structured data.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                response_format=response_model,
                temperature=0.1,
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
                    event_story="Something happened during this time period.",
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
                    mood_score=50,  # Neutral on 1-100 scale
                    stress_level=50,  # Neutral on 1-100 scale
                    energy_level=50,  # Neutral on 1-100 scale
                    interaction_dynamic="N/A",
                    inferred_impact_on_user_name="N/A",
                    topic_labels=["N/A"],
                    action_item="N/A",
                )

    async def _save_events(self, username: str, events: List[EventAnalysis]) -> None:
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

    async def _detect_reanalysis_range(
        self, username: str, raw_event_groups: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if delayed transcriptions fall between existing events and need re-analysis.
        
        Args:
            username: Username to check events for
            raw_event_groups: New transcript groups being processed
            
        Returns:
            Dictionary with reanalysis range info or None if no reanalysis needed
        """
        if not raw_event_groups:
            return None
            
        # Get all existing completed events for this user
        all_events = get_user_events(username)
        completed_events = [
            event for event in all_events 
            if event.event_status == "completed" and 
            hasattr(event, 'start_timestamp') and hasattr(event, 'end_timestamp') and
            event.start_timestamp and event.end_timestamp
        ]
        
        if not completed_events:
            # No existing events to consider for reanalysis
            return None
            
        # Sort events by start time (handle None values)
        completed_events.sort(key=lambda e: e.start_timestamp or datetime.min.replace(tzinfo=timezone.utc))
        
        # Find the time range of new transcript groups
        new_start = min(group["start_time"] for group in raw_event_groups)
        new_end = max(group["end_time"] for group in raw_event_groups)
        
        logger.info(f"🔍 REANALYSIS_CHECK: New transcripts range {new_start} to {new_end}")
        
        # Find events that might be affected by the new transcripts
        affected_events = []
        
        for event in completed_events:
            event_start = event.start_timestamp
            event_end = event.end_timestamp
            
            # Skip events with missing timestamps
            if not event_start or not event_end:
                continue
            
            # Ensure timezone-aware comparison
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)
            if new_start.tzinfo is None:
                new_start = new_start.replace(tzinfo=timezone.utc)
            if new_end.tzinfo is None:
                new_end = new_end.replace(tzinfo=timezone.utc)
            
            # Check if new transcripts fall within the gap threshold of existing events
            gap_before = (new_start - event_end).total_seconds()
            gap_after = (event_start - new_end).total_seconds()
            
            # Event is affected if:
            # 1. New transcripts start close to when this event ended (potential continuation)
            # 2. New transcripts end close to when this event started (potential prefix)
            # 3. New transcripts overlap with the event time range
            if (
                (0 <= gap_before <= self.raw_event_gap_seconds) or  # New starts after event ends (within gap)
                (0 <= gap_after <= self.raw_event_gap_seconds) or   # New ends before event starts (within gap)
                (new_start <= event_end and new_end >= event_start)  # Overlap
            ):
                affected_events.append(event)
                logger.info(f"🎯 AFFECTED_EVENT: {event.event_id} ({event_start} to {event_end}) affected by new transcripts")
        
        if not affected_events:
            logger.info("✅ NO_REANALYSIS: No existing events affected by new transcripts")
            return None
            
        # Determine the reanalysis range
        # Include all events that might be connected by the new transcripts
        range_start = min(
            min(event.start_timestamp for event in affected_events),
            new_start
        )
        range_end = max(
            max(event.end_timestamp for event in affected_events),
            new_end
        )
        
        # Extend range to include any events that fall within the expanded time window
        extended_affected = []
        for event in completed_events:
            event_start = event.start_timestamp
            event_end = event.end_timestamp
            
            # Skip events with missing timestamps
            if not event_start or not event_end:
                continue
                
            if event_start.tzinfo is None:
                event_start = event_start.replace(tzinfo=timezone.utc)
            if event_end.tzinfo is None:
                event_end = event_end.replace(tzinfo=timezone.utc)
                
            # Include event if it overlaps with the reanalysis range
            if event_start <= range_end and event_end >= range_start:
                extended_affected.append(event)
        
        logger.info(f"🔄 REANALYSIS_RANGE: {range_start} to {range_end} with {len(extended_affected)} affected events")
        
        return {
            "start_time": range_start,
            "end_time": range_end,
            "affected_events": extended_affected,
            "new_groups": raw_event_groups
        }

    async def _reprocess_time_range(
        self, username: str, reanalysis_range: Dict[str, Any]
    ) -> IncrementalAnalyzeResponse:
        """
        Re-process a time range by collecting all transcriptions and re-analyzing as a batch.
        
        Args:
            username: Username
            reanalysis_range: Dictionary containing affected events and new groups
            
        Returns:
            IncrementalAnalyzeResponse: Processing results
        """
        start_time = reanalysis_range["start_time"]
        end_time = reanalysis_range["end_time"]
        affected_events = reanalysis_range["affected_events"]
        new_groups = reanalysis_range["new_groups"]
        
        logger.info(f"🔄 REPROCESSING: Time range {start_time} to {end_time} with {len(affected_events)} existing events")
        
        # Step 1: Collect all transcriptions for this time range
        all_transcriptions = await self._collect_transcriptions_for_range(username, start_time, end_time)
        
        # Step 2: Combine existing transcriptions with new transcript groups
        combined_transcript_parts = []
        
        # Add existing transcriptions from the database
        for trans in all_transcriptions:
            if trans.transcription_text.strip():
                start_str = trans.start_time.isoformat()
                end_str = trans.end_time.isoformat()
                combined_transcript_parts.append(f"[{start_str}|{end_str}] {trans.transcription_text.strip()}")
        
        # Add new transcript groups (they're already parsed)
        for group in new_groups:
            if group.get("text", "").strip():
                start_str = group["start_time"].isoformat()
                end_str = group["end_time"].isoformat()
                combined_transcript_parts.append(f"[{start_str}|{end_str}] {group['text'].strip()}")
        
        if not combined_transcript_parts:
            logger.warning("No transcriptions found for reanalysis range")
            return IncrementalAnalyzeResponse(
                updated_events_count=0,
                new_events_count=0,
                total_events_count=await self._get_total_event_count(username),
                message="No transcriptions found for reanalysis"
            )
        
        # Sort by timestamp to maintain chronological order
        combined_transcript_parts.sort(key=lambda x: self._extract_start_time_from_transcript_line(x))
        combined_transcript = " ".join(combined_transcript_parts)
        
        logger.info(f"📋 REANALYSIS_INPUT: {len(combined_transcript_parts)} transcript segments for range {start_time} to {end_time}")
        
        # Step 3: Delete affected events (they will be replaced)
        logger.info(f"🗑️ DELETING: {len(affected_events)} existing events for re-analysis")
        await self._delete_events(username, [event.event_id for event in affected_events])
        
        # Step 4: Re-process the combined transcripts using completion analysis
        # Use the date from the start of the range
        date_str = start_time.strftime("%Y-%m-%d")
        
        # Parse and group the combined transcripts
        transcript_chunks = self._parse_transcript_with_times(combined_transcript)
        raw_event_groups_combined = self._group_into_raw_events(transcript_chunks, username)
        
        logger.info(f"📊 REANALYSIS_GROUPS: {len(transcript_chunks)} transcript chunks → {len(raw_event_groups_combined)} groups")
        
        # Step 5: Process all groups as completed events (no ongoing since this is historical)
        new_events = []
        for group in raw_event_groups_combined:
            event = await self._create_completed_event(group, username)
            if event:
                new_events.append(event)
        
        # Step 6: Save the new events
        await self._save_events(username, new_events)
        
        # Step 7: Get updated total count
        total_events = await self._get_total_event_count(username)
        
        logger.info(f"✅ REANALYSIS_COMPLETE: Created {len(new_events)} new events from reanalysis")
        
        return IncrementalAnalyzeResponse(
            updated_events_count=0,  # We deleted and recreated, so no "updates"
            new_events_count=len(new_events),
            total_events_count=total_events,
            message=f"Re-analyzed range {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}: {len(affected_events)} events deleted, {len(new_events)} events created"
        )

    async def _collect_transcriptions_for_range(
        self, username: str, start_time: datetime, end_time: datetime
    ) -> List[TranscriptionResultDB]:
        """
        Collect all transcriptions from the database for a given time range.
        
        Args:
            username: Username to filter transcriptions
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List of transcription results ordered by start time
        """
        db = SessionLocal()
        try:
            # Query transcriptions that overlap with the time range
            transcriptions = db.query(TranscriptionResultDB).filter(
                and_(
                    TranscriptionResultDB.username == username,
                    TranscriptionResultDB.start_time <= end_time,
                    TranscriptionResultDB.end_time >= start_time
                )
            ).order_by(TranscriptionResultDB.start_time).all()
            
            logger.info(f"📊 COLLECTED: {len(transcriptions)} transcriptions for range {start_time} to {end_time}")
            return transcriptions
            
        finally:
            db.close()

    def _extract_start_time_from_transcript_line(self, transcript_line: str) -> datetime:
        """
        Extract start time from a transcript line in format '[START_ISO|END_ISO] text'.
        
        Args:
            transcript_line: Line with timestamp prefix
            
        Returns:
            Parsed start time as datetime
        """
        import re
        
        try:
            # Extract timestamp from [START|END] format
            match = re.match(r'\[([^|]+)\|[^\]]+\]', transcript_line)
            if match:
                time_str = match.group(1)
                return self._parse_time_string(time_str)
            else:
                # Fallback: try to extract any timestamp
                match = re.match(r'\[([^\]]+)\]', transcript_line)
                if match:
                    time_str = match.group(1)
                    return self._parse_time_string(time_str)
        except Exception as e:
            logger.warning(f"Failed to extract time from transcript line '{transcript_line[:50]}...': {e}")
        
        # Fallback to current time if parsing fails
        return datetime.now(timezone.utc)

    async def _delete_events(self, username: str, event_ids: List[str]) -> None:
        """
        Delete events by their IDs from the events table.
        
        Args:
            username: Username (for verification)
            event_ids: List of event IDs to delete
        """
        if not event_ids:
            return
            
        db = SessionLocal()
        try:
            from ...db.pgsql_object import EventDB
            
            # Delete events with matching IDs and username (for security)
            deleted_count = db.query(EventDB).filter(
                and_(
                    EventDB.event_id.in_(event_ids),
                    EventDB.username == username
                )
            ).delete(synchronize_session=False)
            
            db.commit()
            logger.info(f"🗑️ DELETED: {deleted_count} events for user {username}")
            
        except Exception as e:
            logger.error(f"Failed to delete events: {e}")
            db.rollback()
            raise
        finally:
            db.close()
