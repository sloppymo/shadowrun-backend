#!/usr/bin/env python3
"""
Test script for Image Generation System
Tests the new image generation endpoints and functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_ping():
    """Test basic server connectivity"""
    print("🔍 Testing server connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/api/ping")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return False

def test_session_creation():
    """Create a test session for image generation"""
    print("\n🔍 Creating test session...")
    try:
        response = requests.post(f"{BASE_URL}/api/session", json={
            "name": "Image Generation Test Session",
            "gm_user_id": "test_gm_user"
        })
        
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data['session_id']
            print(f"✅ Session created: {session_id}")
            return session_id
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return None

def test_join_session(session_id):
    """Join the test session as a player"""
    print(f"\n🔍 Joining session {session_id}...")
    try:
        response = requests.post(f"{BASE_URL}/api/session/{session_id}/join", json={
            "user_id": "test_player_user",
            "role": "player"
        })
        
        if response.status_code == 200:
            print("✅ Successfully joined session")
            return True
        else:
            print(f"❌ Failed to join session: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Session join error: {e}")
        return False

def test_image_providers(session_id):
    """Test getting available image providers"""
    print(f"\n🔍 Testing image providers endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/session/{session_id}/image-providers")
        
        if response.status_code == 200:
            data = response.json()
            providers = data.get('providers', [])
            default = data.get('default')
            print(f"✅ Available providers: {providers}")
            print(f"✅ Default provider: {default}")
            return providers, default
        else:
            print(f"❌ Failed to get providers: {response.status_code}")
            print(response.text)
            return [], None
    except Exception as e:
        print(f"❌ Providers test error: {e}")
        return [], None

def test_image_generation_queue(session_id):
    """Test queued image generation"""
    print(f"\n🔍 Testing queued image generation...")
    try:
        response = requests.post(f"{BASE_URL}/api/session/{session_id}/generate-image", json={
            "user_id": "test_player_user",
            "prompt": "A cyberpunk street scene with neon lights and rain",
            "type": "scene",
            "priority": 2,
            "style_preferences": {
                "provider": "dalle",
                "quality": "standard"
            }
        })
        
        if response.status_code == 200:
            data = response.json()
            request_id = data.get('request_id')
            print(f"✅ Image generation queued: {request_id}")
            return request_id
        else:
            print(f"❌ Failed to queue image generation: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Queue generation error: {e}")
        return None

def test_get_session_images(session_id):
    """Test getting session images"""
    print(f"\n🔍 Testing get session images...")
    try:
        response = requests.get(f"{BASE_URL}/api/session/{session_id}/images?user_id=test_player_user&limit=10")
        
        if response.status_code == 200:
            data = response.json()
            images = data.get('images', [])
            count = data.get('count', 0)
            print(f"✅ Retrieved {count} images")
            for img in images[:3]:  # Show first 3 images
                print(f"   - {img['id']}: {img['prompt'][:50]}...")
            return images
        else:
            print(f"❌ Failed to get images: {response.status_code}")
            print(response.text)
            return []
    except Exception as e:
        print(f"❌ Get images error: {e}")
        return []

def test_image_generation_instant_mock(session_id):
    """Test instant image generation with mock data (no real API calls)"""
    print(f"\n🔍 Testing instant image generation (mock mode)...")
    
    # This would normally fail without API keys, but we can test the endpoint structure
    try:
        response = requests.post(f"{BASE_URL}/api/session/{session_id}/generate-image-instant", json={
            "user_id": "test_player_user",
            "prompt": "A shadowrunner in a dark alley with cybernetic implants",
            "provider": "dalle",
            "style_preferences": {
                "quality": "standard",
                "size": "1024x1024"
            }
        })
        
        # We expect this to fail due to missing API keys, but the endpoint should exist
        if response.status_code == 500:
            error_data = response.json()
            if "API key not configured" in error_data.get('error', ''):
                print("✅ Endpoint exists and correctly reports missing API key")
                return True
            else:
                print(f"⚠️  Unexpected error: {error_data.get('error')}")
                return False
        elif response.status_code == 200:
            print("✅ Image generation succeeded (API key configured)")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Instant generation error: {e}")
        return False

def main():
    """Run all image generation tests"""
    print("🚀 Starting Image Generation System Tests")
    print("=" * 50)
    
    # Test basic connectivity
    if not test_ping():
        print("\n❌ Server not available. Please start the Flask server first.")
        return
    
    # Create test session
    session_id = test_session_creation()
    if not session_id:
        print("\n❌ Cannot proceed without a session")
        return
    
    # Join session
    if not test_join_session(session_id):
        print("\n❌ Cannot proceed without joining session")
        return
    
    # Test image providers
    providers, default = test_image_providers(session_id)
    
    # Test queued generation
    request_id = test_image_generation_queue(session_id)
    
    # Test instant generation (mock)
    test_image_generation_instant_mock(session_id)
    
    # Test getting images
    images = test_get_session_images(session_id)
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print(f"   Session ID: {session_id}")
    print(f"   Available Providers: {len(providers)}")
    print(f"   Images Retrieved: {len(images)}")
    
    if providers:
        print("✅ Image generation system is properly configured")
    else:
        print("⚠️  No image providers available - configure API keys to enable generation")
    
    print("\n💡 To enable image generation:")
    print("   1. Set OPENAI_API_KEY environment variable for DALL-E")
    print("   2. Set STABILITY_API_KEY environment variable for Stable Diffusion")
    print("   3. Restart the Flask server")

if __name__ == "__main__":
    main() 