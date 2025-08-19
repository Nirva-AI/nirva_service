# Nirva Service API Endpoints Reference

This document provides a comprehensive reference for all available API endpoints in the Nirva Service. Use this guide to integrate with the service from client applications.

## Base URLs

- **AppService Server**: `http://localhost:8000`
- **Analyzer Server**: `http://localhost:8100`
- **Chat Server**: `http://localhost:8200`

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

## 1. Authentication Endpoints

### 1.1 Login
**Endpoint**: `POST /login/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 1.2 Refresh Token
**Endpoint**: `POST /refresh/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "refresh_token": "string"
}
```

**Response**: Same as login response

### 1.3 Logout
**Endpoint**: `POST /logout/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "refresh_token": "string"
}
```

**Response**: HTTP 200 (no content)

## 2. Analysis Endpoints

### 2.1 Create Analysis Task
**Endpoint**: `POST /action/analyze/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "time_stamp": "2025-01-20",
  "file_number": 1
}
```

**Response**:
```json
{
  "task_id": "uuid_string",
  "message": "分析任务已创建，请使用任务ID查询状态和结果"
}
```

**Notes**: This creates a background task. Use the returned `task_id` to check status.

### 2.2 Check Task Status
**Endpoint**: `GET /action/task/status/v1/{task_id}/`  
**Server**: AppService (Port 8000)

**Path Parameters**:
- `task_id`: The task ID returned from create analysis task

**Response**:
```json
{
  "task_id": "uuid_string",
  "status": "completed|processing|failed",
  "result": {
    "journal_file": {
      "username": "string",
      "time_stamp": "string",
      "events": [...],
      "daily_reflection": {...}
    }
  },
  "error": "string (if failed)"
}
```

### 2.3 Incremental Analysis
**Endpoint**: `POST /action/analyze/incremental/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "time_stamp": "2025-01-20",
  "new_transcript": "New transcript content to analyze"
}
```

**Response**:
```json
{
  "updated_events_count": 2,
  "new_events_count": 1,
  "total_events_count": 5,
  "message": "增量分析完成，更新了2个事件，新增了1个事件"
}
```

**Notes**: This endpoint performs real-time incremental analysis on new transcript content.

### 2.4 Get Events
**Endpoint**: `POST /action/analyze/events/get/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "time_stamp": "2025-01-20"
}
```

**Response**:
```json
{
  "time_stamp": "2025-01-20",
  "events": [
    {
      "event_id": "uuid_string",
      "title": "Event title",
      "description": "Event description",
      "tags": ["tag1", "tag2"],
      "time_range": "09:00-10:00",
      "importance": 8
    }
  ],
  "total_count": 5,
  "last_updated": "2025-01-20T15:30:00"
}
```

### 2.5 Get Journal File
**Endpoint**: `GET /action/get_journal_file/v1/{time_stamp}/`  
**Server**: AppService (Port 8000)

**Path Parameters**:
- `time_stamp`: Date in format "2025-01-20"

**Response**:
```json
{
  "username": "string",
  "time_stamp": "2025-01-20",
  "events": [...],
  "daily_reflection": {
    "summary": "Daily summary",
    "insights": ["insight1", "insight2"],
    "action_items": ["action1", "action2"]
  }
}
```

## 3. Transcript Management

### 3.1 Upload Transcript
**Endpoint**: `POST /action/upload_transcript/v1/`  
**Server**: AppService (Port 8000)

**Request Body**:
```json
{
  "transcripts": [
    {
      "time_stamp": "2025-01-20",
      "content": "Transcript content here"
    }
  ]
}
```

**Response**:
```json
{
  "results": [
    {
      "time_stamp": "2025-01-20",
      "status": "success",
      "message": "Transcript stored successfully"
    }
  ],
  "message": "批量转录内容处理完成: 用户=username, 处理数量=1"
}
```

## 4. Chat Endpoints

### 4.1 Chat Action
**Endpoint**: `POST /action/chat/v1/`  
**Server**: Chat Server (Port 8200)

**Request Body**:
```json
{
  "human_message": {
    "id": "uuid_string",
    "role": 1,
    "content": "User message content",
    "time_stamp": "2025-01-20T10:00:00",
    "tags": ["tag1", "tag2"]
  },
  "chat_history": [
    {
      "id": "uuid_string",
      "role": 0,
      "content": "System message",
      "time_stamp": "2025-01-20T09:00:00"
    }
  ]
}
```

**Response**:
```json
{
  "ai_message": {
    "id": "uuid_string",
    "role": 2,
    "content": "AI response content",
    "time_stamp": "2025-01-20T10:01:00",
    "tags": ["response"]
  }
}
```

## 5. Configuration Endpoints

### 5.1 Get URL Configuration
**Endpoint**: `GET /config`  
**Server**: AppService (Port 8000)

**Response**:
```json
{
  "api_version": "v1.0.0",
  "endpoints": {
    "analyze": "/action/analyze/v1/",
    "chat": "/action/chat/v1/",
    "login": "/login/v1/"
  },
  "deprecated": false,
  "notice": ""
}
```

## 6. Data Models

### 6.1 Event Analysis
```json
{
  "event_id": "uuid_string",
  "title": "string",
  "description": "string",
  "tags": ["string"],
  "time_range": "string",
  "importance": 1-10,
  "category": "string"
}
```

### 6.2 Daily Reflection
```json
{
  "summary": "string",
  "insights": ["string"],
  "action_items": ["string"],
  "mood": "string",
  "energy_level": 1-10
}
```

### 6.3 Message Role Values
- `0`: System message
- `1`: Human message  
- `2`: AI message

## 7. Error Handling

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (missing/invalid token)
- `404`: Not Found
- `500`: Internal Server Error

Error responses include a `detail` field with error information:

```json
{
  "detail": "Error description here"
}
```

## 8. Usage Examples

### 8.1 Complete Analysis Workflow

```python
import requests

