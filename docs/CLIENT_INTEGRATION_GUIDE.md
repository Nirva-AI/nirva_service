# Client Integration Guide - Quick Start

This guide helps you quickly integrate your client application with the Nirva Service API.

## 🚀 Quick Start (5 minutes)

### 1. Prerequisites
- Python 3.8+ or any HTTP client
- Access to the Nirva Service servers
- Valid user credentials

### 2. Basic Setup

```python
import requests

# Base URLs
BASE_URL = "http://localhost:8000"  # AppService
CHAT_URL = "http://localhost:8200"  # Chat Server

# Headers for authenticated requests
def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
```

### 3. Authentication Flow

```python
def authenticate(username, password):
    """Get JWT token for API access"""
    response = requests.post(f"{BASE_URL}/login/v1/", json={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        raise Exception(f"Authentication failed: {response.text}")

# Usage
token = authenticate("your_username", "your_password")
headers = get_auth_headers(token)
```

## 📝 Common Use Cases

### Case 1: Analyze a Transcript

```python
def analyze_transcript(token, date, transcript_content):
    """Complete workflow: upload transcript and analyze"""
    
    # 1. Upload transcript
    upload_response = requests.post(
        f"{BASE_URL}/action/upload_transcript/v1/",
        json={
            "transcripts": [{
                "time_stamp": date,
                "content": transcript_content
            }]
        },
        headers=get_auth_headers(token)
    )
    
    if upload_response.status_code != 200:
        raise Exception(f"Upload failed: {upload_response.text}")
    
    # 2. Start analysis
    analyze_response = requests.post(
        f"{BASE_URL}/action/analyze/v1/",
        json={
            "time_stamp": date,
            "file_number": 1
        },
        headers=get_auth_headers(token)
    )
    
    if analyze_response.status_code != 200:
        raise Exception(f"Analysis failed: {analyze_response.text}")
    
    task_id = analyze_response.json()["task_id"]
    return task_id

def wait_for_analysis(token, task_id, max_wait=300):
    """Wait for analysis to complete and return results"""
    import time
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        status_response = requests.get(
            f"{BASE_URL}/action/task/status/v1/{task_id}/",
            headers=get_auth_headers(token)
        )
        
        if status_response.status_code != 200:
            raise Exception(f"Status check failed: {status_response.text}")
        
        status_data = status_response.json()
        
        if status_data["status"] == "completed":
            return status_data["result"]["journal_file"]
        elif status_data["status"] == "failed":
            raise Exception(f"Analysis failed: {status_data.get('error', 'Unknown error')}")
        
        time.sleep(2)  # Wait 2 seconds before checking again
    
    raise Exception("Analysis timeout")

# Usage
task_id = analyze_transcript(token, "2025-01-20", "Today I had a productive meeting...")
journal_file = wait_for_analysis(token, task_id)
print(f"Analysis complete! Found {len(journal_file['events'])} events")
```

### Case 2: Real-time Incremental Analysis

```python
def incremental_analyze(token, date, new_content):
    """Analyze new content in real-time"""
    
    response = requests.post(
        f"{BASE_URL}/action/analyze/incremental/v1/",
        json={
            "time_stamp": date,
            "new_transcript": new_content
        },
        headers=get_auth_headers(token)
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Updated {result['updated_events_count']} events")
        print(f"Added {result['new_events_count']} new events")
        return result
    else:
        raise Exception(f"Incremental analysis failed: {response.text}")

# Usage
result = incremental_analyze(token, "2025-01-20", "Just finished a client call...")
```

### Case 3: Get Events for a Date

```python
def get_events(token, date):
    """Get all events for a specific date"""
    
    response = requests.post(
        f"{BASE_URL}/action/analyze/events/get/v1/",
        json={"time_stamp": date},
        headers=get_auth_headers(token)
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total_count']} events for {date}")
        return data["events"]
    else:
        raise Exception(f"Failed to get events: {response.text}")

# Usage
events = get_events(token, "2025-01-20")
for event in events:
    print(f"- {event['title']}: {event['description']}")
```

### Case 4: Chat with AI

