# This is the main chatbot logic file. 
# It defines the rules for handling specific user inputs and integrates with Google Gemini for generating responses when no rules match. 
# It also includes error handling for API issues and missing configurations.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List

from app.chatbot import get_chatbot_response
from app.memory import ChatMemory

# Initialize chat memory and FastAPI app
app = FastAPI(
    title = "RADI - Responsive AI Assistant",
    description = "RADI is a responsive AI assistant powered by Google Gemini via API.",
    version = "2.0.0"
)

# CORS middleware to allow cross-origin requests from any domain (for frontend integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Chat_memory = ChatMemory(max_sessions=100, max_messages_per_session=50)

# Predefined rules for specific user inputs and their corresponding responses.
class MessageRequest(BaseModel):
    session_id: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user123",
                "message": "Hello, how are you?"
            }
        }

# Predefined rules for specific user inputs and their corresponding responses.
class MessageResponse(BaseModel):
    session_id: str
    user_message: str
    bot_response: str
    timestamp: str
    message_count: int

# Predefined rules for specific user inputs and their corresponding responses.
class HelloRequest(BaseModel):
    status: str
    message: str

@app.get("/hello", response_model=HelloRequest) # Simple endpoint to check if the service is running and to provide basic information about the chatbot.
async def root():
    return HelloRequest(
        status="success", 
        message="Hello, I'm RADI! Powered by Google Gemini (free). Visit /docs for more information."
        )


@app.get("/health", response_model=HelloRequest) # Health check endpoint to verify that the service is operational and can be used for monitoring or load balancer health checks.
async def health_check():
    return HelloRequest(
        status="success",
        message="Service is healthy."
    )

@app.post("/chat", response_model=MessageResponse) # Main endpoint to handle user messages, generate responses using the chatbot logic, and manage conversation history.
async def chat(request: MessageRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    history = Chat_memory.get_history(request.session_id) # Retrieve conversation history for the session to provide context for the chatbot's response.
    bot_reply = get_chatbot_response(request.message, history) # This function generates a response from the chatbot based on the user's message and the conversation history. it will check predefined rules first and then call Google Gemini if no rules match.

    Chat_memory.add_message(request.session_id, role="user", content=request.message) # Add the user's message to the conversation history.
    Chat_memory.add_message(request.session_id, role="bot", content=bot_reply) # Add the chatbot's response to the conversation history.

    return MessageResponse( # Return the chatbot's response along with session information and message count for the frontend to display and manage the conversation.
        session_id=request.session_id,
        user_message=request.message,
        bot_response=bot_reply,
        timestamp=datetime.now().isoformat(),
        message_count=Chat_memory.get_count(request.session_id)

    )

@app.get("/history/{session_id}") # Endpoint to retrieve the conversation history for a specific session, allowing users to see past interactions with the chatbot.
async def get_history(session_id: str):  
    history = Chat_memory.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "messages": history, "total_messages": len(history)}


@app.delete("/history/{session_id}") # Endpoint to clear the conversation history for a specific session.
async def clear_history(session_id: str):
    Chat_memory.clear_history(session_id)
    return {"session_id": session_id, "message": "History cleared successfully."}


@app.get("/sessions") # Endpoint to retrieve a list of all active sessions and the total number of sessions.
async def get_sessions():
    return{
        "active_sessions": Chat_memory.get_all_sessions(),
        "total_sessions": len(Chat_memory.get_all_sessions())
    }