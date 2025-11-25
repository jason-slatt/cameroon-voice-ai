"""Conversation state storage"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
import json
from datetime import datetime, timedelta
from functools import lru_cache

from app.core.conversation.state import ConversationState
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConversationStore(ABC):
    """Abstract base class for conversation storage"""
    
    @abstractmethod
    async def get(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state by ID"""
        pass
    
    @abstractmethod
    async def save(self, state: ConversationState) -> None:
        """Save conversation state"""
        pass
    
    @abstractmethod
    async def delete(self, conversation_id: str) -> None:
        """Delete conversation state"""
        pass


class InMemoryConversationStore(ConversationStore):
    """In-memory conversation storage (for development/testing)"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self._store: Dict[str, dict] = {}
        self._ttl = ttl_seconds
    
    async def get(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state"""
        data = self._store.get(conversation_id)
        
        if data is None:
            return None
        
        # Check TTL
        try:
            expires_at = datetime.fromisoformat(data.get("_expires_at", ""))
            if datetime.utcnow() > expires_at:
                del self._store[conversation_id]
                return None
        except (ValueError, TypeError):
            pass
        
        return ConversationState.from_dict(data)
    
    async def save(self, state: ConversationState) -> None:
        """Save conversation state"""
        data = state.to_dict()
        data["_expires_at"] = (datetime.utcnow() + timedelta(seconds=self._ttl)).isoformat()
        self._store[state.conversation_id] = data
    
    async def delete(self, conversation_id: str) -> None:
        """Delete conversation state"""
        self._store.pop(conversation_id, None)


class RedisConversationStore(ConversationStore):
    """Redis-based conversation storage (for production)"""
    
    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._ttl = ttl_seconds
            self._prefix = "bafoka:conversation:"
        except ImportError:
            logger.warning("redis package not installed, falling back to in-memory storage")
            raise
    
    def _key(self, conversation_id: str) -> str:
        """Get Redis key for conversation"""
        return f"{self._prefix}{conversation_id}"
    
    async def get(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state from Redis"""
        try:
            data = await self._redis.get(self._key(conversation_id))
            
            if data is None:
                return None
            
            return ConversationState.from_dict(json.loads(data))
        except Exception as e:
            logger.error(f"Error getting conversation from Redis: {e}")
            return None
    
    async def save(self, state: ConversationState) -> None:
        """Save conversation state to Redis"""
        try:
            data = json.dumps(state.to_dict())
            await self._redis.setex(
                self._key(state.conversation_id),
                self._ttl,
                data,
            )
        except Exception as e:
            logger.error(f"Error saving conversation to Redis: {e}")
    
    async def delete(self, conversation_id: str) -> None:
        """Delete conversation state from Redis"""
        try:
            await self._redis.delete(self._key(conversation_id))
        except Exception as e:
            logger.error(f"Error deleting conversation from Redis: {e}")


@lru_cache()
def get_conversation_store() -> ConversationStore:
    """Get conversation store based on configuration"""
    if settings.REDIS_URL:
        try:
            logger.info("Using Redis conversation store")
            return RedisConversationStore(
                redis_url=settings.REDIS_URL,
                ttl_seconds=settings.CONVERSATION_TTL,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis store: {e}, using in-memory")
    
    logger.info("Using in-memory conversation store")
    return InMemoryConversationStore(
        ttl_seconds=settings.CONVERSATION_TTL,
    )