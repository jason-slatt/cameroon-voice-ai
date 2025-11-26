# app/core/conversation/flows/account.py

from typing import Tuple, Optional
from app.core.conversation.state import ConversationState, FlowType, FlowStep
from app.core.conversation.flows.base import BaseFlow
from app.core.extraction import DataExtractor
from app.config.prompts import GROUPEMENTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AccountCreationFlow(BaseFlow):
    """Handles account creation flow with all required fields"""
    
    FLOW_NAME = "account_creation"  # This tells BaseFlow which prompts to load
    
    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.extractor = DataExtractor()
        self.groupements = GROUPEMENTS
        # Don't override self.prompts here - BaseFlow handles it
    
    async def start(self) -> str:
        """Start account creation flow"""
        self.state.start_flow(FlowType.ACCOUNT_CREATION, FlowStep.ASK_NAME)
        return self.get_prompt("start")  # Use get_prompt() instead of self.prompts["start"]
    
    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for account creation"""
        step = self.state.flow_step
        
        if step == FlowStep.ASK_NAME:
            return await self._process_name(user_input)
        elif step == FlowStep.ASK_AGE:
            return await self._process_age(user_input)
        elif step == FlowStep.ASK_SEX:
            return await self._process_sex(user_input)
        elif step == FlowStep.ASK_GROUPEMENT:
            return await self._process_groupement(user_input)
        elif step == FlowStep.CONFIRM:
            return await self._process_confirmation(user_input)
        
        return "", False
    
    async def _process_name(self, user_input: str) -> Tuple[str, bool]:
        """Process name input"""
        name = self.extractor.extract_name(user_input)
        
        if name:
            self.state.add_data("full_name", name)
            self.state.next_step(FlowStep.ASK_AGE)
            return self.get_prompt("ask_age").format(name=name), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self.get_prompt("max_attempts"), True
        
        return self.get_prompt("invalid_name"), False
    
    async def _process_age(self, user_input: str) -> Tuple[str, bool]:
        """Process age input"""
        age = self.extractor.extract_age(user_input)
        
        if age:
            if age < 18:
                return self.get_prompt("underage"), False
            if age > 120:
                return self.get_prompt("invalid_age"), False
            
            self.state.add_data("age", str(age))
            self.state.next_step(FlowStep.ASK_SEX)
            return self.get_prompt("ask_sex"), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self.get_prompt("max_attempts"), True
        
        return self.get_prompt("invalid_age"), False
    
    async def _process_sex(self, user_input: str) -> Tuple[str, bool]:
        """Process sex/gender input"""
        sex = self.extractor.extract_sex(user_input)
        
        if sex:
            self.state.add_data("sex", sex)
            self.state.next_step(FlowStep.ASK_GROUPEMENT)
            return self.get_prompt("ask_groupement"), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self.get_prompt("max_attempts"), True
        
        return self.get_prompt("invalid_sex"), False
    
    async def _process_groupement(self, user_input: str) -> Tuple[str, bool]:
        """Process groupement selection"""
        groupement_id = self.extractor.extract_groupement(user_input, self.groupements)
        
        if groupement_id:
            self.state.add_data("groupement_id", groupement_id)
            
            groupement = next((g for g in self.groupements if g['id'] == groupement_id), None)
            if groupement:
                self.state.add_data("groupement_name", groupement['name'])
            
            self.state.next_step(FlowStep.CONFIRM)
            return self._get_confirmation_message(), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self.get_prompt("max_attempts"), True
        
        return self.get_prompt("invalid_groupement"), False
    
    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Process confirmation"""
        confirmed = self.extractor.is_confirmation(user_input)
        
        if confirmed is True:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True
        
        elif confirmed is False:
            return self.get_prompt("what_to_change"), False
        
        text_lower = user_input.lower()
        if 'name' in text_lower:
            self.state.next_step(FlowStep.ASK_NAME)
            return self.get_prompt("change_name"), False
        elif 'age' in text_lower:
            self.state.next_step(FlowStep.ASK_AGE)
            return self.get_prompt("change_age"), False
        elif 'sex' in text_lower or 'gender' in text_lower:
            self.state.next_step(FlowStep.ASK_SEX)
            return self.get_prompt("change_sex"), False
        elif 'groupement' in text_lower or 'group' in text_lower:
            self.state.next_step(FlowStep.ASK_GROUPEMENT)
            return self.get_prompt("ask_groupement"), False
        
        return self.get_prompt("confirm_prompt"), False
    
    def _get_confirmation_message(self) -> str:
        """Generate confirmation message"""
        name = self.state.get_data("full_name")
        age = self.state.get_data("age")
        sex = "Male" if self.state.get_data("sex") == "M" else "Female"
        groupement_name = self.state.get_data("groupement_name", "Unknown")
        
        return self.get_prompt("confirm").format(
            name=name,
            age=age,
            sex=sex,
            groupement_name=groupement_name,
        )
    
    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete account creation by calling backend"""
        full_name = self.state.get_data("full_name")
        age = self.state.get_data("age")
        sex = self.state.get_data("sex")
        groupement_id = self.state.get_data("groupement_id")
        phone_number = self.state.phone_number
        
        try:
            from app.services.backend.accounts import account_service
            
            account = await account_service.create_account(
                full_name=full_name,
                phone_number=phone_number,
                age=age,
                sex=sex,
                groupement_id=groupement_id,
            )
            
            self.state.account_id = account.id
            self.state.account_balance = account.balance
            self.state.reset_flow()
            
            return (
                self.get_prompt("success").format(name=full_name),
                {
                    "account_id": account.id,
                    "account_number": account.account_number,
                    "full_name": full_name,
                    "age": age,
                    "sex": sex,
                    "groupement_id": groupement_id,
                }
            )
            
        except Exception as e:
            logger.error(f"Account creation failed: {e}")
            self.state.reset_flow()
            return self.get_prompt("error"), {"error": str(e)}