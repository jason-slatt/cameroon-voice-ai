"""Top-up/Deposit flow"""

from typing import Tuple, Optional
from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.core.extraction import DataExtractor
from app.services.backend import account_service, transaction_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS


class TopUpFlow(BaseFlow):
    """Handles top-up/deposit flow"""
    
    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.extractor = DataExtractor()
        self.prompts = FLOW_PROMPTS["topup"]
    
    async def start(self) -> str:
        """Start top-up flow"""
        # Check if user has an account
        if not self.state.account_id:
            account = await account_service.get_account_by_phone(self.state.phone_number)
            if account:
                self.state.account_id = account.id
                self.state.account_balance = account.balance
            else:
                return "You don't have an account yet. Would you like to create one?"
        
        self.state.start_flow(FlowType.TOPUP, FlowStep.ASK_AMOUNT)
        return self.prompts["start"]
    
    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for top-up"""
        step = self.state.flow_step
        
        if step == FlowStep.ASK_AMOUNT:
            return await self._process_amount(user_input)
        
        elif step == FlowStep.CONFIRM:
            return await self._process_confirmation(user_input)
        
        return "", False
    
    async def _process_amount(self, user_input: str) -> Tuple[str, bool]:
        """Process amount input"""
        amount = self.extractor.extract_amount(user_input)
        
        if amount:
            # Validate amount
            if amount < settings.TOPUP_MIN:
                return f"Minimum deposit is {settings.TOPUP_MIN:.0f} {settings.CURRENCY}.", False
            
            if amount > settings.TOPUP_MAX:
                return f"Maximum deposit is {settings.TOPUP_MAX:.0f} {settings.CURRENCY}.", False
            
            self.state.add_data("amount", amount)
            self.state.next_step(FlowStep.CONFIRM)
            return self.prompts["confirm"].format(
                amount=amount,
                currency=settings.CURRENCY,
            ), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I couldn't understand the amount. Let's try again later.", True
        
        return f"Please tell me the amount. For example, '10000' or '10000 {settings.CURRENCY}'.", False
    
    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Process confirmation"""
        confirmed = self.extractor.is_confirmation(user_input)
        
        if confirmed is True:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True
        
        elif confirmed is False:
            self.state.next_step(FlowStep.ASK_AMOUNT)
            self.state.collected_data.pop("amount", None)
            return "Okay, how much would you like to deposit instead?", False
        
        amount = self.state.get_data("amount")
        return f"Please confirm: deposit {amount:.0f} {settings.CURRENCY}? Say 'yes' or 'no'.", False
    
    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete deposit by calling backend"""
        amount = self.state.get_data("amount")
        account_id = self.state.account_id
        
        try:
            # Call backend API
            transaction = await transaction_service.create_deposit(
                account_id=account_id,
                amount=amount,
            )
            
            # Update balance
            balance = await account_service.get_balance(account_id)
            self.state.account_balance = balance.balance
            
            # Reset flow
            self.state.reset_flow()
            
            return (
                self.prompts["success"].format(
                    amount=amount,
                    currency=settings.CURRENCY,
                    new_balance=balance.balance,
                ),
                {
                    "transaction_id": transaction.id,
                    "amount": amount,
                    "new_balance": balance.balance,
                }
            )
            
        except Exception as e:
            self.state.reset_flow()
            return self.prompts["error"], {"error": str(e)}