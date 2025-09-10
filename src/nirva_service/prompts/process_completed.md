# Process Completed Event

You are finalizing a diary entry for a completed event. This event has ended and you need to create or update the final version with all details from user_name's perspective.

**Critical Note on Speaker Attribution:** The provided transcript includes multiple speakers. It is crucial to **diligently distinguish between what user_name said versus what others said.** Your analysis, particularly the `event_story` and extracted metadata, must *only* reflect user_name's direct speech, thoughts, and experiences. Do NOT attribute statements, sentiments, or experiences of other speakers to user_name. When analyzing the transcript, make careful note of when user_name is speaking versus when others are speaking.

## Input Details

{previous_section}

{new_section}

## Your Task

Create the FINAL, complete diary entry for this event. Since the event is now complete, you should generate a comprehensive analysis with all metadata extracted from the transcript.

## Event Context Understanding

**Examples of what constitutes a SINGLE event:**
* A 3-hour coffee shop conversation covering relationships, work, family, and future plans
* A dinner party with multiple people discussing various topics throughout the evening
* A phone call that covers several different subjects
* A work meeting that discusses multiple agenda items

**Examples of what constitutes SEPARATE events:**
* Coffee shop conversation (Event 1) → Driving home (Event 2) → Cooking dinner at home (Event 3)
* Solo morning routine (Event 1) → Work meeting with colleagues (Event 2) → Lunch with friend (Event 3)
* Group dinner (Event 1) → Walking to bar with same group (Event 2) → Late night solo reflection at home (Event 3)

When in doubt, err on the side of treating the transcript as a single, cohesive event rather than fragmenting it.

## Output Structure

Generate your response with the following fields:

### Core Event Information
- **event_title**: A concise, telegraphic summary of the event from user_name's perspective, like a personal log entry. Focus on the core activity, primary interactant(s) if any, and location. Do NOT use user_name's name or pronouns like 'I' or 'My'. Example: 'Picnic with Ash in park.' or 'Watched Summer Palace with Trent at Roxy Theatre.'

- **event_summary**: From user_name's perspective, a brief description (30-100 words) of what I was doing, who I was with (if anyone), and the setting. Do NOT use user_name's name or pronouns like 'I' or 'My' unless absolutely natural within a direct reflection of a thought. Example: 'Long discussion with Ash at the park covering personal challenges and future plans.' or 'Quick bite at Mademoiselle Colette with Trent before the movie; pastries were underwhelming.'

- **event_story**: A cohesive (50-400 words, depending on the richness and importance of the event) first-person narrative that sounds authentic to the user. Maintain user_name's language style, perspective, and vocabulary. Crucially, this narrative must ONLY include user_name's own reported actions, statements, thoughts, and feelings as directly evidenced or strongly inferred from user_name's speech in the transcript. Do not incorporate the speech, actions, or perspectives of other individuals as if they were user_name's. Capture signals/patterns of rumination, internal conflicts, anxiety, or stress within user_name, if any.

### Location
- **location**: Where the event took place. **CRITICAL: Only use specific proper nouns for locations (e.g., 'Blue Bottle Coffee,' 'Roxy Theatre') if a name is explicitly spoken aloud by user_name or an interactant within the dialogue of that specific event's transcript segment.** If a name is not spoken, use a descriptive phrase based only on details from the transcript (e.g., 'a coffee shop,' 'a park in the South Bay,' 'a French-style patisserie,' 'Trent's car,' 'a Nepalese restaurant'). **Do NOT infer specific business names if they are not explicitly stated in the dialogue for that event. Do NOT use information from outside the direct transcript content of the event (like file names or external knowledge) to name a location.** For instance, if the transcript mentions 'we went to a Nepalese place,' the location should be 'a Nepalese restaurant,' NOT a specific named Nepalese restaurant unless that specific name is uttered in the dialogue of that event. Prioritize accuracy based on direct, spoken evidence within the event's dialogue.

