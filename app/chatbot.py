# This file act like brain of the chatbot it will process user input and generate response using AI model and also manage conversation history using memory.py
# WE use AI model as Gemini AI for generating responses based on user input and conversation history. It also handles session management and interacts with memory.py to store and retrieve conversation history.

import os
import re
from typing import List, Dict, Optional

# Try to import Gemini AI library, if not available, set a flag and print a warning message. This allows the chatbot to function without Gemini AI features while informing the user about the missing dependency.
try:   
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:            # If the library is not found, set the flag to False and print a warning message to inform the user about the missing dependency and how to install it.
    genai = None  # Ensure genai is always defined to avoid "possibly unbound" errors
    GEMINI_AVAILABLE = False
    print("Gemini AI library not found. Please install google-generativeai to use Gemini AI features. use 'pip install google-generativeai' to install.")

# Phase 1 : Role Based Response Generation

Rules = [
    {
        "pattern": r"\b(hi|hello|hey|greetings)\b",
        "response": "Hello! I am RADI assistant powered by GEMINI AI, How can I assist you today?"
    },
    {
        "pattern": r"\b(bye|farewell|goodbye|see you|exit|quit)\b",
        "response": "Goodbye! Have a wonderful day! :) Feel free to come back anytime."
    },
    {
        "pattern": r"\b(thank you|thanks|thx|grateful)\b",
        "response": "You're welcome! Is there anything else I can help you with?"
    },
    {
        "pattern": r"\b(your name|who are you|what is your name)\b",
        "response": "I am RADI, a helpful assistant powered by GEMINI AI."
    },
    {
        "pattern": r"\b(how are you|how are you doing|how do you do)\b",
        "response": "I'm doing well, thank you for asking! How can I help you today?"
    },
    {
        "pattern": r"\b(help|what can you do|what are your capabilities|what can you help with)\b",
        "response": ( "I can assist you with a wide range of tasks, including answering questions, providing information, generating text, and more \n"
                      "Powered by Gemini AI, I can understand and respond to a variety of topics. \n"
                      "Just ask me anything you'd like help with!" )
    },
    {
        "pattern": r"\b(joke|funny|make me laugh)\b",
        "response": "Why do programmers prefer dark mode? Because light attracts bugs! 😄"
    },
    {
        "pattern": r"\b(weather|forecast|temperature)\b",
        "response": "I don't have real-time weather information, but I can help you find it! You can check your local weather by searching online or using a weather app. Is there anything else I can assist you with?"
    },
    {
        "pattern": r"\b(gemini|google ai|google gemini)\b",
        "response": "Yes, I'm powered by Google Gemini! It's Google's AI model — free to use via API. No credit card needed! 🎉"
    },
    {
        "pattern": r"\b(swot|swot analysis|strengths|weaknesses|opportunities|threats)\b",
        "response": "SWOT Analysis consists of:\n✅ **Strengths** - Internal positive factors\n⚠️ **Weaknesses** - Internal challenges\n🚀 **Opportunities** - External positive factors\n⛔ **Threats** - External risks\nIt's used for strategic planning!"
    },
    {
        "pattern": r"\b(docker|containers|container|containerization)\b",
        "response": "🐳 **Docker** in simple terms:\nDocker packages your app + all dependencies into a 'container' - like a shipping box that works the same everywhere! You can run it on any computer without worrying about differences. It's lightweight and efficient!"
    },
    {
        "pattern": r"\b(fun fact|random fact|tell me a fact|interesting fact)\b",
        "response": "🤓 **Fun Fact**: Honey never spoils! Archaeologists found 3,000-year-old honey in Egyptian tombs that was still perfectly edible. Honey has such low moisture and high acidity that bacteria can't grow in it!"
    },
    {
        "pattern": r"\b(who are you|what are you|about yourself|tell me about yourself)\b",
        "response": "👋 I'm **RADI** (Responsive AI Assistant)! I'm an AI chatbot powered by Google Gemini. I can answer questions, have conversations, and help with various tasks. I have predefined answers for common questions and use AI for complex topics!"
    },
    {
        "pattern": r"\b(time|date|what time|what's the time)\b",
        "response": "⏰ I can't tell the current time or date, but you can check your system clock or search 'current time' online!"
    }
]

# This function checks if the user's message matches any of the predefined rules and returns the corresponding response.
#Check if message matches any rule and return the response if found, otherwise return None.
def check_rules(message: str):
    
    message = message.lower().strip()
    for rule in Rules:
        if re.search(rule["pattern"], message):
            return rule["response"]
    return None


#Send message to Google Gemini and get a response.
def get_gemini_response(message: str, history: List[Dict]) -> str:
    
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        return (
            "⚠️ GEMINI_API_KEY not set in your .env file!\n"
            "Get your free key at: https://aistudio.google.com\n"
            "Then add to .env: GEMINI_API_KEY=AIzaSy..."
        )

    if not GEMINI_AVAILABLE:
        return "⚠️ google-genai package not installed. Run: pip install google-genai"

    if not genai:
        return "⚠️ google-generativeai library not available. Please install it first."
    
    try:
        # Step 1: Configure the Gemini API with your API key
        genai.configure(api_key=api_key)

        # Step 2: Create the model instance
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=(
                "You are a helpful, friendly, and concise AI assistant. "
                "Keep responses clear and under 150 words unless the user asks for detail. "
                "Use emojis occasionally to be friendly. "
                "If you don't know something, say so honestly."
            )
        )

        # Step 3: Build conversation history for chat
        chat_history = []
        for msg in history[-10:]:  # Last 10 messages (keeps cost/tokens low)
            chat_history.append({
                "role": "model" if msg["role"] == "bot" else "user",
                "parts": msg["content"]
            })

        # Step 4: Start a chat session and send the message
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(
            message,
            generation_config={
                "max_output_tokens": 300,
                "temperature": 0.7,
            }
        )

        # Step 5: Return the response text
        return response.text


    except Exception as e:
        # Always handle errors gracefully!
        error_msg = str(e)

        # Give helpful hints for common errors
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return "❌ Invalid Gemini API key. Check your GEMINI_API_KEY in .env"
        elif "quota" in error_msg.lower() or "429" in error_msg:
            return "⏳ Rate limit hit. Free tier allows 15 requests/minute. Try again in a moment!"
        elif "SAFETY" in error_msg:
            return "🔒 That message was blocked by Gemini's safety filters. Please rephrase."
        else:
            return f"❌ Gemini API error: {error_msg}. Please try again."


# Main entry point to call main.py to process user input and generate response.

def get_chatbot_response(message: str, history: List[Dict]) -> str:
    # First, check if the message matches any predefined rules
    # Role based response creation 
    rule_response = check_rules(message)
    if rule_response:
        return rule_response

    # If no any rules matched, get a response from Gemini AI
    gemini_response = get_gemini_response(message, history)
    return gemini_response