```python
def chat_with_ai(token, message, chat_history=None):
    """Send a message to the AI chat service"""
    
    if chat_history is None:
        chat_history = []
    
    import uuid
    from datetime import datetime
    
    chat_request = {
        "human_message": {
            "id": str(uuid.uuid4()),
            "role": 1,  # Human message
            "content": message,
            "time_stamp": datetime.now().isoformat(),
            "tags": ["user_input"]
        },
        "chat_history": chat_history
    }
    
    response = requests.post(
        f"{CHAT_URL}/action/chat/v1/",
        json=chat_request,
        headers=get_auth_headers(token)
    )
    
    if response.status_code == 200:
        ai_message = response.json()["ai_message"]
        return ai_message["content"]
    else:
        raise Exception(f"Chat failed: {response.text}")

# Usage
response = chat_with_ai(token, "What should I focus on today?")
print(f"AI: {response}")
```

## 🔧 Error Handling

```python
def safe_api_call(func, *args, **kwargs):
    """Wrapper for safe API calls with error handling"""
    try:
        return func(*args, **kwargs)
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"API error: {e}")
        return None

# Usage
result = safe_api_call(get_events, token, "2025-01-20")
if result is None:
    print("Failed to get events, please try again later")
```

## 📊 Data Models

### Event Structure
```python
event_example = {
    "event_id": "uuid-string",
    "title": "Team Meeting",
    "description": "Weekly standup with development team",
    "tags": ["meeting", "team", "standup"],
    "time_range": "09:00-09:30",
    "importance": 8,
    "category": "work"
}
```

### Journal File Structure
```python
journal_example = {
    "username": "user123",
    "time_stamp": "2025-01-20",
    "events": [event_example],
    "daily_reflection": {
        "summary": "Productive day with good team collaboration",
        "insights": ["Clear communication is key", "Need to follow up on action items"],
        "action_items": ["Schedule follow-up meeting", "Update project timeline"]
    }
}
```

## 🧪 Testing Your Integration

### 1. Test Authentication
```python
# Test if your credentials work
try:
    token = authenticate("test_user", "test_password")
    print("✅ Authentication successful")
except Exception as e:
    print(f"❌ Authentication failed: {e}")
```

### 2. Test Basic Endpoints
```python
# Test if servers are responding
def test_connectivity():
    try:
        # Test AppService
        response = requests.get(f"{BASE_URL}/config")
        print(f"✅ AppService: {response.status_code}")
        
        # Test Chat Server
        response = requests.get(f"{CHAT_URL}/docs")
        print(f"✅ Chat Server: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")

test_connectivity()
```

### 3. Test Full Workflow
```python
def test_full_workflow():
    """Test the complete analysis workflow"""
    try:
        # 1. Authenticate
        token = authenticate("test_user", "test_password")
        
        # 2. Upload test transcript
        test_content = "Today I had a productive meeting with the team. We discussed the new project requirements and set clear goals."
        task_id = analyze_transcript(token, "2025-01-20", test_content)
        
        # 3. Wait for analysis
        journal_file = wait_for_analysis(token, task_id)
        
        # 4. Get events
        events = get_events(token, "2025-01-20")
        
        print(f"✅ Full workflow test successful!")
        print(f"   - Task ID: {task_id}")
        print(f"   - Events found: {len(events)}")
        
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")

# Run the test
test_full_workflow()
```

## 🚨 Common Issues & Solutions

### Issue 1: Authentication Failed
- **Cause**: Invalid credentials or expired token
- **Solution**: Check username/password, refresh token if expired

### Issue 2: Connection Refused
- **Cause**: Servers not running
- **Solution**: Ensure all three servers are started with `make run-all`

### Issue 3: Analysis Timeout
- **Cause**: Long processing time or server issues
- **Solution**: Increase `max_wait` parameter, check server logs

### Issue 4: Invalid Request Format
- **Cause**: Incorrect JSON structure
- **Solution**: Use the examples above, check API documentation

## 📚 Next Steps

1. **Read the full API reference**: `docs/API_ENDPOINTS_REFERENCE.md`
2. **Test with the interactive docs**: Visit `/docs` endpoints in your browser
3. **Implement error handling**: Use the safe wrapper functions
4. **Add retry logic**: For production applications
5. **Monitor performance**: Track API response times

## 🆘 Need Help?

- Check server logs: `pm2 logs`
- Test endpoints manually: Use the `/docs` interfaces
- Verify server status: `pm2 status`
- Check database connectivity: Ensure Redis and PostgreSQL are running
