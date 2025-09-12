# Enhanced Chat v2 Database Schema

## Overview

This document describes the database schema for the Enhanced Chat v2 system in Nirva Service. The enhanced chat system uses a PostgreSQL database with JSON columns to support conversation persistence, context awareness, and advanced chat features.

## Database Tables

### 1. user_conversations

**Purpose**: Stores metadata for each user's single persistent conversation

```sql
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
```

**Key Features**:
- One conversation per user (WhatsApp-style model)
- Automatic timestamps for creation and updates
- Message counting for analytics
- Personality settings stored as JSON for flexibility
- Optional conversation summary for context

**Indexes**:
```sql
CREATE INDEX idx_user_conversations_user_id ON user_conversations(user_id);
CREATE INDEX idx_user_conversations_last_activity ON user_conversations(last_activity);
```

### 2. conversation_messages

**Purpose**: Stores individual messages within conversations

```sql
CREATE TABLE conversation_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    role INTEGER NOT NULL, -- 0=system, 1=human, 2=ai
    content TEXT NOT NULL,
    message_type INTEGER DEFAULT 0, -- 0=text
    message_metadata JSON,
    context_snapshot JSON, -- Mental state + events at message time
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    
    FOREIGN KEY (user_id) REFERENCES user_conversations(user_id) ON DELETE CASCADE
);
```

**Key Features**:
- Auto-generated UUID primary key
- Role-based message system (system/human/ai)
- Context snapshot preserved with each message
- Response time tracking for performance analysis
- Extensible metadata storage

**Indexes**:
```sql
CREATE INDEX idx_conversation_messages_user_id ON conversation_messages(user_id);
CREATE INDEX idx_conversation_messages_timestamp ON conversation_messages(timestamp);
CREATE INDEX idx_conversation_messages_role ON conversation_messages(role);
CREATE INDEX idx_conversation_messages_content_gin ON conversation_messages USING gin(to_tsvector('english', content));
```

**Role Constants**:
- `0` = System message
- `1` = Human message
- `2` = AI message

### 3. conversation_context

**Purpose**: Stores learned conversation memory and context

```sql
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
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES user_conversations(user_id) ON DELETE CASCADE
);
```

**Key Features**:
- AI-learned facts about user preferences
- Personality insights from conversation analysis
- Communication style adaptation
- Thematic analysis of conversation topics
- Background memory updates for performance

**Indexes**:
```sql
CREATE INDEX idx_conversation_context_user_id ON conversation_context(user_id);
CREATE INDEX idx_conversation_context_last_updated ON conversation_context(last_updated);
```

### 4. chat_messages (Legacy)

**Purpose**: Legacy chat messages table for backward compatibility

