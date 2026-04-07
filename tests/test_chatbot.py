import pytest  
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Add parent directory to sys.path

from app.main import app
from app.chatbot import check_rules, get_chatbot_response
from app.memory import ChatMemory

client = TestClient(app)

class TestHealthEndpoints:
    def test_root_returns_200ok(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Chatbot is running!"

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["message"] == "healthy!"

class TestChatbotEndpoint:
    def test_message_under_rules(self):
        response = client.post("/chat", json={
            "session_id": "test-01",
            "message": "Hello"
        })
        assert response.status_code == 200
        data = response.json()
        assert "bot_reply" in data
        assert len(data["bot_reply"]) > 0
        assert data["user_message"] == "Hello"
        assert data["session_id"] == "test-01"

    def test_empty_message_returns_404(self):
        response = client.post("/chat", json={
            "session_id": "test-02",
            "message": ""
        })
        assert response.status_code == 404

    def test_whitespace_message_returns_404(self):
        response = client.post("/chat", json={
            "session_id": "test-03",
            "message": "   "
        })
        assert response.status_code == 404

    def test_message_count_increment(self):
        session = "count-tests"
        r1 = client.post("/chat", json={"session_id": session, "message": "Hello"})
        r2 = client.post("/chat", json={"session_id": session, "message": "How are you?"})
        assert r2.json()["message_count"] > r1.json()["message_count"]

    def test_missing_fields_returns_422(self):
        response = client.post("/chat", json={
            "session_id": "test-04"
        })
        assert response.status_code == 422

    def test_gemini_unknown_api_response(self):
        with patch("app.chatbot.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = "Unknown API RESPONSE"
            mock_client.models.generate_content.return_value = mock_response

            with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key-test"}):
                response = client.post("/chat", json={
                    "session_id": "gemini-test",
                    "message": "What is the longest river?"
                })

            assert response.status_code == 200
            assert response.json()["bot_reply"] == "Unknown API RESPONSE"

class TestHistoryEndpoints:
    def test_get_empty_history(self):
        response = client.get("/history/brand-new-session-xyz")
        assert response.status_code == 200
        assert response.json()["messages"] == []

    def test_history_after_chat(self):
        session = "history-test-session"
        client.post("/chat", json={"session_id": session, "message": "Hello"})
        response = client.get(f"/history/{session}")
        assert response.json()["total"] > 0

    def test_clear_history(self):
        session = "clear-test-session"
        client.post("/chat", json={"session_id": session, "message": "Hello"})
        client.delete(f"/history/{session}")
        history = client.get(f"/history/{session}").json()
        assert history["total"] == 0



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

            
               


            

