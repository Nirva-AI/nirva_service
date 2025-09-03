from typing import List, Literal, Optional, final
from datetime import datetime

from pydantic import BaseModel, Field

from .registry import register_base_model_class


###############################################################################################################################################
@final
@register_base_model_class
class EventAnalysis(BaseModel):
    event_id: str = Field(description="Unique identifier (e.g., event_01, event_02)")
    event_title: str = Field(
        description="A concise, telegraphic summary of the event from user_name's perspective, like a personal log entry. Focus on the core activity, primary interactant(s) if any, and location. Do NOT use user_name's name or pronouns like 'I' or 'My'. Example: 'Picnic with Ash in park.' or 'Watched Summer Palace with Trent at Roxy Theatre.'"
    )
    time_range: str = Field(
        description="Approximate start and end time of the event (e.g., '07:00-07:30'). Infer from transcript timestamps if available, otherwise estimate duration and sequence."
    )
    duration_minutes: int = Field(description="Integer representing estimated duration")
    location: str = Field(
        description="Where the event took place. **CRITICAL: Only use specific proper nouns for locations (e.g., 'Blue Bottle Coffee,' 'Roxy Theatre') if a name is explicitly spoken aloud by user_name or an interactant within the dialogue of that specific event's transcript segment.** If a name is not spoken, use a descriptive phrase based only on details from the transcript (e.g., 'a coffee shop,' 'a park in the South Bay,' 'a French-style patisserie,' 'Trent's car,' 'a Nepalese restaurant'). **Do NOT infer specific business names if they are not explicitly stated in the dialogue for that event. Do NOT use information from outside the direct transcript content of the event (like file names or external knowledge) to name a location.** For instance, if the transcript mentions 'we went to a Nepalese place,' the location should be 'a Nepalese restaurant,' NOT a specific named Nepalese restaurant unless that specific name is uttered in the dialogue of that event. Prioritize accuracy based on direct, spoken evidence within the event's dialogue."
    )
    mood_labels: List[str] = Field(
        description="Identify 1 to 3 mood labels that best describe user_name's personal mood during this event, based on their speech and reactions. Choose from: peaceful, energized, engaged, disengaged, happy, sad, anxious, stressed, relaxed, excited, bored, frustrated, content, neutral. The first label should be the most dominant mood for user_name. If only one strong mood is evident for user_name, use only that one label. If user_name's mood is unclear or mixed without a dominant feeling, use 'neutral'. These labels should reflect user_name's state, not the general atmosphere or the mood of other people involved, unless it clearly dictates user_name's mood."
    )
    mood_score: int = Field(
        description="Integer from 1 (very negative) to 10 (very positive) assessing user_name's overall mood during this event"
    )
    stress_level: int = Field(
        description="Integer from 1 (very low stress) to 10 (very high stress) assessing user_name's stress level during this event"
    )
    energy_level: int = Field(
        description="Integer from 1 (very low energy/drained) to 10 (very high energy/engaged) assessing user_name's energy level during this event"
    )
    activity_type: Literal[
        "work",
        "exercise",
        "social",
        "learning",
        "self-care",
        "chores",
        "commute",
        "meal",
        "leisure",
        "unknown",
    ] = Field(
        description="Categorize the event. Choose one: work, exercise, social, learning, self-care, chores, commute, meal, leisure, unknown."
    )
    people_involved: List[str] = Field(
        description="List names of the primary individuals user_name had significant, direct interactions with during the event. **Do NOT include user_name (e.g., Wei) herself in this list.** Exclude individuals involved only in brief, transactional service encounters (e.g., unnamed cafe staff, store clerks) unless the interaction became a more substantial part of the event's dialogue or activity. If user_name was alone or only had such brief encounters, use an empty array []."
    )
    interaction_dynamic: str = Field(
        description="If social, describe the dynamic (e.g., 'collaborative', 'supportive', 'tense', 'neutral', 'instructional', 'one-sided'). If not social, use 'N/A'."
    )
    inferred_impact_on_user_name: str = Field(
        description="For social interactions, infer if it seemed 'energizing', 'draining', or 'neutral' for user_name, based on their language, tone, and reactions. For non-social, use 'N/A'."
    )
    topic_labels: List[str] = Field(
        description="If a conversation, categorize the main topics (up to 2). Examples: 'technology', 'work', 'relationship', 'logistics'. If not a conversation, use 'N/A'."
    )
    one_sentence_summary: str = Field(
        description="From user_name's perspective, a brief description (30-100 words) of what I was doing, who I was with (if anyone), and the setting. Do NOT use user_name's name or pronouns like 'I' or 'My' unless absolutely natural within a direct reflection of a thought. Example: 'Long discussion with Ash at the park covering personal challenges and future plans.' or 'Quick bite at Mademoiselle Colette with Trent before the movie; pastries were underwhelming.'"
    )
    first_person_narrative: str = Field(
        description="A cohesive (50-400 words, depending on the richness and importance of the event) first-person narrative that sounds authentic to the user. Maintain user_name's language style, perspective, and vocabulary. Crucially, this narrative must ONLY include user_name's own reported actions, statements, thoughts, and feelings as directly evidenced or strongly inferred from user_name's speech in the transcript. Do not incorporate the speech, actions, or perspectives of other individuals as if they were user_name's. Capture signals/patterns of rumination, internal conflicts, anxiety, or stress within user_name, if any."
    )
    action_item: str = Field(
        description="**Only include key action items, decisions, or reminders that user_name (e.g., Wei) personally stated she would do, needs to do, explicitly decided upon, or was directly tasked with and acknowledged. Do NOT include actions for other people, or general discussion points unless they translate into a direct, personal action or decision for user_name. If user_name is merely observing or discussing someone else's potential action, it's not an action item for her unless she then explicitly states a related personal task or commitment. If no such action item exists for user_name, use 'N/A'.**"
    )
    
    # New fields for ongoing/completed event processing
    event_status: Literal["ongoing", "completed"] = Field(
        default="completed",
        description="Status of the event - 'ongoing' if still being processed, 'completed' when finalized"
    )
    event_story: Optional[str] = Field(
        default=None,
        description="Full diary-style narrative of the event, combining all details into a coherent story"
    )
    event_summary: Optional[str] = Field(
        default=None,
        description="Brief 1-2 sentence summary of the event's key activities and outcomes"
    )
    start_timestamp: Optional[datetime] = Field(
        default=None,
        description="Actual start timestamp of the event (UTC)"
    )
    end_timestamp: Optional[datetime] = Field(
        default=None,
        description="Actual end timestamp of the event (UTC)"
    )
    last_processed_at: Optional[datetime] = Field(
        default=None,
        description="Last time this event was processed by LLM"
    )


