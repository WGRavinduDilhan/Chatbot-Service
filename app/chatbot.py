# This file act like brain of the chatbot it will process user input and generate response using AI model and also manage conversation history using memory.py
# WE use AI model as Gemini AI for generating responses based on user input and conversation history. It also handles session management and interacts with memory.py to store and retrieve conversation history.

import os
import re
from typing import List, Dict

# Try to import Gemini AI library, if not available, set a flag and print a warning message. This allows the chatbot to function without Gemini AI features while informing the user about the missing dependency.
try:   
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:            # If the library is not found, set the flag to False and print a warning message to inform the user about the missing dependency and how to install it.
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
    }
]