```sql
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

**Status**: Deprecated - maintained for backward compatibility only

## Context Snapshot Schema

### Structure

Each message includes a context snapshot capturing the user's state at the time of the message:

```json
{
  "username": "string",
  "display_name": "string", 
  "timestamp": "2025-09-12T05:06:12.627973+00:00",
  "mental_state_available": boolean,
  "current_energy": number, // 0-100 scale
  "current_stress": number, // 0-100 scale
  "mental_state_confidence": number, // 0.0-1.0
  "mental_state_source": "string", // "events_impact" | "baseline" | etc.
  "recent_events_available": boolean,
  "recent_events_count": number,
  "recent_events": [
    {
      "event_type": "string",
      "description": "string",
      "energy_level": number, // 0-100
      "stress_level": number, // 0-100
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

### Mental State Integration

The context snapshot integrates with the mental state system:
- **Energy/Stress Scores**: Real-time 0-100 scale values
- **Confidence Metrics**: AI confidence in mental state calculation
- **Data Sources**: Tracking how mental state was derived
- **Recent Events**: Events that influenced current mental state

### Event Context

Recent events are included to provide AI with situational awareness:
- **Event Types**: work, exercise, social, meal, break, sleep, other
- **Impact Scores**: How each event affected energy/stress levels
- **Temporal Context**: When events occurred relative to conversation

## Conversation Memory Schema

### Facts Storage

```json
{
  "preferences": {
    "communication_style": "direct",
    "topics_of_interest": ["technology", "productivity"],
    "preferred_response_length": "medium"
  },
  "personal_info": {
    "timezone": "America/New_York",
    "work_schedule": "9-5",
    "key_relationships": ["colleague:Sarah", "manager:John"]
  },
  "context_patterns": {
    "morning_energy_high": true,
    "stress_triggers": ["deadlines", "meetings"],
    "preferred_activities": ["coding", "reading"]
  }
}
```

### Personality Insights

```json
{
  "traits": {
    "introversion_score": 0.7,
    "detail_orientation": 0.8,
    "planning_preference": 0.9
  },
  "communication_patterns": {
    "question_style": "specific",
    "response_preference": "actionable",
    "feedback_style": "direct"
  },
  "learned_behaviors": {
    "responds_well_to": ["structured_advice", "step_by_step"],
    "avoids": ["small_talk", "generic_responses"]
  }
}
```

## Database Operations

### Message Storage Flow

1. **Insert Human Message**:
   ```sql
   INSERT INTO conversation_messages (user_id, role, content, context_snapshot, timestamp)
   VALUES ($1, 1, $2, $3, NOW());
   ```

2. **Update Conversation Metadata**:
   ```sql
   UPDATE user_conversations 
   SET last_activity = NOW(), 
       total_messages = total_messages + 1,
       updated_at = NOW()
   WHERE user_id = $1;
   ```

3. **Insert AI Response**:
   ```sql
   INSERT INTO conversation_messages (user_id, role, content, response_time_ms, timestamp)
   VALUES ($1, 2, $2, $3, NOW());
   ```

### History Retrieval

```sql
SELECT id, role, content, timestamp, message_metadata
FROM conversation_messages
WHERE user_id = $1
ORDER BY timestamp DESC
LIMIT $2 OFFSET $3;
```

### Full-Text Search

```sql
SELECT id, role, content, timestamp, ts_rank(
    to_tsvector('english', content), 
    plainto_tsquery('english', $2)
) AS rank
FROM conversation_messages
WHERE user_id = $1 
AND to_tsvector('english', content) @@ plainto_tsquery('english', $2)
ORDER BY rank DESC, timestamp DESC
LIMIT $3;
```

### Conversation Statistics

```sql
SELECT 
    total_messages,
    created_at,
    last_activity,
    (SELECT COUNT(*) FROM conversation_messages WHERE user_id = $1 AND role = 1) as human_messages,
    (SELECT COUNT(*) FROM conversation_messages WHERE user_id = $1 AND role = 2) as ai_messages
FROM user_conversations 
WHERE user_id = $1;
```

## Performance Considerations

### Indexing Strategy

1. **Primary Keys**: UUIDs with btree indexes
2. **Foreign Keys**: user_id columns indexed
3. **Temporal Queries**: timestamp columns indexed
4. **Full-Text Search**: GIN indexes on content
5. **Role Filtering**: role column indexed

### Query Optimization

1. **Pagination**: Always use LIMIT/OFFSET for large result sets
2. **Context Loading**: Load context snapshots lazily when needed
3. **Memory Updates**: Process conversation memory asynchronously
4. **Connection Pooling**: Use connection pooling for concurrent requests

### Storage Efficiency

1. **JSON Compression**: PostgreSQL automatically compresses JSON data
2. **Context Pruning**: Periodically clean old context snapshots
3. **Message Archiving**: Archive old messages to separate tables
4. **Index Maintenance**: Regular VACUUM and ANALYZE operations

## Migration Scripts

### Creating Tables

```sql
-- Create user_conversations table
CREATE TABLE IF NOT EXISTS user_conversations (
    user_id UUID PRIMARY KEY,
    title VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE,
    total_messages INTEGER DEFAULT 0,
    personality_settings JSON,
    conversation_summary TEXT
);

-- Create conversation_messages table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    role INTEGER NOT NULL,
    content TEXT NOT NULL,
    message_type INTEGER DEFAULT 0,
    message_metadata JSON,
    context_snapshot JSON,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER,
    FOREIGN KEY (user_id) REFERENCES user_conversations(user_id) ON DELETE CASCADE
);

-- Create conversation_context table
CREATE TABLE IF NOT EXISTS conversation_context (
    user_id UUID PRIMARY KEY,
    facts JSON,
    personality_insights JSON,
    communication_style JSON,
    context_themes JSON,
    mental_state_summary TEXT,
    recent_events_summary TEXT,
    conversation_memory JSON,
    personality_state JSON,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_conversations(user_id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_id ON conversation_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_timestamp ON conversation_messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_role ON conversation_messages(role);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_content_gin ON conversation_messages USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_user_conversations_last_activity ON user_conversations(last_activity);
CREATE INDEX IF NOT EXISTS idx_conversation_context_user_id ON conversation_context(user_id);
```

### Data Migration from Legacy

```sql
-- Migrate from chat_messages to conversation_messages
INSERT INTO conversation_messages (user_id, role, content, message_metadata, context_snapshot, timestamp, response_time_ms)
SELECT 
    user_id,
    CASE 
        WHEN role = 'system' THEN 0
        WHEN role = 'human' THEN 1 
        WHEN role = 'ai' THEN 2
        ELSE 1
    END as role,
    content,
    message_metadata,
    context_snapshot,
    timestamp,
    response_time_ms
FROM chat_messages
WHERE NOT EXISTS (
    SELECT 1 FROM conversation_messages cm 
    WHERE cm.user_id = chat_messages.user_id 
    AND cm.timestamp = chat_messages.timestamp
);

-- Initialize user_conversations from messages
INSERT INTO user_conversations (user_id, created_at, last_activity, total_messages)
SELECT 
    user_id,
    MIN(timestamp) as created_at,
    MAX(timestamp) as last_activity,
    COUNT(*) as total_messages
FROM conversation_messages
GROUP BY user_id
ON CONFLICT (user_id) DO UPDATE SET
    last_activity = EXCLUDED.last_activity,
    total_messages = EXCLUDED.total_messages;
```

## Security Considerations

### Data Access

1. **User Isolation**: All queries filtered by user_id
2. **JWT Authentication**: Token validation for all operations
3. **SQL Injection**: Parameterized queries only
4. **Context Sanitization**: Sanitize context data before storage

### Privacy

1. **Data Retention**: Configurable message retention policies
2. **Anonymization**: Option to anonymize old conversations
3. **Export/Delete**: User data export and deletion capabilities
4. **Encryption**: Consider encrypting sensitive context data

## Monitoring and Maintenance

### Performance Metrics

1. **Query Response Times**: Monitor slow queries
2. **Index Usage**: Track index hit rates
3. **Storage Growth**: Monitor table sizes
4. **Connection Usage**: Track database connection pool

### Maintenance Tasks

1. **Daily**: Update table statistics with ANALYZE
2. **Weekly**: VACUUM tables to reclaim space
3. **Monthly**: Reindex for optimal performance
4. **Quarterly**: Review and archive old data

### Backup Strategy

1. **Continuous**: PostgreSQL WAL archiving
2. **Daily**: Full database backups
3. **Testing**: Regular backup restoration tests
4. **Retention**: Configurable backup retention periods

## Troubleshooting

### Common Issues

1. **Slow Queries**: Check query plans and index usage
2. **Storage Growth**: Monitor JSON column sizes
3. **Connection Limits**: Check connection pool configuration
4. **Foreign Key Violations**: Ensure user_conversations exists before messages

### Diagnostic Queries

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename IN ('user_conversations', 'conversation_messages', 'conversation_context');

-- Monitor query performance
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements 
WHERE query ILIKE '%conversation%'
ORDER BY total_time DESC;

-- Check index usage
SELECT 
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE relname IN ('user_conversations', 'conversation_messages', 'conversation_context');
```