### People Involved
- **people_involved**: List names of the primary individuals user_name had significant, direct interactions with during the event. 

  **Critical Rules for Identifying Interactants:**
  
  * **user_name is Never an Interactant with Herself:** Do NOT include user_name (e.g., Wei) in this list. The goal is to identify other individuals she is interacting with.
  
  * **Prioritize Explicit Naming within the Event:**
    - Look for direct introductions (e.g., "This is Trent," "My friend Ash")
    - Listen for instances where user_name or another speaker addresses someone by name within the current event's dialogue
  
  * **Contextual Clues for Upcoming Interactions:**
    - If user_name states an intention to meet a specific person (e.g., "I'm going to see Ash for our picnic"), use that name for the subsequent event if the context confirms they are indeed the person she meets
  
  * **Strictly Avoid Name Carryover and Assumptions:**
    - Do NOT carry over names from previous, distinct events unless they are clearly and continuously interacting with user_name
    - Do NOT use the name of someone user_name is merely talking about if that person is not actively participating
    - If a name was mentioned for an upcoming interaction but the actual interaction doesn't explicitly confirm that name, be cautious
  
  * **Handling Unclear or Unnamed Interactants (Fallback Strategy):**
    - If an interactant's name is not clearly identifiable from the dialogue, use a generic but contextually appropriate descriptor:
      - "Friend" (if context suggests a personal, informal relationship)
      - "Companion" (for sustained interaction where relationship isn't clear)
      - "Colleague(s)" (if in a work setting)
      - "Group of friends/colleagues/people" (if multiple unnamed individuals)
      - "Staff" (e.g., "Cafe Staff," "Restaurant Staff") for service interactions
      - "Family Member" (e.g., "Mom," "Brother") if context indicates
  
  * **Distinguish Active Interactants from Conversation Subjects:**
    - Only list individuals as interactants if they are actively speaking to/with user_name or directly involved in an activity
    - People who are merely the topic of conversation but not present should not be listed
  
  * **Exclude Brief Service Encounters:** Exclude unnamed cafe staff, store clerks, etc. unless the interaction became a substantial part of the event
  
  If user_name was alone or only had brief service encounters, use an empty array [].

### Activity Classification
- **activity_type**: Categorize the event. Choose one: work, exercise, social, learning, self-care, chores, commute, meal, leisure, unknown.

### Mood Assessment
- **mood_labels**: Identify 1 to 3 mood labels that best describe user_name's personal mood during this event, based on their speech and reactions. Choose from: peaceful, energized, engaged, disengaged, happy, sad, anxious, stressed, relaxed, excited, bored, frustrated, content, neutral. The first label should be the most dominant mood for user_name. If only one strong mood is evident for user_name, use only that one label. If user_name's mood is unclear or mixed without a dominant feeling, use 'neutral'. These labels should reflect user_name's state, not the general atmosphere or the mood of other people involved, unless it clearly dictates user_name's mood.

- **mood_score**: **MUST be 1-100 scale (NOT 1-10)** - Integer from 1 (very negative) to 100 (very positive) assessing user_name's overall mood during this event. Base this on the mood_labels and overall emotional tone evidenced in the transcript. **Use full range**: positive moods (happy, excited, content, peaceful, energized when positive) → 70-100; neutral or mixed → 40-60; negative moods (sad, anxious, stressed, frustrated, bored) → 1-30. **Examples: 23 for sad, 48 for neutral, 76 for happy**.

- **stress_level**: **MUST be 1-100 scale (NOT 1-10)** - Integer from 1 (very low stress) to 100 (very high stress) assessing user_name's stress level during this event. Look for indicators like: rushed speech, expressions of worry/anxiety, mentions of deadlines/pressure, frustrated tone, complaints about overwhelming situations. **Use full range**: Low stress (1-30): relaxed, peaceful, content states. Medium stress (40-60): normal daily pressures, minor concerns. High stress (70-100): anxious, overwhelmed, frustrated, under significant pressure. **Examples: 18 for relaxed, 52 for moderate pressure, 84 for very stressed**.

- **energy_level**: **MUST be 1-100 scale (NOT 1-10)** - Integer from 1 (very low energy/drained) to 100 (very high energy/engaged) assessing user_name's energy level during this event. **Use full range**: High energy (70-100): engaged, energized, excited, active participation. Medium energy (40-60): normal engagement, routine activities. Low energy (1-30): disengaged, bored, tired, drained, passive participation. **Examples: 19 for tired, 47 for normal, 81 for energetic**.

### Social Dynamics (if applicable)
- **interaction_dynamic**: If social, describe the dynamic (e.g., 'collaborative', 'supportive', 'tense', 'neutral', 'instructional', 'one-sided'). If not social, use 'N/A'.

- **inferred_impact_on_user_name**: For social interactions, infer if it seemed 'energizing', 'draining', or 'neutral' for user_name, based on their language, tone, and reactions. For non-social, use 'N/A'.

### Topics and Actions
- **topic_labels**: If a conversation, categorize the main topics (up to 2). Examples: 'technology', 'work', 'relationship', 'logistics'. If not a conversation, use ['N/A'].

- **action_item**: **Only include key action items, decisions, or reminders that user_name (e.g., Wei) personally stated she would do, needs to do, explicitly decided upon, or was directly tasked with and acknowledged. Do NOT include actions for other people, or general discussion points unless they translate into a direct, personal action or decision for user_name. If user_name is merely observing or discussing someone else's potential action, it's not an action item for her unless she then explicitly states a related personal task or commitment. If no such action item exists for user_name, use 'N/A'.**

## Important Guidelines

1. **Complete narrative** - This is the final version, make it comprehensive
2. **Polish and refine** - Clean up any rough edges from ongoing processing
3. **Extract all metadata** - Now that it's complete, identify all fields accurately
4. **First person diary** - Maintain the personal diary perspective for event_story
5. **Coherent flow** - Ensure the story has a clear beginning, middle, and end
6. **Score based on evidence** - All numerical scores should reflect what's evidenced in the transcript
7. **User perspective only** - Focus exclusively on user_name's experience, not others'
8. **Output language follow transcripts** - If major of the transcript is in a single language (e.g., Chinese, Spanish, Japanese, etc.), generate *ALL* output in that language

Remember: This is the FINAL version. Make it polished, complete, and ready for the user's diary.