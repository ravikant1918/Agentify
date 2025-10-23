"""
Redis-based session management for chat threads
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dataclasses import dataclass, asdict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str
    message_id: Optional[str] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatMessage':
        return cls(**data)

@dataclass
class ChatThread:
    thread_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[ChatMessage]
    mcp_url: Optional[str] = None
    system_prompt: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.messages, list) and len(self.messages) > 0:
            if isinstance(self.messages[0], dict):
                self.messages = [ChatMessage.from_dict(msg) for msg in self.messages]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['messages'] = [msg.to_dict() for msg in self.messages]
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatThread':
        messages_data = data.get('messages', [])
        messages = [ChatMessage.from_dict(msg) if isinstance(msg, dict) else msg for msg in messages_data]
        data['messages'] = messages
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ChatThread':
        return cls.from_dict(json.loads(json_str))

class RedisSessionManager:
    def __init__(self, redis_url: Optional[str] = None):
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                print(f"[INFO] Connected to Redis at {redis_url}")
            except Exception as e:
                print(f"[WARN] Redis connection failed: {e}. Using in-memory storage.")
                self.redis_client = None
                self._memory_store = {}
        else:
            print("[WARN] Redis not available. Using in-memory storage.")
            self.redis_client = None
            self._memory_store = {}
    
    def _get_thread_key(self, thread_id: str) -> str:
        return f"chat_thread:{thread_id}"
    
    def _get_user_threads_key(self, user_id: str = "default") -> str:
        return f"user_threads:{user_id}"
    
    def create_thread(self, title: Optional[str] = None, user_id: str = "default", 
                     mcp_url: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
        """Create a new chat thread"""
        thread_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if title is None:
            title = f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
        
        thread = ChatThread(
            thread_id=thread_id,
            title=title,
            created_at=now,
            updated_at=now,
            messages=[],
            mcp_url=mcp_url,
            system_prompt=system_prompt
        )
        
        self._save_thread(thread)
        self._add_thread_to_user(user_id, thread_id, title, now)
        
        return thread_id
    
    def get_thread(self, thread_id: str) -> Optional[ChatThread]:
        """Get a chat thread by ID"""
        if self.redis_client:
            try:
                thread_data = self.redis_client.get(self._get_thread_key(thread_id))
                if thread_data:
                    return ChatThread.from_json(thread_data)
            except Exception as e:
                print(f"[ERROR] Failed to get thread from Redis: {e}")
        else:
            # Fallback to memory storage
            return self._memory_store.get(thread_id)
        
        return None
    
    def _save_thread(self, thread: ChatThread):
        """Save thread to storage"""
        thread.updated_at = datetime.now().isoformat()
        
        if self.redis_client:
            try:
                # Save thread data
                self.redis_client.setex(
                    self._get_thread_key(thread.thread_id),
                    timedelta(days=30),  # Expire after 30 days
                    thread.to_json()
                )
            except Exception as e:
                print(f"[ERROR] Failed to save thread to Redis: {e}")
                # Fallback to memory
                self._memory_store[thread.thread_id] = thread
        else:
            # Memory storage
            self._memory_store[thread.thread_id] = thread
    
    def _add_thread_to_user(self, user_id: str, thread_id: str, title: str, created_at: str):
        """Add thread to user's thread list"""
        if self.redis_client:
            try:
                thread_info = {
                    "thread_id": thread_id,
                    "title": title,
                    "created_at": created_at,
                    "updated_at": created_at
                }
                self.redis_client.lpush(self._get_user_threads_key(user_id), json.dumps(thread_info))
                # Keep only last 100 threads per user
                self.redis_client.ltrim(self._get_user_threads_key(user_id), 0, 99)
            except Exception as e:
                print(f"[ERROR] Failed to add thread to user list: {e}")
    
    def get_user_threads(self, user_id: str = "default") -> List[Dict]:
        """Get all threads for a user"""
        if self.redis_client:
            try:
                threads_data = self.redis_client.lrange(self._get_user_threads_key(user_id), 0, -1)
                return [json.loads(thread_data) for thread_data in threads_data]
            except Exception as e:
                print(f"[ERROR] Failed to get user threads: {e}")
        
        # Fallback: return all threads from memory
        return [
            {
                "thread_id": thread_id,
                "title": thread.title,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at
            }
            for thread_id, thread in self._memory_store.items()
        ]
    
    def add_message(self, thread_id: str, role: str, content: str) -> Optional[str]:
        """Add a message to a thread"""
        thread = self.get_thread(thread_id)
        if not thread:
            return None
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        
        thread.messages.append(message)
        self._save_thread(thread)
        
        return message.message_id
    
    def get_messages(self, thread_id: str) -> List[ChatMessage]:
        """Get all messages from a thread"""
        thread = self.get_thread(thread_id)
        return thread.messages if thread else []
    
    def update_thread_title(self, thread_id: str, title: str, user_id: str = "default"):
        """Update thread title"""
        thread = self.get_thread(thread_id)
        if thread:
            thread.title = title
            self._save_thread(thread)
            
            # Update in user's thread list
            if self.redis_client:
                try:
                    threads_data = self.redis_client.lrange(self._get_user_threads_key(user_id), 0, -1)
                    updated_threads = []
                    for thread_data in threads_data:
                        thread_info = json.loads(thread_data)
                        if thread_info["thread_id"] == thread_id:
                            thread_info["title"] = title
                            thread_info["updated_at"] = datetime.now().isoformat()
                        updated_threads.append(json.dumps(thread_info))
                    
                    # Replace the entire list
                    self.redis_client.delete(self._get_user_threads_key(user_id))
                    if updated_threads:
                        self.redis_client.lpush(self._get_user_threads_key(user_id), *updated_threads)
                except Exception as e:
                    print(f"[ERROR] Failed to update thread title in user list: {e}")
    
    def delete_thread(self, thread_id: str, user_id: str = "default"):
        """Delete a thread"""
        if self.redis_client:
            try:
                # Delete thread data
                self.redis_client.delete(self._get_thread_key(thread_id))
                
                # Remove from user's thread list
                threads_data = self.redis_client.lrange(self._get_user_threads_key(user_id), 0, -1)
                updated_threads = []
                for thread_data in threads_data:
                    thread_info = json.loads(thread_data)
                    if thread_info["thread_id"] != thread_id:
                        updated_threads.append(thread_data)
                
                # Replace the entire list
                self.redis_client.delete(self._get_user_threads_key(user_id))
                if updated_threads:
                    self.redis_client.lpush(self._get_user_threads_key(user_id), *updated_threads)
            except Exception as e:
                print(f"[ERROR] Failed to delete thread: {e}")
        else:
            # Memory storage
            if thread_id in self._memory_store:
                del self._memory_store[thread_id]
    
    def update_thread_config(self, thread_id: str, mcp_url: Optional[str] = None, system_prompt: Optional[str] = None):
        """Update thread configuration"""
        thread = self.get_thread(thread_id)
        if thread:
            if mcp_url is not None:
                thread.mcp_url = mcp_url
            if system_prompt is not None:
                thread.system_prompt = system_prompt
            self._save_thread(thread)
    
    def clear_thread_messages(self, thread_id: str):
        """Clear all messages from a thread"""
        thread = self.get_thread(thread_id)
        if thread:
            thread.messages = []
            self._save_thread(thread)

# Global session manager instance
session_manager = RedisSessionManager()
