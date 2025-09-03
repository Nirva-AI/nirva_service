# Process Completed Event

You are finalizing a diary entry for a completed event. This event has ended and you need to create or update the final version with all details.

## Input Details

{previous_section}

{new_section}

## Your Task

Create the FINAL, complete diary entry for this event. Since the event is now complete, you should:
1. Create a polished, final title
2. Write a comprehensive summary
3. Craft the complete story with all details
4. Extract key metadata (location, people, mood, etc.)

## Output Requirements

Provide a JSON response with the following structure:

```json
{{
  "event_title": "Final polished title (5-10 words)",
  "event_summary": "Complete 1-2 sentence summary of what happened",
  "event_story": "Final comprehensive diary entry (100-800 words)",
  "location": "Where this took place (be specific if mentioned, general if not)",
  "people_involved": ["List of people mentioned or involved"],
  "activity_type": "work|exercise|social|learning|self-care|chores|commute|meal|leisure|unknown",
  "mood_labels": ["1-3 mood descriptors: peaceful, energized, engaged, disengaged, happy, sad, anxious, stressed, relaxed, excited, bored, frustrated, content, neutral"],
  "mood_score": 7
}}
```

## Important Guidelines

1. **Complete narrative** - This is the final version, make it comprehensive
2. **Polish and refine** - Clean up any rough edges from ongoing processing
3. **Extract metadata** - Now that it's complete, identify location, people, mood
4. **First person diary** - Maintain the personal diary perspective
5. **Coherent flow** - Ensure the story has a clear beginning, middle, and end
6. **Activity categorization** - Choose the most fitting activity type
7. **Mood assessment** - Evaluate the overall emotional tone (1=very negative, 10=very positive)

## Location Guidelines
- If a specific place is mentioned, use it (e.g., "Blue Bottle Coffee", "Central Park")
- If only a type of place is clear, use that (e.g., "coffee shop", "park", "office")
- If location is unclear, use "unspecified" or your best inference based on context

## People Guidelines
- Include actual names if mentioned
- Use roles/relationships if names aren't given (e.g., "colleague", "friend")
- Empty list if alone or no one else is mentioned

Remember: This is the FINAL version. Make it polished, complete, and ready for the user's diary.