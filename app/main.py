from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from starlette.concurrency import run_in_threadpool
import os

from app.chatbot import get_chatbot_response
from app.memory import ChatMemory

# Initialize chat memory with Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
Chat_memory = ChatMemory(redis_url=redis_url, max_sessions=100, max_messages_per_session=50)

# Create FastAPI app
app = FastAPI(
    title="RADI - Responsive AI Assistant",
    description="AI chatbot powered by Google Gemini",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Pydantic Models ============
class MessageRequest(BaseModel):
    session_id: str
    message: str

class MessageResponse(BaseModel):
    session_id: str
    user_message: str
    bot_response: str
    timestamp: str
    message_count: int

class StatusResponse(BaseModel):
    status: str
    message: str

# ============ Endpoints ============

@app.get("/hello", response_model=StatusResponse)
async def hello():
    """Check if the service is running"""
    return StatusResponse(
        status="success", 
        message="Hello, I'm RADI! Powered by Google Gemini (free)."
    )

@app.get("/health", response_model=StatusResponse)
async def health():
    """Health check endpoint"""
    return StatusResponse(
        status="success",
        message="Service is healthy."
    )

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """Send a message to the chatbot and get a response"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    history = Chat_memory.get_history(request.session_id)
    # The Gemini SDK is synchronous. Run it outside the event loop so one
    # slow model request cannot block health checks or other chat sessions.
    bot_reply = await run_in_threadpool(get_chatbot_response, request.message, history)

    Chat_memory.add_message(request.session_id, role="user", content=request.message)
    Chat_memory.add_message(request.session_id, role="bot", content=bot_reply)

    return MessageResponse(
        session_id=request.session_id,
        user_message=request.message,
        bot_response=bot_reply,
        timestamp=datetime.now().isoformat(),
        message_count=Chat_memory.get_count(request.session_id)
    )

@app.get("/status")
async def status():
    """Check system status and Redis connection"""
    status = Chat_memory.get_status()
    return {
        "service": "RADI Chatbot API",
        "version": "2.0.0",
        "memory": status
    }

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session"""
    history = Chat_memory.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "messages": history,
        "total_messages": len(history)
    }

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear conversation history for a session"""
    Chat_memory.clear_history(session_id)
    return {
        "session_id": session_id,
        "message": "History cleared successfully."
    }

@app.get("/sessions")
async def get_sessions():
    """Get all active sessions"""
    sessions = Chat_memory.get_all_sessions()
    return {
        "active_sessions": sessions,
        "total_sessions": len(sessions)
    }
