# Process New Ongoing Event

You are analyzing a transcript from the user's day to create a diary entry. This is a NEW event that is still ongoing (may continue with more content later).

## Language Detection

Before analyzing the transcript, examine the language(s) used. If more than 90% of the transcript is in a single language (e.g., Chinese, Spanish, Japanese, etc.), generate ALL output in that language.

## Your Task

Analyze the transcript below and create a diary entry with a title, summary, and story. Focus on understanding what's happening, who's involved, and the user's experience.

## Transcript

{transcript}

## Output Requirements

Provide your response with:
- **event_title**: Brief descriptive title (5-10 words)
- **event_summary**: 1-2 sentence summary of what's happening
- **event_story**: Full narrative diary entry from the user's perspective (20-500 words, based on transcription length)

## Important Guidelines

1. **Write from first person perspective** - This is the user's diary
2. **Focus on what's actually happening** - Don't speculate beyond the transcript
3. **Capture the essence** - Include key activities, interactions, and feelings
4. **Natural language** - Write as if the user is telling their own story
5. **No timestamps** - Don't mention times, just focus on the narrative flow
6. **Identify interactants carefully** - When mentioning people:
   - Never list the user as interacting with themselves
   - Use explicit names only when clearly stated in the transcript
   - Use generic descriptors (Friend, Colleague, etc.) when names are unclear
   - Only include people actively participating, not those merely mentioned

Remember: This event is ONGOING, so the story might be incomplete. That's okay - just capture what has happened so far.