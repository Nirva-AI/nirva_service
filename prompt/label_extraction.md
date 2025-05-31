# Label Extraction

## Step 2: Structured Event Analysis (JSON Output)

For each individual event identified in Step 1, generate a structured analysis in the following JSON format:

```json
[
  {
    "event_id": "unique_event_identifier_001",
    "event_title": "A concise, telegraphic summary of the event from user_name's perspective, like a personal log entry. Focus on the core activity, primary interactant(s) if any, and location. Do NOT use user_name's name or pronouns like 'I' or 'My'. Example: 'Picnic with Ash in park.' or 'Watched Summer Palace with Trent at Roxy Theatre.'",
    "time_range": "Approximate start and end time of the event (e.g., '07:00-07:30'). Infer from transcript timestamps if available, otherwise estimate duration and sequence.",
    "duration_minutes": 30,
    "location": "Where the event took place. **CRITICAL: Only use specific proper nouns for locations (e.g., 'Blue Bottle Coffee,' 'Roxy Theatre') if a name is explicitly spoken aloud by user_name or an interactant within the dialogue of that specific event's transcript segment.** If a name is not spoken, use a descriptive phrase based only on details from the transcript (e.g., 'a coffee shop,' 'a park in the South Bay,' 'a French-style patisserie,' 'Trent's car,' 'a Nepalese restaurant'). **Do NOT infer specific business names if they are not explicitly stated in the dialogue for that event. Do NOT use information from outside the direct transcript content of the event (like file names or external knowledge) to name a location.** For instance, if the transcript mentions 'we went to a Nepalese place,' the location should be 'a Nepalese restaurant,' NOT a specific named Nepalese restaurant unless that specific name is uttered in the dialogue of that event. Prioritize accuracy based on direct, spoken evidence within the event's dialogue.",
    "mood_labels": ["primary_mood", "secondary_mood", "tertiary_mood"],
    "mood_score": 7,
    "stress_level": 3,
    "energy_level": 8,
    "activity_type": "Categorize the event. Choose one: work, exercise, social, learning, self-care, chores, commute, meal, leisure, unknown.",
    "people_involved": ["Name1", "Name2"],
    "interaction_dynamic": "If social, describe the dynamic (e.g., 'collaborative', 'supportive', 'tense', 'neutral', 'instructional', 'one-sided'). If not social, use 'N/A'.",
    "inferred_impact_on_user_name": "For social interactions, infer if it seemed 'energizing', 'draining', or 'neutral' for user_name, based on their language, tone, and reactions. For non-social, use 'N/A'.",
    "topic_labels": ["primary_topic", "secondary_topic"],
    "one_sentence_summary": "From user_name's perspective, a brief description (30-100 words) of what I was doing, who I was with (if anyone), and the setting. Do NOT use user_name's name or pronouns like 'I' or 'My' unless absolutely natural within a direct reflection of a thought. Example: 'Long discussion with Ash at the park covering personal challenges and future plans.' or 'Quick bite at Mademoiselle Colette with Trent before the movie; pastries were underwhelming.'",
    "first_person_narrative": "A cohesive (50-400 words, depending on the richness and importance of the event) first-person narrative that sounds authentic to the user. Maintain user_name's language style, perspective, and vocabulary. Crucially, this narrative must ONLY include user_name's own reported actions, statements, thoughts, and feelings as directly evidenced or strongly inferred from user_name's speech in the transcript. Do not incorporate the speech, actions, or perspectives of other individuals as if they were user_name's. Capture signals/patterns of rumination, internal conflicts, anxiety, or stress within user_name, if any.",
    "action_item": "**Only include key action items, decisions, or reminders that user_name (e.g., Wei) personally stated she would do, needs to do, explicitly decided upon, or was directly tasked with and acknowledged. Do NOT include actions for other people, or general discussion points unless they translate into a direct, personal action or decision for user_name. If user_name is merely observing or discussing someone else's potential action, it's not an action item for her unless she then explicitly states a related personal task or commitment. If no such action item exists for user_name, use 'N/A'.**"
  }
]
```

### Field Descriptions

- **event_id**: Unique identifier (e.g., event_01, event_02)
- **duration_minutes**: Integer representing estimated duration
- **mood_labels**: Identify 1 to 3 mood labels that best describe user_name's personal mood during this event, based on their speech and reactions. Choose from: peaceful, energized, engaged, disengaged, happy, sad, anxious, stressed, relaxed, excited, bored, frustrated, content, neutral. The first label should be the most dominant mood for user_name. If only one strong mood is evident for user_name, use only that one label. If user_name's mood is unclear or mixed without a dominant feeling, use 'neutral'. These labels should reflect user_name's state, not the general atmosphere or the mood of other people involved, unless it clearly dictates user_name's mood.
- **mood_score**: Integer from 1 (very negative) to 10 (very positive) assessing user_name's overall mood during this event
- **stress_level**: Integer from 1 (very low stress) to 10 (very high stress) assessing user_name's stress level during this event
- **energy_level**: Integer from 1 (very low energy/drained) to 10 (very high energy/engaged) assessing user_name's energy level during this event
- **people_involved**: List names of the primary individuals user_name had significant, direct interactions with during the event. **Do NOT include user_name (e.g., Wei) herself in this list.** Exclude individuals involved only in brief, transactional service encounters (e.g., unnamed cafe staff, store clerks) unless the interaction became a more substantial part of the event's dialogue or activity. If user_name was alone or only had such brief encounters, use an empty array [].
- **topic_labels**: If a conversation, categorize the main topics (up to 2). Examples: 'technology', 'work', 'relationship', 'logistics'. If not a conversation, use 'N/A'.
