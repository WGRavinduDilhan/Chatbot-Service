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
        assert response.json()["status"]== {"message": "Chatbot is running!"}

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == {"message": "healthy!"}

class TestChatbotendpoint:
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

    def gemini_unkown_api_response(self):
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

            
               


            

