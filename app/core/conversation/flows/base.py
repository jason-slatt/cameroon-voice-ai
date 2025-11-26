# app/core/conversation/flows/base.py

from typing import Tuple, Optional, Dict, Any
from app.core.conversation.state import ConversationState
from app.config.prompts import FLOW_PROMPTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseFlow:
    """Base class for conversation flows with language support"""
    
    FLOW_NAME: str = ""  # Override in subclass
    
    # Default prompts as fallback
    DEFAULT_PROMPTS = {
        "max_attempts": "I'm having trouble understanding. Let's try again later. Say 'help' if you need assistance.",
        "error": "Sorry, something went wrong. Please try again.",
    }
    
    def __init__(self, state: ConversationState):
        self.state = state
        self.prompts = FLOW_PROMPTS.get(self.FLOW_NAME, {})
    
    def get_prompt(self, key: str, **kwargs) -> str:
        """
        Get language-specific prompt with fallback.
        Supports both formats:
        - Language-specific: "start_en", "start_fr"
        - Simple: "start"
        """
        lang = self.state.lang or "en"
        
        # Try language-specific key first (e.g., "start_en")
        lang_key = f"{key}_{lang}"
        if lang_key in self.prompts:
            prompt = self.prompts[lang_key]
            return prompt.format(**kwargs) if kwargs else prompt
        
        # Fallback to English version
        en_key = f"{key}_en"
        if en_key in self.prompts:
            prompt = self.prompts[en_key]
            return prompt.format(**kwargs) if kwargs else prompt
        
        # Try simple key (backward compatibility)
        if key in self.prompts:
            prompt = self.prompts[key]
            return prompt.format(**kwargs) if kwargs else prompt
        
        # Check default prompts
        if key in self.DEFAULT_PROMPTS:
            prompt = self.DEFAULT_PROMPTS[key]
            return prompt.format(**kwargs) if kwargs else prompt
        
        logger.warning(f"Prompt '{key}' not found for flow '{self.FLOW_NAME}'")
        return f"[Missing prompt: {key}]"
    
    async def start(self) -> str:
        """Start the flow - override in subclass"""
        raise NotImplementedError
    
    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input - override in subclass"""
        raise NotImplementedError
    
    async def complete(self) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Complete the flow - override in subclass"""
        raise NotImplementedError