###############################################################################################################################################
# Structured output models for the new incremental analyzer
@final
@register_base_model_class
class OngoingEventOutput(BaseModel):
    """LLM output structure for ongoing events"""
    event_title: str = Field(
        description="Brief, descriptive title of the event (5-10 words)"
    )
    event_summary: str = Field(
        description="1-2 sentence summary of what's happening in this event"
    )
    event_story: str = Field(
        description="Full narrative diary entry of the event from user's perspective (50-500 words)"
    )


@final
@register_base_model_class
class CompletedEventOutput(BaseModel):
    """LLM output structure for completed events"""
    event_title: str = Field(
        description="Final, polished title of the completed event (5-10 words)"
    )
    event_summary: str = Field(
        description="Complete 1-2 sentence summary of what happened in this event"
    )
    event_story: str = Field(
        description="Final, comprehensive narrative diary entry of the entire event (100-800 words)"
    )
    location: str = Field(
        description="Where the event took place, based on context clues from the transcript"
    )
    people_involved: List[str] = Field(
        description="List of people mentioned or involved in the event (names or roles)"
    )
    activity_type: Literal[
        "work", "exercise", "social", "learning", "self-care", 
        "chores", "commute", "meal", "leisure", "unknown"
    ] = Field(
        description="Category of the event activity"
    )
    mood_labels: List[str] = Field(
        description="1-3 mood descriptors from: peaceful, energized, engaged, disengaged, happy, sad, anxious, stressed, relaxed, excited, bored, frustrated, content, neutral"
    )
    mood_score: int = Field(
        description="Overall mood score from 1 (very negative) to 10 (very positive)",
        ge=1,
        le=10
    )


