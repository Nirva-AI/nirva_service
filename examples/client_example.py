#!/usr/bin/env python3
"""
Example client for Nirva Service API

This script demonstrates how to integrate with the Nirva Service API
for common use cases like transcript analysis and event retrieval.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class NirvaClient:
    """Client for interacting with Nirva Service API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", chat_url: str = "http://localhost:8200"):
        self.base_url = base_url
        self.chat_url = chat_url
        self.token = None
        self.headers = {}
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate and get JWT token"""
        try:
            response = requests.post(f"{self.base_url}/login/v1/", json={
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print(f"✅ Authenticated successfully as {username}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def upload_transcript(self, date: str, content: str) -> Optional[Dict[str, Any]]:
        """Upload transcript content for analysis"""
        try:
            response = requests.post(
                f"{self.base_url}/action/upload_transcript/v1/",
                json={
                    "transcripts": [{
                        "time_stamp": date,
                        "content": content
                    }]
                },
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Transcript uploaded successfully for {date}")
                return result
            else:
                print(f"❌ Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    def start_analysis(self, date: str, file_number: int = 1) -> Optional[str]:
        """Start analysis task for uploaded transcript"""
        try:
            response = requests.post(
                f"{self.base_url}/action/analyze/v1/",
                json={
                    "time_stamp": date,
                    "file_number": file_number
                },
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result["task_id"]
                print(f"✅ Analysis started with task ID: {task_id}")
                return task_id
            else:
                print(f"❌ Analysis start failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Analysis start error: {e}")
            return None
    
    def check_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Check the status of a background task"""
        try:
            response = requests.get(
                f"{self.base_url}/action/task/status/v1/{task_id}/",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Status check failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return None
    
    def wait_for_analysis(self, task_id: str, max_wait: int = 300) -> Optional[Dict[str, Any]]:
        """Wait for analysis to complete and return results"""
        print(f"⏳ Waiting for analysis to complete (max {max_wait}s)...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_data = self.check_task_status(task_id)
            
            if not status_data:
                time.sleep(2)
                continue
            
            status = status_data.get("status")
            
            if status == "completed":
                print("✅ Analysis completed successfully!")
                return status_data.get("result", {}).get("journal_file")
            elif status == "failed":
                error = status_data.get("error", "Unknown error")
                print(f"❌ Analysis failed: {error}")
                return None
            
            # Still processing
            print(f"⏳ Analysis in progress... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(2)
        
        print("❌ Analysis timeout")
        return None
    
    def get_events(self, date: str) -> Optional[Dict[str, Any]]:
        """Get all events for a specific date"""
        try:
            response = requests.post(
                f"{self.base_url}/action/analyze/events/get/v1/",
                json={"time_stamp": date},
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Retrieved {data['total_count']} events for {date}")
                return data
            else:
                print(f"❌ Get events failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Get events error: {e}")
            return None
    
    def incremental_analyze(self, date: str, new_content: str) -> Optional[Dict[str, Any]]:
        """Perform incremental analysis on new content"""
        try:
            response = requests.post(
                f"{self.base_url}/action/analyze/incremental/v1/",
                json={
                    "time_stamp": date,
                    "new_transcript": new_content
                },
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Incremental analysis completed:")
                print(f"   - Updated events: {result['updated_events_count']}")
                print(f"   - New events: {result['new_events_count']}")
                print(f"   - Total events: {result['total_events_count']}")
                return result
            else:
                print(f"❌ Incremental analysis failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Incremental analysis error: {e}")
            return None
    
    def chat_with_ai(self, message: str, chat_history: Optional[list] = None) -> Optional[str]:
        """Send a message to the AI chat service"""
        if chat_history is None:
            chat_history = []
        
        try:
            import uuid
            
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
                f"{self.chat_url}/action/chat/v1/",
                json=chat_request,
                headers=self.headers
            )
            
            if response.status_code == 200:
                ai_message = response.json()["ai_message"]
                print(f"🤖 AI: {ai_message['content']}")
                return ai_message["content"]
            else:
                print(f"❌ Chat failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return None


def main():
    """Main example demonstrating API usage"""
    print("🚀 Nirva Service API Client Example")
    print("=" * 50)
    
    # Initialize client
    client = NirvaClient()
    
    # Test credentials (replace with actual credentials)
    username = "test_user"
    password = "test_password"
    
    # 1. Authenticate
    if not client.authenticate(username, password):
        print("❌ Cannot proceed without authentication")
        return
    
    print("\n📝 Example 1: Complete Analysis Workflow")
    print("-" * 40)
    
    # Test date and content
    test_date = "2025-01-20"
    test_content = """
    Today I had a productive morning meeting with the development team. 
    We discussed the new project requirements and set clear goals for the sprint. 
    After lunch, I worked on the API documentation and reviewed some pull requests. 
    The team collaboration was excellent and we made good progress.
    """
    
    # 2. Upload transcript
    upload_result = client.upload_transcript(test_date, test_content)
    if not upload_result:
        print("❌ Cannot proceed without transcript upload")
        return
    
    # 3. Start analysis
    task_id = client.start_analysis(test_date)
    if not task_id:
        print("❌ Cannot proceed without analysis task")
        return
    
    # 4. Wait for analysis completion
    journal_file = client.wait_for_analysis(task_id, max_wait=60)  # Wait up to 60 seconds
    if not journal_file:
        print("❌ Analysis did not complete successfully")
        return
    
    # 5. Get events
    events_data = client.get_events(test_date)
    if events_data:
        print(f"\n📊 Retrieved Events:")
        for i, event in enumerate(events_data["events"], 1):
            print(f"   {i}. {event.get('title', 'No title')}")
            print(f"      Description: {event.get('description', 'No description')}")
            print(f"      Tags: {', '.join(event.get('tags', []))}")
            print()
    
    print("\n📝 Example 2: Incremental Analysis")
    print("-" * 40)
    
    # Add new content for incremental analysis
    new_content = "Just finished a client call discussing the new feature requirements."
    incremental_result = client.incremental_analyze(test_date, new_content)
    
    print("\n📝 Example 3: Chat with AI")
    print("-" * 40)
    
    # Chat with AI about the day
    chat_response = client.chat_with_ai("Based on my activities today, what should I focus on tomorrow?")
    
    print("\n✅ Example completed successfully!")
    print("\n💡 Tips:")
    print("   - Check the interactive API docs at /docs endpoints")
    print("   - Use proper error handling in production code")
    print("   - Implement retry logic for network issues")
    print("   - Monitor API response times")


if __name__ == "__main__":
    main()
