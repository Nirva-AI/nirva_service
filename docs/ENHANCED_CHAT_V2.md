# Enhanced Chat v2 System

## Overview

Enhanced Chat v2 is a complete redesign of the Nirva chat system that introduces persistent conversation storage, context awareness, and WhatsApp-style single conversation per user model. This replaces the previous stateless chat v1 system.

## Key Features

### 🔄 **Server-Side Conversation Management**
- **Single persistent conversation per user** - WhatsApp-style experience
- **Automatic message storage** - All messages stored in database automatically
- **Server manages conversation history** - Client sends empty `chat_history` array
- **Cross-session continuity** - Conversations persist across app sessions

### 🧠 **Context Awareness**
- **Mental state integration** - AI receives current energy/stress scores
- **Recent events awareness** - AI knows about recent user activities
- **Conversation memory** - Long-term personality and preference learning
- **Enhanced system prompts** - Rich context provided to AI

### 📊 **Advanced Chat Features**
- **Conversation history retrieval** - Paginated access to chat history
- **Full-text search** - Search across all conversation messages
- **Conversation statistics** - Analytics on chat usage patterns
- **Real-time context updates** - Fresh mental state data per message

## Architecture

### Database Schema

```sql
-- Main conversation metadata
CREATE TABLE user_conversations (
    user_id UUID PRIMARY KEY,
    title VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE,
    total_messages INTEGER DEFAULT 0,
    personality_settings JSON,
    conversation_summary TEXT
);

-- Individual conversation messages
CREATE TABLE conversation_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    role INTEGER NOT NULL, -- 0=system, 1=human, 2=ai
    content TEXT NOT NULL,
    message_type INTEGER DEFAULT 0, -- 0=text
    message_metadata JSON,
    context_snapshot JSON, -- Mental state + events at message time
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER
);

-- Conversation context and memory
CREATE TABLE conversation_context (
    user_id UUID PRIMARY KEY,
    facts JSON,
    personality_insights JSON,
    communication_style JSON,
    context_themes JSON,
    mental_state_summary TEXT,
    recent_events_summary TEXT,
    conversation_memory JSON,
    personality_state JSON,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Legacy chat messages (still used)
CREATE TABLE chat_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR DEFAULT 'TEXT',
    attachments JSON DEFAULT '[]',
    message_metadata JSON,
    context_snapshot JSON,
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Service Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│   Enhanced Chat     │    │   Conversation      │
│   Actions Service   │◄───┤   Manager Service   │
│                     │    │                     │
└─────────────────────┘    └─────────────────────┘
           │                           │
           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│   Context Builder   │    │   Database Layer    │
│   - Mental State    │    │   - PostgreSQL      │
│   - Recent Events   │    │   - JSON Storage    │
│   - Conversation    │    │   - Full-text       │
│     Memory          │    │     Search          │
└─────────────────────┘    └─────────────────────┘
```

## API Endpoints

### Enhanced Chat v2

**POST** `/action/chat/v2/`

**Request Format:**
```json
{
  "human_message": {
    "id": "client-message-id",
    "role": 1,
    "content": "User message text", 
    "time_stamp": "2025-09-11T21:00:00"
  },
  "chat_history": []  // Always empty - server manages this
}
```

**Response Format:**
```json
{
  "ai_message": {
    "id": "server-generated-uuid",
    "role": 2,
    "content": "AI response with context awareness",
    "time_stamp": "2025-09-12T05:06:12.627973+00:00",
    "tags": null
  }
}
```

### Conversation History

**GET** `/conversation/history/?limit=50&offset=0`

