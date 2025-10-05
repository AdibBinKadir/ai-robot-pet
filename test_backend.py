#!/usr/bin/env python3
"""
AI Robot Pet - Backend Testing Script
Run this to verify your backend integration is working correctly
"""

import os
import sys
import requests
import json
from datetime import datetime

def test_backend_health():
    """Test if backend server is running and healthy"""
    print("🧪 Testing Backend Health...")
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is healthy")
            print(f"   Supabase: {data.get('supabase', 'unknown')}")
            print(f"   Robot AI: {data.get('robot_ai', 'unknown')}")
            return True
        else:
            print(f"❌ Backend unhealthy - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure backend is running: python my-app/src/backend/app.py")
        return False

def test_server_status():
    """Test detailed server status"""
    print("\n🔍 Testing Server Status...")
    try:
        response = requests.get("http://localhost:5000/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server Status Retrieved")
            print(f"   Services: {data.get('services', {})}")
            print(f"   Stats: {data.get('stats', {})}")
            return True
        else:
            print(f"❌ Status check failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return False

def test_image_upload():
    """Test image upload functionality (without actual file)"""
    print("\n📸 Testing Image Upload API...")
    try:
        # Test OPTIONS request (CORS preflight)
        response = requests.options("http://localhost:5000/images", timeout=5)
        if response.status_code == 204:
            print("✅ Image upload CORS configured correctly")
        
        # Test POST without files (should return error but endpoint should work)
        response = requests.post("http://localhost:5000/images", 
                               headers={"x-user-id": "test-user"}, timeout=5)
        
        if response.status_code == 400:  # Expected error for no files
            data = response.json()
            if "no valid image files uploaded" in data.get('error', ''):
                print("✅ Image upload endpoint working (correctly rejects empty uploads)")
                return True
        
        print(f"⚠️  Unexpected image upload response: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ Image upload test error: {e}")
        return False

def test_text_processing():
    """Test AI text processing without audio file"""
    print("\n🤖 Testing AI Text Processing...")
    try:
        # This would require the backend to have a text endpoint
        # For now, just test that the main endpoint exists
        response = requests.post("http://localhost:5000/api/upload-audio", 
                               headers={"x-user-id": "test-user"}, 
                               timeout=5)
        
        # Should get 400 for no audio file
        if response.status_code == 400:
            data = response.json()
            if "No audio file provided" in data.get('error', ''):
                print("✅ Audio processing endpoint working (correctly rejects empty uploads)")
                return True
        
        print(f"⚠️  Unexpected audio processing response: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ AI processing test error: {e}")
        return False

def test_command_history():
    """Test command history retrieval"""
    print("\n📋 Testing Command History...")
    try:
        response = requests.get("http://localhost:5000/api/history?user_id=test-user&limit=5", 
                              timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Command history retrieved")
            print(f"   Source: {data.get('source', 'unknown')}")
            print(f"   Commands: {len(data.get('history', []))}")
            return True
        else:
            print(f"❌ Command history failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Command history error: {e}")
        return False

def test_pending_commands():
    """Test pending commands for Pi client"""
    print("\n⏳ Testing Pending Commands (Pi Client View)...")
    try:
        response = requests.get("http://localhost:5000/api/commands/pending", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pending commands retrieved")
            print(f"   Pending: {len(data.get('commands', []))}")
            return True
        else:
            print(f"❌ Pending commands failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Pending commands error: {e}")
        return False

def run_all_tests():
    """Run all backend tests"""
    print("🚀 AI Robot Pet Backend Test Suite")
    print("=" * 50)
    
    tests = [
        test_backend_health,
        test_server_status,
        test_image_upload,
        test_text_processing,
        test_command_history,
        test_pending_commands
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your backend is working correctly.")
        print("\nNext steps:")
        print("1. Add your actual API keys to backend/.env")
        print("2. Run the database schema in Supabase")
        print("3. Start the frontend: cd my-app && npm run dev")
        print("4. Test the complete system!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        print("\nTroubleshooting:")
        print("- Make sure backend is running: python my-app/src/backend/app.py")
        print("- Check your .env file has correct Supabase credentials")
        print("- Verify Gemini API key is configured")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)