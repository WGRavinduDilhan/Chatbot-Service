# This memory.py file for memory management, saving and loading conversation history, and managing user sessions.
# Also as indetail HTTP is stateless so each request independent and can not remember previous requests this file manually store conversation history so AI can read and go on

from typing import List, Dict
from datetime import datetime
import collections
from collections import OrderedDict

# This Manages chat history for multiple users Uses dictionary type to hold data key as session id and value as list of messages [{role, content, timestamp}]
class ChatMemory:

    def __init__(self, max_sessions: int=100, max_messages_per_session: int=50):

        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session

        self._storage: OrderedDict[str, List[Dict]] = collections.OrderedDict()  # session_id -> list of messages


    def _ensure_session(self, session_id: str):

        # Create new session if it doesn't exist, or mark it as recently used if it does
        if session_id not in self._storage:
            if len(self._storage) >= self.max_sessions:
                oldest_key = next(iter(self._storage))
                del self._storage[oldest_key]
                print(f"Memory limit reached. Oldest session '{oldest_key}' removed.")

            # Create new session
            self._storage[session_id] = []
        else:
            self._storage.move_to_end(session_id)  # Mark as most recently used


    def add_message(self, session_id: str, role: str, content: str):
        # Add message to session history, ensuring session exists and managing memory limits
        self._ensure_session(session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self._storage[session_id].append(message)

        if len(self._storage[session_id]) > self.max_messages_per_session:  # If message limit exceeded, remove oldest message
            self._storage[session_id] = self._storage[session_id][-self.max_messages_per_session:]  # Keep only the most recent messages


    def get_history(self, session_id: str) -> List[Dict]:   # Retrieve conversation history for a session, or return empty list if session doesn't exist 
        return self._storage.get(session_id, [])
    

    def get_count(self, session_id: str) -> int:  # Get the number of messages in a session, or return 0 if session doesn't exist
        return len(self._storage.get(session_id, []))
    
    
    def clear_history(self, session_id: str): # Clear conversation history for a session, or do nothing if session doesn't exist refresh session
        if session_id in self._storage:       
            del self._storage[session_id] 


    def get_all_sessions(self) -> List[str]:  # Get a list of all active session IDs this very useful for admin
        return list(self._storage.keys())
    

    def get_status(self) -> Dict:  # Get memory status including total sessions, max sessions, and message count per session for monitoring and debugging
        return {
            "total sessions" : len(self._storage),
            "max sessions" : self.max_sessions,
            "sessions": {session_id: len(messages) for session_id, messages in self._storage.items()}
        }
    



        
    

