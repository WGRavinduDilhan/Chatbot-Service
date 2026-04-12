import pytest  
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.chatbot import check_rules, get_chatbot_response
from app.memory import ChatMemory

# Create a test client
client = TestClient(app)

# ==== TEST SUITE 1: Health & Status Endpoints ====
class TestHealthEndpoints:
    """Test service health check and status endpoints"""
    
    def test_health_check_returns_200(self):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Service is healthy" in data["message"]

    def test_hello_endpoint_returns_200(self):
        """Test /hello endpoint"""
        response = client.get("/hello")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "RADI" in data["message"]

    def test_status_endpoint_shows_redis_info(self):
        """Test /status endpoint returns Redis connection info"""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "memory" in data
        assert data["service"] == "RADI Chatbot API"

# ==== TEST SUITE 2: Chat Endpoint ====
class TestChatbotEndpoint:
    """Test chat functionality with rules and AI"""
    
    def test_rule_matched_response(self):
        """Test message that matches a rule (instant response)"""
        response = client.post("/chat", json={
            "session_id": "test-rule-01",
            "message": "hello"
        })
        assert response.status_code == 200
        data = response.json()
        assert "bot_response" in data
        assert len(data["bot_response"]) > 0
        assert data["user_message"] == "hello"
        assert data["session_id"] == "test-rule-01"
        assert data["message_count"] == 2  # user + bot

    def test_different_rule_matches(self):
        """Test various rule patterns"""
        rules_to_test = [
            ("hi", "RADI"),  # greeting rule
            ("thanks", "welcome"),  # gratitude rule
            ("bye", "Goodbye"),  # farewell rule
            ("joke", "programmers"),  # joke rule
        ]
        
        for message, expected_keyword in rules_to_test:
            response = client.post("/chat", json={
                "session_id": f"test-rules-{message}",
                "message": message
            })
            assert response.status_code == 200
            bot_response = response.json()["bot_response"]
            assert expected_keyword.lower() in bot_response.lower()

    def test_empty_message_returns_400(self):
        """Test that empty message raises 400 error"""
        response = client.post("/chat", json={
            "session_id": "test-empty-01",
            "message": ""
        })
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"].lower()

    def test_whitespace_message_returns_400(self):
        """Test that whitespace-only message raises 400 error"""
        response = client.post("/chat", json={
            "session_id": "test-whitespace-01",
            "message": "   \n\t  "
        })
        assert response.status_code == 400

    def test_missing_session_id_returns_422(self):
        """Test that missing session_id raises 422 validation error"""
        response = client.post("/chat", json={
            "message": "Hello"
        })
        assert response.status_code == 422

    def test_missing_message_returns_422(self):
        """Test that missing message raises 422 validation error"""
        response = client.post("/chat", json={
            "session_id": "test-missing-msg"
        })
        assert response.status_code == 422

    def test_message_count_increments(self):
        """Test that message count increases with each message"""
        session = "test-count-increments"
        response1 = client.post("/chat", json={
            "session_id": session,
            "message": "Hello"
        })
        count1 = response1.json()["message_count"]
        
        response2 = client.post("/chat", json={
            "session_id": session,
            "message": "How are you?"
        })
        count2 = response2.json()["message_count"]
        
        assert count2 > count1
        assert count1 == 2  # first user msg + bot response
        assert count2 == 4  # second user msg + bot response

    def test_timestamp_is_iso_format(self):
        """Test that response includes ISO format timestamp"""
        response = client.post("/chat", json={
            "session_id": "test-timestamp",
            "message": "hello"
        })
        assert response.status_code == 200
        timestamp = response.json()["timestamp"]
        # Check ISO format: YYYY-MM-DDTHH:MM:SS
        assert "T" in timestamp
        assert "-" in timestamp
        assert ":" in timestamp