###############################################################################################################################################
@final
@register_base_model_class
class LabelExtractionResponse(BaseModel):
    events: List[EventAnalysis] = Field(
        description="A list of structured event analyses, each containing detailed information about a specific event in user_name's day."
    )


###############################################################################################################################################
@final
@register_base_model_class
class Gratitude(BaseModel):
    gratitude_summary: List[str] = Field(
        description="3 bullet points of gratitude, each <50 words"
    )
    gratitude_details: str = Field(
        description="What user_name is genuinely grateful for, qualities admired in others"
    )
    win_summary: List[str] = Field(
        description="3 celebration points highlighting successes, each <50 words"
    )
    win_details: str = Field(description="Successes and wins, big and small")
    feel_alive_moments: str = Field(
        description="Magical or meaningful moments, unexpected joys, connections, insights"
    )


###############################################################################################################################################
@final
@register_base_model_class
class ChallengesAndGrowth(BaseModel):
    growth_summary: List[str] = Field(description="3 improvement areas, each <50 words")
    obstacles_faced: str = Field(
        description="External challenges and internal struggles"
    )
    unfinished_intentions: str = Field(
        description="What user_name intended to accomplish but didn't"
    )
    contributing_factors: str = Field(
        description="Patterns: time management, energy, priorities, circumstances"
    )


###############################################################################################################################################
@final
@register_base_model_class
class LearningAndInsights(BaseModel):
    new_knowledge: str = Field(
        description="Technical learning, creative techniques, practical skills, fresh perspectives"
    )
    self_discovery: str = Field(
        description="New strengths, patterns, emotional responses, preferences"
    )
    insights_about_others: str = Field(
        description="Insights about colleagues, friends, family, strangers"
    )
    broader_lessons: str = Field(
        description="Lessons about work, relationships, life, world"
    )


###############################################################################################################################################
@final
@register_base_model_class
class ConnectionsAndRelationships(BaseModel):
    meaningful_interactions: str = Field(
        description="Quality and impact of interactions beyond just names"
    )
    notable_about_people: str = Field(
        description="New perspectives, admired qualities, surprises"
    )
    follow_up_needed: str = Field(
        description="Who deserves attention: to thank, update, ask questions, give feedback"
    )


###############################################################################################################################################
@final
@register_base_model_class
class LookingForward(BaseModel):
    do_differently_tomorrow: str = Field(
        description="Based on today's experiences and lessons"
    )
    continue_what_worked: str = Field(
        description="Successful strategies, positive habits, effective approaches"
    )
    top_3_priorities_tomorrow: List[str] = Field(
        description="Specific, achievable priorities connected to larger goals"
    )


###############################################################################################################################################
@final
@register_base_model_class
class DailyReflection(BaseModel):
    reflection_summary: str = Field(
        description="How the day unfolded overall, <50 words"
    )
    gratitude: Gratitude = Field(
        description="Reflections on gratitude, wins, and meaningful moments"
    )
    challenges_and_growth: ChallengesAndGrowth = Field(
        description="Reflections on challenges, growth opportunities, and unfinished tasks"
    )
    learning_and_insights: LearningAndInsights = Field(
        description="New knowledge, personal discoveries, and broader lessons"
    )
    connections_and_relationships: ConnectionsAndRelationships = Field(
        description="Analysis of social interactions and relationships"
    )
    looking_forward: LookingForward = Field(
        description="Plans and priorities for tomorrow"
    )


###############################################################################################################################################
@final
@register_base_model_class
class ReflectionResponse(BaseModel):
    daily_reflection: DailyReflection = Field(
        description="A comprehensive reflection on user_name's day, including gratitude, challenges, learnings, connections, and forward-looking plans"
    )


###############################################################################################################################################