**Response:**
```json
{
  "messages": [
    {
      "id": "message-uuid",
      "role": 1,
      "content": "Message content",
      "time_stamp": "2025-09-12T05:02:00.638605+00:00",
      "tags": null
    }
  ],
  "total_count": 25,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

### Conversation Search

**POST** `/conversation/search/`

**Request (Form Data):**
```
query=search_term&limit=10
```

**Response:**
```json
{
  "messages": [...],
  "query": "search_term",
  "result_count": 5
}
```

### Conversation Statistics

**GET** `/conversation/stats/`

**Response:**
```json
{
  "total_messages": 25,
  "first_message": "2025-09-12T05:02:00.638605+00:00",
  "last_activity": "2025-09-12T05:06:12.627973+00:00",
  "message_types": {"text": 25},
  "created_at": "2025-09-12T05:02:00.638605+00:00"
}
```

## Context Snapshot Structure

Each message includes a context snapshot capturing the user's state:

```json
{
  "username": "user123",
  "display_name": "John Doe",
  "timestamp": "2025-09-12T05:06:12.627973+00:00",
  "mental_state_available": true,
  "current_energy": 65.0,
  "current_stress": 35.0,
  "mental_state_confidence": 0.85,
  "mental_state_source": "events_impact",
  "recent_events_available": true,
  "recent_events_count": 3,
  "recent_events": [
    {
      "event_type": "work_meeting",
      "description": "Had productive team standup",
      "energy_level": 70,
      "stress_level": 30,
      "timestamp": "2025-09-12T04:30:00+00:00"
    }
  ],
  "conversation_memory": {
    "facts": {},
    "personality_insights": {},
    "context_available": {}
  }
}
```

## Implementation Details

### Message Processing Flow

1. **Receive Message** - Client sends human message to `/action/chat/v2/`
2. **Store Human Message** - Message stored with context snapshot
3. **Build Context** - Mental state + recent events + conversation memory
4. **AI Processing** - Context-aware system prompt + conversation history
5. **Store AI Response** - AI message stored with metadata
6. **Update Memory** - Background conversation memory update
7. **Return Response** - AI message returned to client

### Context Building

```python
def _build_context_snapshot(username: str, display_name: str, user_id: UUID) -> Dict[str, Any]:
    """Build comprehensive context snapshot for AI processing."""
    context = {
        "username": username,
        "display_name": display_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mental_state_available": False,
        "recent_events_available": False,
    }
    
    # Add mental state (energy/stress scores)
    try:
        calculator = MentalStateCalculator()
        timeline = calculator.calculate_timeline(username, ...)
        if timeline:
            latest_state = timeline[-1]
            context.update({
                "mental_state_available": True,
                "current_energy": latest_state.energy_score,
                "current_stress": latest_state.stress_score,
                ...
            })
    except Exception as e:
        logger.warning(f"Failed to get mental state: {e}")
    
    # Add recent events
    try:
        recent_events = get_events_in_range(username, ...)
        if recent_events:
            context.update({
                "recent_events_available": True,
                "recent_events": [format_event(e) for e in recent_events[:5]]
            })
    except Exception as e:
        logger.warning(f"Failed to get recent events: {e}")
    
    return context
```

### Conversation Memory

The system learns and remembers:
- **User preferences** and communication style
- **Recurring topics** and interests  
- **Personality traits** observed over time
- **Context patterns** for better responses

Memory is updated asynchronously after each conversation to avoid blocking responses.

## Migration from Chat v1

### Key Differences

| Feature | Chat v1 | Enhanced Chat v2 |
|---------|---------|------------------|
| Conversation Storage | Stateless | Persistent |
| Client Responsibility | Manage history | Send messages only |
| Context Awareness | Basic prompts | Rich context snapshots |
| Conversation Model | Session-based | Single persistent chat |
| Memory | None | Long-term learning |
| Search | Not available | Full-text search |

### URL Configuration Changes

```python
# Updated endpoints
"chat": base + "action/chat/v2/",  # Changed from v1
"conversation_history": base + "conversation/history/",  # New
"conversation_stats": base + "conversation/stats/",      # New  
"conversation_search": base + "conversation/search/",    # New
```

## Deployment Notes

### Database Setup

When deploying to new environments, ensure all tables are created:

```bash
# Create conversation tables
psql -U fastapi_user -d my_fastapi_db -f scripts/create_conversation_tables.sql
```

### Required Tables
- `user_conversations` - Conversation metadata
- `conversation_messages` - Individual messages
- `conversation_context` - Memory and context
- `chat_messages` - Legacy compatibility

### Configuration

The system requires:
- **OpenAI API Key** - For AI responses
- **PostgreSQL Database** - With JSON support
- **Mental State Service** - For context awareness
- **Events System** - For recent activity data

## Performance Considerations

- **Context Snapshot Size** - Large JSON objects stored per message
- **Memory Updates** - Background processing to avoid blocking
- **Search Performance** - Full-text search on message content
- **History Pagination** - Limit queries to prevent large responses

## Future Enhancements

- **Voice message support** - Audio message handling
- **Message reactions** - Like/dislike functionality  
- **Conversation themes** - Automatic categorization
- **Advanced search** - Semantic search with embeddings
- **Multi-conversation** - Support for multiple conversation threads