# 1. Login to get token
login_response = requests.post("http://localhost:8000/login/v1/", json={
    "username": "your_username",
    "password": "your_password"
})
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Upload transcript
transcript_response = requests.post(
    "http://localhost:8000/action/upload_transcript/v1/",
    json={
        "transcripts": [{
            "time_stamp": "2025-01-20",
            "content": "Today I had a productive meeting..."
        }]
    },
    headers=headers
)

# 3. Create analysis task
analyze_response = requests.post(
    "http://localhost:8000/action/analyze/v1/",
    json={
        "time_stamp": "2025-01-20",
        "file_number": 1
    },
    headers=headers
)
task_id = analyze_response.json()["task_id"]

# 4. Check task status
status_response = requests.get(
    f"http://localhost:8000/action/task/status/v1/{task_id}/",
    headers=headers
)

# 5. Get events when analysis is complete
events_response = requests.post(
    "http://localhost:8000/action/analyze/events/get/v1/",
    json={"time_stamp": "2025-01-20"},
    headers=headers
)
```

### 8.2 Incremental Analysis

```python
# Perform incremental analysis on new content
incremental_response = requests.post(
    "http://localhost:8000/action/analyze/incremental/v1/",
    json={
        "time_stamp": "2025-01-20",
        "new_transcript": "Additional content to analyze..."
    },
    headers=headers
)
```

## 9. Rate Limits and Best Practices

- **Authentication**: Always include the JWT token in requests
- **Error Handling**: Implement proper error handling for all API calls
- **Background Tasks**: Use task IDs to monitor long-running operations
- **Batch Operations**: Use batch endpoints when processing multiple items
- **Incremental Updates**: Use incremental analysis for real-time updates

## 10. Testing

You can test all endpoints using the interactive API documentation:

- AppService: http://localhost:8000/docs
- Analyzer: http://localhost:8100/docs  
- Chat: http://localhost:8200/docs

These provide Swagger UI interfaces for testing endpoints directly in the browser.

## 11. Support

For questions or issues with the API:

1. Check the server logs for detailed error information
2. Verify your authentication token is valid
3. Ensure request payloads match the expected schema
4. Check that required services (Redis, PostgreSQL) are running
