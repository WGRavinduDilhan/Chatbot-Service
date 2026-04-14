#!/usr/bin/env python3
"""
Test script to verify Gemini API integration is working
"""

import requests
import json
import time
import sys

API_BASE = "http://localhost/api"  # Use nginx proxy on port 80
SESSION_ID = f"test-session-{int(time.time())}"

def test_health():
    """Test if API is healthy"""
    print("=" * 60)
    print("🏥 TEST 1: Checking API Health")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print("✅ API is healthy!")
            print(f"Response: {response.json()}\n")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}\n")
        return False

def test_predefined_rule():
    """Test predefined rule (should NOT call Gemini API)"""
    print("=" * 60)
    print("🎯 TEST 2: Testing Predefined Rule")
    print("=" * 60)
    print("Sending: 'hello' (predefined rule)")
    
    payload = {
        "session_id": SESSION_ID,
        "message": "hello"
    }
    
    try:
        response = requests.post(f"{API_BASE}/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received:")
            print(f"Bot: {data['bot_response']}\n")
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.text}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def test_gemini_api_real_question():
    """Test real Gemini API call with a question that doesn't match rules"""
    print("=" * 60)
    print("🤖 TEST 3: Testing Real Gemini API Call")
    print("=" * 60)
    print("Sending: 'What is the capital of France?' (NOT a predefined rule)")
    print("This SHOULD call Gemini API for a real answer\n")
    
    payload = {
        "session_id": SESSION_ID,
        "message": "What is the capital of France?"
    }
    
    start_time = time.time()
    try:
        response = requests.post(f"{API_BASE}/chat", json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            bot_response = data['bot_response']
            
            print(f"✅ Response received in {elapsed:.2f}s:")
            print(f"Bot: {bot_response}\n")
            
            # Check if it's a real Gemini response or error
            if "Error" in bot_response or "error" in bot_response.lower():
                print("⚠️ Got error response - Check if:")
                print("   1. GEMINI_API_KEY is valid")
                print("   2. API key has permission to use Gemini API")
                print("   3. You haven't hit rate limit (15 requests/minute)\n")
                return False
            else:
                print("✅ Got real response from Gemini API!\n")
                return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.text}\n")
            return False
    except requests.Timeout:
        print(f"❌ Request timed out after 30 seconds")
        print("   This might mean API is slow or Gemini is not responding\n")
        return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def test_chat_history():
    """Test that chat history is being saved"""
    print("=" * 60)
    print("📝 TEST 4: Testing Chat History")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE}/history/{SESSION_ID}")
        if response.status_code == 200:
            data = response.json()
            message_count = data['total_messages']
            print(f"✅ Chat history retrieved!")
            print(f"Total messages in session: {message_count}")
            print(f"Messages: {json.dumps(data['messages'], indent=2)}\n")
            return message_count > 0
        elif response.status_code == 404:
            print(f"⚠️ No history found (session might be new)\n")
            return False
        else:
            print(f"❌ Failed to get history: {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def test_status():
    """Test system status"""
    print("=" * 60)
    print("📊 TEST 5: Checking System Status")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System Status:")
            print(f"Service: {data['service']}")
            print(f"Version: {data['version']}")
            print(f"Memory Status: {json.dumps(data['memory'], indent=2)}\n")
            return True
        else:
            print(f"❌ Failed to get status: {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def main():
    print("\n" + "=" * 60)
    print("🔍 GEMINI API INTEGRATION TEST SUITE")
    print("=" * 60 + "\n")
    
    print(f"Testing API at: {API_BASE}")
    print(f"Session ID: {SESSION_ID}\n")
    
    results = []
    
    # Run all tests
    results.append(("API Health", test_health()))
    results.append(("Predefined Rules", test_predefined_rule()))
    time.sleep(2)  # Respect rate limit
    results.append(("Gemini API Real Call", test_gemini_api_real_question()))
    results.append(("Chat History", test_chat_history()))
    results.append(("System Status", test_status()))
    
    # Print summary
    print("=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    if passed == total:
        print("🎉 All tests passed! Gemini API is working properly!\n")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
