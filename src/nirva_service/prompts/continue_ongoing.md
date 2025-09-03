# Continue Ongoing Event

You are updating an ongoing diary entry with new content. The user's event continues with additional transcript.

## Previous Event Details

**Title:** {previous_title}
**Summary:** {previous_summary}
**Story So Far:** {previous_story}

## New Transcript

{new_transcript}

## Your Task

Update the diary entry by incorporating the new content. The event continues to unfold, so:
1. Update the title if the new content changes the focus
2. Revise the summary to include new developments
3. Expand the story to include the new content naturally

## Output Requirements

Provide a JSON response with the following structure:

```json
{
  "event_title": "Updated title reflecting the full event (5-10 words)",
  "event_summary": "Updated 1-2 sentence summary including new developments",
  "event_story": "Expanded narrative combining previous and new content (50-500 words)"
}
```

## Important Guidelines

1. **Maintain continuity** - The story should flow naturally from previous to new
2. **Don't repeat verbatim** - Integrate the new content, don't just append
3. **Keep first person** - Maintain the diary perspective
4. **Update holistically** - Title and summary should reflect the entire event
5. **No timestamps** - Focus on narrative flow, not time markers

Remember: This event is STILL ONGOING. Write as if telling the story up to this point.