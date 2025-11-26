# app/core/conversation/flows/account.py

from typing import Tuple, Optional
from app.core.conversation.state import ConversationState, FlowType, FlowStep
from app.core.conversation.flows.base import BaseFlow
from app.core.extraction import DataExtractor
from app.config.prompts import FLOW_PROMPTS, GROUPEMENTS
from app.services.backend.accounts import account_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AccountCreationFlow(BaseFlow):
    """Handles account creation flow with all required fields"""
    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.extractor = DataExtractor()
        self.prompts = FLOW_PROMPTS["account_creation"]
        self.groupements = GROUPEMENTS
    
    async def start(self) -> str:
        """Start account creation flow"""
        self.state.start_flow(FlowType.ACCOUNT_CREATION, FlowStep.ASK_NAME)
        return self.prompts["start"]
    
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
            return self.prompts["ask_age"].format(name=name), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I'm having trouble understanding. Let's start over. Say 'create account' when ready.", True
        
        return "I didn't catch your name. Please tell me your full name.", False
    
    async def _process_age(self, user_input: str) -> Tuple[str, bool]:
        """Process age input"""
        age = self.extractor.extract_age(user_input)
        
        if age:
            # Validate reasonable age for account creation
            if age < 18:
                return "You must be at least 18 years old to create an account. How old are you?", False
            if age > 120:
                return "That doesn't seem right. Please tell me your age in years.", False
            
            self.state.add_data("age", str(age))
            self.state.next_step(FlowStep.ASK_SEX)
            return self.prompts["ask_sex"], False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I'm having trouble understanding your age. Let's try again later.", True
        
        return "I didn't get that. Please tell me your age. For example, '25' or '25 years old'.", False
    
    async def _process_sex(self, user_input: str) -> Tuple[str, bool]:
        """Process sex/gender input"""
        sex = self.extractor.extract_sex(user_input)
        
        if sex:
            self.state.add_data("sex", sex)
            self.state.next_step(FlowStep.ASK_GROUPEMENT)
            return self.prompts["ask_groupement"], False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I'm having trouble understanding. Let's try again later.", True
        
        return "Please tell me if you are male or female. Say 'male' or 'female'.", False
    
    async def _process_groupement(self, user_input: str) -> Tuple[str, bool]:
        """Process groupement selection"""
        groupement_id = self.extractor.extract_groupement(user_input, self.groupements)
        
        if groupement_id:
            self.state.add_data("groupement_id", groupement_id)
            
            # Find groupement name
            groupement = next((g for g in self.groupements if g['id'] == groupement_id), None)
            if groupement:
                self.state.add_data("groupement_name", groupement['name'])
            
            self.state.next_step(FlowStep.CONFIRM)
            return self._get_confirmation_message(), False
        
        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I'm having trouble understanding. Let's try again later.", True
        
        return "Please select a groupement by number (1, 2, or 3) or by name.", False
    
    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Process confirmation"""
        confirmed = self.extractor.is_confirmation(user_input)
        
        if confirmed is True:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True  # Signal completion
        
        elif confirmed is False:
            # Ask what to change
            return "What would you like to change? Say 'name', 'age', 'sex', or 'groupement'.", False
        
        # Check if user wants to change something specific
        text_lower = user_input.lower()
        if 'name' in text_lower:
            self.state.next_step(FlowStep.ASK_NAME)
            return "Okay, what is your correct full name?", False
        elif 'age' in text_lower:
            self.state.next_step(FlowStep.ASK_AGE)
            return "Okay, how old are you?", False
        elif 'sex' in text_lower or 'gender' in text_lower:
            self.state.next_step(FlowStep.ASK_SEX)
            return "Okay, are you male or female?", False
        elif 'groupement' in text_lower or 'group' in text_lower:
            self.state.next_step(FlowStep.ASK_GROUPEMENT)
            return self.prompts["ask_groupement"], False
        
        return "Please confirm: is all the information correct? Say 'yes' or 'no'.", False
    
    def _get_confirmation_message(self) -> str:
        """Generate confirmation message"""
        name = self.state.get_data("full_name")
        age = self.state.get_data("age")
        sex = "Male" if self.state.get_data("sex") == "M" else "Female"
        groupement_name = self.state.get_data("groupement_name", "Unknown")
        
        return self.prompts["confirm"].format(
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
            # Call backend API
            account = await account_service.create_account(
                full_name=full_name,
                phone_number=phone_number,
                age=age,
                sex=sex,
                groupement_id=groupement_id,
            )
            
            # Update state with account info
            self.state.account_id = account.id
            self.state.account_balance = account.balance
            
            # Reset flow
            self.state.reset_flow()
            
            return (
                self.prompts["success"].format(name=full_name),
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
            self.state.reset_flow()
            return self.prompts["error"], {"error": str(e)}