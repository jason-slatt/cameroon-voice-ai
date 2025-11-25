"""Base flow class"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
from ..state import ConversationState, FlowStep


class BaseFlow(ABC):
    """Base class for conversation flows"""
    
    def __init__(self, state: ConversationState):
        self.state = state
    
    @abstractmethod
    async def start(self) -> str:
        """Start the flow, return initial message"""
        pass
    
    @abstractmethod
    async def process(self, user_input: str) -> Tuple[str, bool]:
        """
        Process user input.
        Returns: (response_message, is_complete)
        """
        pass
    
    @abstractmethod
    async def complete(self) -> Tuple[str, Optional[dict]]:
        """
        Complete the flow.
        Returns: (success_message, result_data)
        """
        pass
    
    def cancel(self) -> str:
        """Cancel the flow"""
        self.state.reset_flow()
        return "Okay, I've cancelled that. Is there something else I can help you with?"