from pydantic import BaseModel, SecretStr, Field
from typing import List, Dict, Literal, final
import json


###############################################################################################################################################
def user_session_system_message(username: str, display_name: str) -> str:
    """生成用户会话的系统消息"""
    return f"""# You are Nirva, an AI journaling and life coach assistant. Your purpose is to help the user (user_name: {display_name}) remember and reflect on their day with warmth, clarity, and emotional intelligence."""


###############################################################################################################################################
def user_session_chat_message(username: str, display_name: str, content: str) -> str:
    """生成用户会话的聊天消息"""

    return f"""# This is a conversation message from {display_name}
    Content: {content}"""


###############################################################################################################################################


###############################################################################################################################################
def event_segmentation_message() -> str:
    return r"""# Event Segmentation

You will analyze a transcript of `user_name`'s day to provide insights and summaries. Your goal is to understand what happened and how the user felt throughout the day. Help them remember what's important to them and also guide them with personalized insight.

## Input Transcript

The following is a transcript from an audio recording of `user_name`'s day, including `user_name`'s speech and audible interactions, presented in chronological order.

**Critical Note on Speaker Attribution:** The provided transcript includes multiple speakers. It is crucial to **diligently distinguish between what `user_name` (e.g., Wei) said versus what others said.** Your analysis, particularly the `first_person_narrative` and `key_quote_or_moment`, must *only* reflect `user_name`'s direct speech, thoughts, and experiences. Do NOT attribute statements, sentiments, or experiences of other speakers to `user_name`. During your initial read-through in Step 1, make an internal note or mental flag whenever user_name is speaking versus when others are speaking. This will be crucial for accurate attribution in Step 2.

## Your Task

### Step 1: Transcript Segmentation and Context Identification

Carefully read the provided transcript. Divide it into distinct, meaningful events or episodes. An event represents a continuous period of time where the core context remains consistent.

Identify context shifts based on **MAJOR** changes only:

* Changes in location (moving from home to coffee shop, office to restaurant, etc.)
* Changes in people `user_name` is interacting with (switching from talking to Friend A to Friend B, or from group conversation to solo activity)
* Changes in core activity type (switching from work meeting to exercise, from social gathering to commute, etc.)
* Significant time gaps (clear breaks of 30+ minutes)

**Do NOT** create separate events for:

* Changes in conversation topics within the same interaction
* Brief interruptions or tangents during continuous activities
* Moving between closely related activities in the same location (e.g., eating then talking at the same restaurant)
* Natural flow of conversation between different subjects

**Examples of what constitutes a SINGLE event:**

* A 3-hour coffee shop conversation covering relationships, work, family, and future plans
* A dinner party with multiple people discussing various topics throughout the evening
* A phone call that covers several different subjects
* A work meeting that discusses multiple agenda items

**Examples of what constitutes SEPARATE events:**

* Coffee shop conversation (Event 1) → Driving home (Event 2) → Cooking dinner at home (Event 3)
* Solo morning routine (Event 1) → Work meeting with colleagues (Event 2) → Lunch with friend (Event 3)
* Group dinner (Event 1) → Walking to bar with same group (Event 2) → Late night solo reflection at home (Event 3)

When in doubt, err on the side of fewer, longer events rather than many short ones.

#### Identifying Primary Interactant(s) - Revised and Clarified Instructions

For each event, meticulously identify the Primary Interactant(s). These are the individual(s) `user_name` is directly speaking with or actively engaged in an activity with during that specific event segment.

**`user_name` is the Narrator, Not an Interactant with Herself:**

* You will be provided with `user_name`'s actual name (e.g., Wei). `user_name` is the central individual whose activities are being logged.
* **Crucially**, `user_name` (e.g., Wei) should **never** be listed as a Primary Interactant with herself. The goal is to identify other individuals she is interacting with.

**Prioritize Explicit Naming within the Event:**

* Look for direct introductions (e.g., "This is Trent," "My friend Ash").
* Listen for instances where `user_name` or another speaker addresses someone by name within the current event's dialogue.

**Contextual Clues for Upcoming Interactions:**

* If `user_name` states an intention to meet a specific person for an upcoming event (e.g., "I'm going to see Ash for our picnic," or "I'm meeting Trent for a movie"), use that name for the subsequent event if the context confirms they are indeed the person she meets.

**Strictly Avoid Name Carryover and Assumptions:**

* Do **NOT** carry over names of individuals from previous, distinct events unless they are clearly and continuously interacting with `user_name` into the new event.
* Do **NOT** use the name of someone `user_name` is merely talking about if that person is not actively participating in the current interaction.
* If a name was mentioned for an upcoming interaction but the actual interaction doesn't explicitly confirm that name, be cautious.

**Handling Unclear, Ambiguous, or Unnamed Interactants (Fallback Strategy):**

* If an interactant's specific name is not clearly and unambiguously identifiable from the direct dialogue or immediate context of that specific event segment:
  * Do **NOT** guess a name.
  * Do **NOT** borrow a name from a different context, a person merely mentioned, or `user_name` herself.
  * Instead, use a generic but contextually appropriate descriptor. Examples:
    * "Friend" (if context suggests a personal, informal one-on-one relationship)
    * "Companion" (for a sustained one-on-one interaction where the specific relationship isn't clear but "Friend" feels appropriate, and no name is evident)
    * "Colleague(s)" (if in a work setting)
    * "Group of friends/colleagues/people" (if multiple unnamed individuals are interacting with `user_name` simultaneously)
    * "Staff" (e.g., "Cafe Staff," "Restaurant Staff," "Store Clerk") for service interactions.
    * "Family Member" (if context indicates, e.g., "Mom," "Brother," without a specific name being used in that segment).

* The primary goal is accuracy based only on the information present for that event. It is better to use an accurate generic term (like "Friend" or "Companion") than an incorrect specific name.

**Distinguish Between Active Interactants and Subjects of Conversation:**

* Only list individuals as Primary Interactant(s) if they are actively speaking to or with `user_name`, or are directly involved in an activity with `user_name` during that event segment.
* People who are merely the topic of conversation but not present and participating should not be listed as interactants for that segment."""


