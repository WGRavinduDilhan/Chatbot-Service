# This memory.py file manages persistent chat history using Redis with fallback to in-memory storage
# Redis stores conversation history so AI can retrieve past context and maintain persistent sessions across restarts
# If Redis is unavailable, falls back to in-memory OrderedDict storage

import redis
import json
from typing import List, Dict
from datetime import datetime
import os
from collections import OrderedDict

class ChatMemory:
    """Manages chat history using Redis with fallback to in-memory storage"""

    def __init__(self, redis_url: str = None, max_sessions: int = 100, max_messages_per_session: int = 50):
        """
        Initialize Redis connection with fallback to in-memory storage
        
        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379)
            max_sessions: Maximum number of active sessions to maintain
            max_messages_per_session: Maximum messages to keep per session
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Try to connect to Redis
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            print(f"✅ Redis connected: {redis_url}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("⚠️ Using in-memory fallback storage instead")
            self.redis_client = None
        
        # Fallback in-memory storage (always available)
        self._fallback_storage: OrderedDict[str, List[Dict]] = OrderedDict()
        
        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session
        self.SESSIONS_KEY = "chatbot:sessions"
        self.MESSAGE_PREFIX = "chatbot:messages:"

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session history with Redis persistence or in-memory fallback"""
        if not session_id:
            return
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.redis_client:
            try:
                # Store message as JSON in Redis list
                message_key = f"{self.MESSAGE_PREFIX}{session_id}"
                self.redis_client.rpush(message_key, json.dumps(message))
                
                # Keep only the latest messages
                self.redis_client.ltrim(message_key, -self.max_messages_per_session, -1)
                
                # Set expiration: 7 days (604800 seconds)
                self.redis_client.expire(message_key, 604800)
                
                # Add session to sessions set
                self.redis_client.sadd(self.SESSIONS_KEY, session_id)
                
            except Exception as e:
                print(f"❌ Error adding message to Redis: {e}")
                print("⚠️ Storing in memory instead")
                self._add_to_fallback(session_id, message)
        else:
            # Use fallback in-memory storage
            self._add_to_fallback(session_id, message)

    def _add_to_fallback(self, session_id: str, message: Dict):
        """Add message to in-memory fallback storage"""
        if session_id not in self._fallback_storage:
            # Manage session limits
            if len(self._fallback_storage) >= self.max_sessions:
                oldest_key = next(iter(self._fallback_storage))
                del self._fallback_storage[oldest_key]
                print(f"Memory limit reached. Oldest session '{oldest_key}' removed.")
            
            self._fallback_storage[session_id] = []
        else:
            # Mark as recently used
            self._fallback_storage.move_to_end(session_id)
        
        # Add message
        self._fallback_storage[session_id].append(message)
        
        # Keep only latest messages
        if len(self._fallback_storage[session_id]) > self.max_messages_per_session:
            self._fallback_storage[session_id] = self._fallback_storage[session_id][-self.max_messages_per_session:]

    def get_history(self, session_id: str) -> List[Dict]:
        """Retrieve conversation history for a session from Redis or fallback"""
        if not session_id:
            return []
        
        if self.redis_client:
            try:
                message_key = f"{self.MESSAGE_PREFIX}{session_id}"
                messages_json = self.redis_client.lrange(message_key, 0, -1)
                
                # Parse JSON messages
                messages = [json.loads(msg) for msg in messages_json]
                return messages
                
            except Exception as e:
                print(f"❌ Error retrieving history from Redis: {e}")
                return self._fallback_storage.get(session_id, [])
        else:
            return self._fallback_storage.get(session_id, [])

    def get_count(self, session_id: str) -> int:
        """Get the number of messages in a session"""
        if not session_id:
            return 0
        
        if self.redis_client:
            try:
                message_key = f"{self.MESSAGE_PREFIX}{session_id}"
                return self.redis_client.llen(message_key)
            except Exception as e:
                print(f"❌ Error getting message count: {e}")
                return len(self._fallback_storage.get(session_id, []))
        else:
            return len(self._fallback_storage.get(session_id, []))

    def clear_history(self, session_id: str):
        """Clear conversation history for a session"""
        if not session_id:
            return
        
        if self.redis_client:
            try:
                message_key = f"{self.MESSAGE_PREFIX}{session_id}"
                self.redis_client.delete(message_key)
                self.redis_client.srem(self.SESSIONS_KEY, session_id)
            except Exception as e:
                print(f"❌ Error clearing history: {e}")
        
        # Also clear from fallback
        if session_id in self._fallback_storage:
            del self._fallback_storage[session_id]

    def get_all_sessions(self) -> List[str]:
        """Get list of all active session IDs from Redis or fallback"""
        if self.redis_client:
            try:
                return list(self.redis_client.smembers(self.SESSIONS_KEY))
            except Exception as e:
                print(f"❌ Error retrieving sessions: {e}")
                return list(self._fallback_storage.keys())
        else:
            return list(self._fallback_storage.keys())

    def get_status(self) -> Dict:
        """Get memory status including Redis connection and session info"""
        if self.redis_client:
            try:
                sessions = self.get_all_sessions()
                session_stats = {}
                
                for session_id in sessions:
                    count = self.get_count(session_id)
                    session_stats[session_id] = count
                
                info = self.redis_client.info()
                
                return {
                    "status": "connected",
                    "redis_version": info.get("redis_version"),
                    "used_memory_mb": round(int(info.get("used_memory", 0)) / (1024 * 1024), 2),
                    "total_sessions": len(sessions),
                    "max_sessions": self.max_sessions,
                    "sessions": session_stats
                }
            except Exception as e:
                print(f"❌ Error getting status: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "using_fallback": True
                }
        else:
            # Return fallback storage status
            return {
                "status": "disconnected",
                "storage_type": "in-memory",
                "total_sessions": len(self._fallback_storage),
                "max_sessions": self.max_sessions,
                "sessions": {sid: len(msgs) for sid, msgs in self._fallback_storage.items()}
            }
    



        
    

