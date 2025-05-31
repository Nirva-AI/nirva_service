# Reflection

## Step 3: Generate daily reflection based on the what happened and how the user felt through out the day. (JSON Output)

```json
{
  "daily_reflection": {
    "reflection_summary": "string", // How the day unfolded overall, <50 words
    "gratitude": {
      "gratitude_summary": ["string", "string", "string"], // 3 bullet points, each <50 words
      "gratitude_details": "string", // What genuinely grateful for, qualities admired in others
      "win_summary": ["string", "string", "string"], // 3 celebration points, each <50 words
      "win_details": "string", // Successes and wins, big and small
      "feel_alive_moments": "string" // Magical or meaningful moments, unexpected joys, connections, insights
    },
    "challenges_and_growth": {
      "growth_summary": ["string", "string", "string"], // 3 improvement areas, each <50 words
      "obstacles_faced": "string", // External challenges and internal struggles
      "unfinished_intentions": "string", // What intended to accomplish but didn't
      "contributing_factors": "string" // Patterns: time management, energy, priorities, circumstances
    },
    "learning_and_insights": {
      "new_knowledge": "string", // Technical learning, creative techniques, practical skills, fresh perspectives
      "self_discovery": "string", // New strengths, patterns, emotional responses, preferences
      "insights_about_others": "string", // About colleagues, friends, family, strangers
      "broader_lessons": "string" // About work, relationships, life, world
    },
    "connections_and_relationships": {
      "meaningful_interactions": "string", // Quality and impact of interactions beyond just names
      "notable_about_people": "string", // New perspectives, admired qualities, surprises
      "follow_up_needed": "string" // Who deserves attention: to thank, update, ask questions, give feedback
    },
    "looking_forward": {
      "do_differently_tomorrow": "string", // Based on today's experiences and lessons
      "continue_what_worked": "string", // Successful strategies, positive habits, effective approaches
      "top_3_priorities_tomorrow": ["string", "string", "string"] // Specific, achievable priorities connected to larger goals
    }
  }
}
```
