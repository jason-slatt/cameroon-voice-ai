"""Account creation flow"""

from typing import Tuple, Optional
from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.core.extraction import DataExtractor
from app.services.backend import account_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS


class AccountCreationFlow(BaseFlow):
    """Handles account creation flow"""
    
    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.extractor = DataExtractor()
        self.prompts = FLOW_PROMPTS["account_creation"]
    
    async def start(self) -> str:
        """Start account creation flow"""
        self.state.start_flow(FlowType.ACCOUNT_CREATION, FlowStep.ASK_NAME)
        return self.prompts["start"]
    
    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for account creation"""
        step = self.state.flow_step
        
        if step == FlowStep.ASK_NAME:
            return await self._process_name(user_input)
        
        elif step == FlowStep.CONFIRM:
            return await self._process_confirmation(user_input)
        
        return "", False
    
    async def _process_name(self, user_input: str) -> Tuple[str, bool]:
        """Process name input"""
        name = self.extractor.extract_name(user_input)
        
        if name:
            self.state.add_data("full_name", name)
            self.state.next_step(FlowStep.CONFIRM)
            return self.prompts["confirm_name"].format(name=name), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I'm having trouble understanding. Let's start over when you're ready.", True
        
        return "I didn't catch your name. Please tell me your full name.", False
    
    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Process confirmation"""
        confirmed = self.extractor.is_confirmation(user_input)
        
        if confirmed is True:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True  # Signal completion
        
        elif confirmed is False:
            self.state.next_step(FlowStep.ASK_NAME)
            return "Okay, what is your correct full name?", False
        
        name = self.state.get_data("full_name")
        return f"Please confirm: is '{name}' correct? Say 'yes' or 'no'.", False
    
    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete account creation by calling backend"""
        full_name = self.state.get_data("full_name")
        phone_number = self.state.phone_number
        
        try:
            # Call backend API
            account = await account_service.create_account(
                full_name=full_name,
                phone_number=phone_number,
            )
            
            # Update state with account info
            self.state.account_id = account.id
            self.state.account_balance = account.balance
            
            # Reset flow
            self.state.reset_flow()
            
            return (
                self.prompts["success"].format(
                    name=full_name,
                    account_id=account.account_number,
                ),
                {
                    "account_id": account.id,
                    "account_number": account.account_number,
                    "full_name": full_name,
                }
            )
            
        except Exception as e:
            self.state.reset_flow()
            return self.prompts["error"], {"error": str(e)}