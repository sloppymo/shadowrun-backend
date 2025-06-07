#!/usr/bin/env python3
"""
Test script for the Shadowrun DM Review System
This script tests the new DM review functionality without requiring a full frontend setup.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_dm_review_system():
    print("🎲 Testing Shadowrun DM Review System")
    print("=" * 50)
    
    # Test 1: Create a session
    print("\n1. Creating a test session...")
    session_data = {
        "name": "Test DM Review Session",
        "gm_user_id": "test-gm-123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/session", json=session_data)
        if response.status_code == 200:
            session_info = response.json()
            session_id = session_info['session_id']
            print(f"✅ Session created: {session_id}")
        else:
            print(f"❌ Failed to create session: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure the Flask server is running on port 5000.")
        return
    
    # Test 2: Join session as a player
    print("\n2. Adding a player to the session...")
    join_data = {
        "user_id": "test-player-456",
        "role": "player"
    }
    
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/join", json=join_data)
    if response.status_code == 200:
        print("✅ Player joined session")
    else:
        print(f"❌ Failed to join session: {response.status_code}")
        return
    
    # Test 3: Create a pending AI response
    print("\n3. Creating a pending AI response for DM review...")
    ai_request_data = {
        "user_id": "test-player-456",
        "context": "I want to hack into the corporate mainframe using my cyberdeck.",
        "response_type": "narrative",
        "priority": 2,
        "require_review": True
    }
    
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/llm-with-review", json=ai_request_data)
    if response.status_code == 200:
        ai_response = response.json()
        if ai_response.get('status') == 'pending_review':
            pending_id = ai_response['pending_response_id']
            print(f"✅ AI response created for review: {pending_id}")
        else:
            print(f"❌ Unexpected response: {ai_response}")
            return
    else:
        print(f"❌ Failed to create AI response: {response.status_code}")
        return
    
    # Test 4: Check pending responses (as GM)
    print("\n4. Checking pending responses...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}/pending-responses?user_id=test-gm-123")
    if response.status_code == 200:
        pending_responses = response.json()
        print(f"✅ Found {len(pending_responses)} pending response(s)")
        if pending_responses:
            first_response = pending_responses[0]
            print(f"   - Response ID: {first_response['id']}")
            print(f"   - Player: {first_response['user_id']}")
            print(f"   - Context: {first_response['context'][:50]}...")
    else:
        print(f"❌ Failed to fetch pending responses: {response.status_code}")
        return
    
    # Test 5: Review and approve the response
    print("\n5. Reviewing and approving the response...")
    review_data = {
        "user_id": "test-gm-123",
        "action": "edit",
        "final_response": "The GM allows your hack attempt. Roll 6 dice for your Cybertechnology + Logic test. The target system has Firewall 4.",
        "dm_notes": "Player attempted a reasonable hacking action. Approved with some modifications for game balance."
    }
    
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/pending-response/{pending_id}/review", json=review_data)
    if response.status_code == 200:
        print("✅ Response reviewed and approved")
    else:
        print(f"❌ Failed to review response: {response.status_code}")
        return
    
    # Test 6: Check notifications
    print("\n6. Checking DM notifications...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}/dm/notifications?user_id=test-gm-123")
    if response.status_code == 200:
        notifications = response.json()
        print(f"✅ Found {len(notifications)} notification(s)")
    else:
        print(f"❌ Failed to fetch notifications: {response.status_code}")
    
    # Test 7: Check approved responses for player
    print("\n7. Checking approved responses for player...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}/player/test-player-456/approved-responses")
    if response.status_code == 200:
        approved_responses = response.json()
        print(f"✅ Found {len(approved_responses)} approved response(s)")
        if approved_responses:
            latest_response = approved_responses[0]
            print(f"   - Final response: {latest_response['final_response'][:50]}...")
            print(f"   - DM notes: {latest_response['dm_notes'][:50]}...")
    else:
        print(f"❌ Failed to fetch approved responses: {response.status_code}")
    
    print("\n🎉 DM Review System test completed!")
    print(f"Session ID for manual testing: {session_id}")

if __name__ == "__main__":
    test_dm_review_system() 