###############################################################################################################################################


def transcript_message(formatted_date: str, transcript_content: str) -> str:

    return f"""# Transcript
## Date: {formatted_date}
## Content
{transcript_content}"""


###############################################################################################################################################


@final
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


###############################################################################################################################################
@final
class LabelExtractionResponse(BaseModel):
    events: List[EventAnalysis] = Field(
        description="A list of structured event analyses, each containing detailed information about a specific event in user_name's day."
    )


###############################################################################################################################################
def label_extraction_message() -> str:

    label_extraction_schema = LabelExtractionResponse.model_json_schema()

    # 美化 JSON 输出
    schema_json = json.dumps(label_extraction_schema)

    return f"""# Label Extraction

## Step 2: Structured Event Analysis (JSON Output)

For each individual event identified in Step 1, generate a structured analysis that conforms to the following schema:

```json
{schema_json}
```"""


###############################################################################################################################################


@final
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
class ReflectionResponse(BaseModel):
    daily_reflection: DailyReflection = Field(
        description="A comprehensive reflection on user_name's day, including gratitude, challenges, learnings, connections, and forward-looking plans"
    )


###############################################################################################################################################
def reflection_message() -> str:
    import json

    # 获取 ReflectionResponse 的 JSON schema
    reflection_schema = ReflectionResponse.model_json_schema()

    # 美化 JSON 输出
    schema_json = json.dumps(reflection_schema)

    return f"""# Reflection

## Step 3: Generate daily reflection based on what happened and how the user felt throughout the day (JSON Output)

Based on the events analyzed in Step 2, generate a comprehensive daily reflection that conforms to the following schema:

```json
{schema_json}
```"""


###############################################################################################################################################