# ==== TEST SUITE 3: History Endpoint ====
class TestHistoryEndpoints:
    """Test conversation history retrieval"""
    
    def test_new_session_returns_empty_history(self):
        """Test that new session has no history"""
        response = client.get("/history/brand-new-session-xyz-123")
        assert response.status_code == 404  # Session not found
        assert "not found" in response.json()["detail"].lower()

    def test_history_after_chat(self):
        """Test history is saved after chat message"""
        session = "test-history-save"
        
        # Send a message
        client.post("/chat", json={
            "session_id": session,
            "message": "Hello"
        })
        
        # Retrieve history
        response = client.get(f"/history/{session}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session
        assert len(data["messages"]) > 0
        assert data["total_messages"] > 0

    def test_history_contains_role_and_timestamp(self):
        """Test that history messages have role and timestamp"""
        session = "test-history-format"
        
        client.post("/chat", json={
            "session_id": session,
            "message": "Test message"
        })
        
        response = client.get(f"/history/{session}")
        messages = response.json()["messages"]
        
        for msg in messages:
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg
            assert msg["role"] in ["user", "bot"]

    def test_multiple_sessions_have_separate_history(self):
        """Test that different sessions don't share history"""
        session1 = "test-separate-1"
        session2 = "test-separate-2"
        
        # Session 1 message
        client.post("/chat", json={
            "session_id": session1,
            "message": "I am session 1"
        })
        
        # Session 2 message
        client.post("/chat", json={
            "session_id": session2,
            "message": "I am session 2"
        })
        
        # Check histories are different
        hist1 = client.get(f"/history/{session1}").json()["messages"]
        hist2 = client.get(f"/history/{session2}").json()["messages"]
        
        assert hist1[0]["content"] != hist2[0]["content"]

# ==== TEST SUITE 4: Rule-Based System ====
class TestRuleSystem:
    """Test the rule-based response system"""
    
    def test_check_rules_function(self):
        """Test the check_rules function directly"""
        # Test greeting
        result = check_rules("Hello")
        assert result is not None
        assert "RADI" in result
        
        # Test no match returns None
        result = check_rules("xyzabc123notarule")
        assert result is None

    def test_rule_case_insensitive(self):
        """Test that rules work regardless of case"""
        result = check_rules("HELLO")
        assert result is not None
        
        result = check_rules("HeLLo")
        assert result is not None

    def test_rule_with_extra_text(self):
        """Test rules match even with extra text"""
        result = check_rules("hey there, how are you today?")
        assert result is not None  # Should match "hey"

# ==== TEST SUITE 5: Integration Tests ====
class TestIntegration:
    """Test full workflow scenarios"""
    
    def test_conversation_flow(self):
        """Test a complete conversation flow"""
        session = "test-integration-flow"
        
        # Step 1: Greeting
        r1 = client.post("/chat", json={
            "session_id": session,
            "message": "Hi"
        })
        assert r1.status_code == 200
        reply1 = r1.json()["bot_response"]
        assert "RADI" in reply1
        
        # Step 2: Another message in same session
        r2 = client.post("/chat", json={
            "session_id": session,
            "message": "What is your name?"
        })
        assert r2.status_code == 200
        reply2 = r2.json()["bot_response"]
        assert "RADI" in reply2
        
        # Step 3: Verify history
        hist = client.get(f"/history/{session}").json()
        assert hist["total_messages"] == 4  # 2 user + 2 bot

    def test_concurrent_users(self):
        """Test multiple concurrent users"""
        sessions = ["user-1", "user-2", "user-3"]
        
        for session in sessions:
            response = client.post("/chat", json={
                "session_id": session,
                "message": "Hello"
            })
            assert response.status_code == 200
        
        # Verify all sessions have history
        for session in sessions:
            hist = client.get(f"/history/{session}").json()
            assert hist["total_messages"] > 0



class TestRuleBasedResponses:
    def test_greeting_matched(self):
        assert check_rules("hello") is not None
        assert check_rules("hi there") is not None

    def test_farewell_matched(self):
        assert check_rules("goodbye") is not None

    def test_joke_matched(self):
        assert check_rules("tell me a joke") is not None

    def test_unknown_returns_none(self):
        # Unknown question → should go to Gemini (returns None from rules)
        assert check_rules("What is the capital of France?") is None

    def test_case_insensitive(self):
        assert check_rules("HELLO") is not None
        assert check_rules("hElLo") is not None

    def test_gemini_rule_matched(self):
        """NEW — test the new Gemini-specific rule"""
        assert check_rules("tell me about gemini") is not None



class TestChatMemory:
    def setup_method(self):
        self.memory = ChatMemory(max_sessions=5, max_messages_per_session=10)

    def test_add_and_retrieve(self):
        self.memory.add_message("s1", "user", "Hello!")
        history = self.memory.get_history("s1")
        assert len(history) == 1
        assert history[0]["content"] == "Hello!"

    def test_role_stored_correctly(self):
        """
        IMPORTANT FOR GEMINI: Our memory stores role as "bot".
        chatbot.py maps "bot" → "model" when sending to Gemini.
        Make sure this conversion works correctly.
        """
        self.memory.add_message("s2", "bot", "Hi there!")
        history = self.memory.get_history("s2")
        assert history[0]["role"] == "bot"  # stored as "bot"
        # chatbot.py then maps this to "model" for Gemini

    def test_multiple_sessions_isolated(self):
        self.memory.add_message("alice", "user", "Alice's message")
        self.memory.add_message("bob", "user", "Bob's message")
        alice = self.memory.get_history("alice")
        assert len(alice) == 1
        assert alice[0]["content"] == "Alice's message"

    def test_clear_session(self):
        self.memory.add_message("test", "user", "msg")
        self.memory.clear_history("test")
        assert self.memory.get_count("test") == 0

            
               


            

