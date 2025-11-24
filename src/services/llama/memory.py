# src/services/llama/memory.py
"""
Conversation memory - track user language & history
"""
from typing import Optional
import json

from src.core.dependencies import get_redis
from src.core.constants import CameroonLanguage
from src.core.logging import logger


class ConversationMemory:
    """Store conversation context in Redis"""
    
    def __init__(self):
        self.ttl = 86400  # 24 hours
    
    async def get_language(self, conversation_id: str) -> Optional[CameroonLanguage]:
        """Get detected language for this conversation"""
        redis = await get_redis()
        
        key = f"conv:{conversation_id}:language"
        lang_str = await redis.get(key)
        
        if lang_str:
            try:
                return CameroonLanguage(lang_str)
            except:
                return None
        
        return None
    
    async def set_language(
        self,
        conversation_id: str,
        language: CameroonLanguage
    ) -> None:
        """Save detected language"""
        redis = await get_redis()
        
        key = f"conv:{conversation_id}:language"
        await redis.setex(key, self.ttl, language.value)
        
        logger.info(f"Saved language {language.value} for {conversation_id}")
    
    async def get_history(self, conversation_id: str) -> list[dict]:
        """Get conversation history"""
        redis = await get_redis()
        
        key = f"conv:{conversation_id}:history"
        history_json = await redis.get(key)
        
        if history_json:
            try:
                return json.loads(history_json)
            except:
                return []
        
        return []
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        """Add message to history"""
        redis = await get_redis()
        
        history = await self.get_history(conversation_id)
        
        history.append({
            "role": role,
            "content": content
        })
        
        # Keep only last 10 messages
        history = history[-10:]
        
        key = f"conv:{conversation_id}:history"
        await redis.setex(key, self.ttl, json.dumps(history))