"""Conversation flow manager"""

from typing import Optional, Tuple, Dict, Any
from .state import ConversationState, FlowType, FlowStep
from .flows.account import AccountCreationFlow
from .flows.withdrawal import WithdrawalFlow
from .flows.topup import TopUpFlow
from app.core.intent import IntentClassifier, Intent
from app.core.extraction import DataExtractor
from app.services.backend import account_service
from app.storage import ConversationStore
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """Manages conversation flows and state"""
    
    def __init__(self, store: ConversationStore):
        self.store = store
        self.intent_classifier = IntentClassifier()
        self.extractor = DataExtractor()
    
    async def get_or_create_state(
        self,
        conversation_id: str,
        user_id: str,
        phone_number: str,
    ) -> ConversationState:
        """Get existing state or create new one"""
        state = await self.store.get(conversation_id)
        
        if state is None:
            state = ConversationState(
                conversation_id=conversation_id,
                user_id=user_id,
                phone_number=phone_number,
            )
            
            # Try to load account info
            try:
                account = await account_service.get_account_by_phone(phone_number)
                if account:
                    state.account_id = account.id
                    state.account_balance = account.balance
            except Exception as e:
                logger.warning(f"Failed to load account info: {e}")
            
            await self.store.save(state)
        
        return state
    
    async def process_message(
        self,
        conversation_id: str,
        user_id: str,
        phone_number: str,
        text: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process a user message and return response.
        
        Returns:
            Tuple of (response_text, metadata)
        """
        # Get or create state
        state = await self.get_or_create_state(conversation_id, user_id, phone_number)
        
        metadata = {
            "intent": None,
            "flow": {
                "flow_type": state.flow_type.value,
                "step": state.flow_step.value if state.flow_step else None,
                "is_complete": False,
            },
            "transaction_data": None,
        }
        
        # Check for cancel
        if "cancel" in text.lower() and state.is_in_flow():
            flow = self._get_flow(state)
            response = flow.cancel()
            await self.store.save(state)
            return response, metadata
        
        # If in a flow, process with that flow
        if state.is_in_flow():
            response, transaction_data = await self._process_flow(state, text)
            metadata["flow"]["flow_type"] = state.flow_type.value
            metadata["flow"]["step"] = state.flow_step.value if state.flow_step else None
            metadata["flow"]["is_complete"] = not state.is_in_flow()
            metadata["transaction_data"] = transaction_data
            await self.store.save(state)
            return response, metadata
        
        # Classify intent
        intent, confidence = self.intent_classifier.classify(text)
        metadata["intent"] = {"intent": intent.value, "confidence": confidence}
        
        logger.info(f"Classified intent: {intent.value} ({confidence:.2f})")
        
        # Handle different intents
        response = await self._handle_intent(state, intent, text)
        
        metadata["flow"]["flow_type"] = state.flow_type.value
        metadata["flow"]["step"] = state.flow_step.value if state.flow_step else None
        
        await self.store.save(state)
        return response, metadata
    
    async def _process_flow(
        self,
        state: ConversationState,
        text: str,
    ) -> Tuple[str, Optional[Dict]]:
        """Process input for current flow"""
        flow = self._get_flow(state)
        
        if flow is None:
            state.reset_flow()
            return "Something went wrong. How can I help you?", None
        
        response, is_complete = await flow.process(text)
        
        if is_complete:
            # Complete the flow
            success_message, result_data = await flow.complete()
            return success_message, result_data
        
        return response, None
    
    def _get_flow(self, state: ConversationState):
        """Get the flow handler for current flow type"""
        flow_map = {
            FlowType.ACCOUNT_CREATION: AccountCreationFlow,
            FlowType.WITHDRAWAL: WithdrawalFlow,
            FlowType.TOPUP: TopUpFlow,
        }
        
        flow_class = flow_map.get(state.flow_type)
        if flow_class:
            return flow_class(state)
        return None
    
    async def _handle_intent(
        self,
        state: ConversationState,
        intent: Intent,
        text: str,
    ) -> str:
        """Handle classified intent"""
        
        if intent == Intent.ACCOUNT_CREATION:
            flow = AccountCreationFlow(state)
            return await flow.start()
        
        elif intent == Intent.WITHDRAWAL:
            flow = WithdrawalFlow(state)
            return await flow.start()
        
        elif intent == Intent.TOPUP:
            flow = TopUpFlow(state)
            return await flow.start()
        
        elif intent == Intent.BALANCE_INQUIRY:
            return await self._handle_balance_inquiry(state)
        
        elif intent == Intent.TRANSACTION_HISTORY:
            return await self._handle_transaction_history(state)
        
        elif intent == Intent.GREETING:
            return f"Hello! Welcome to {settings.COMPANY_NAME}. How can I help you today?"
        
        elif intent == Intent.GOODBYE:
            return f"Goodbye! Thank you for using {settings.COMPANY_NAME}."
        
        elif intent == Intent.OFF_TOPIC:
            return (
                f"I can help you with {settings.COMPANY_NAME} services: "
                "account creation, withdrawals, top-ups, or balance inquiries. "
                "What would you like to do?"
            )
        
        # Default / general support
        return f"Welcome to {settings.COMPANY_NAME}! I can help you create an account, make withdrawals, or top up your balance. What would you like to do?"
    
    async def _handle_balance_inquiry(self, state: ConversationState) -> str:
        """Handle balance inquiry"""
        if not state.account_id:
            account = await account_service.get_account_by_phone(state.phone_number)
            if account:
                state.account_id = account.id
                state.account_balance = account.balance
            else:
                return "You don't have an account yet. Would you like to create one?"
        
        try:
            balance = await account_service.get_balance(state.account_id)
            state.account_balance = balance.balance
            return f"Your current balance is {balance.balance:.0f} {settings.CURRENCY}. Is there anything else?"
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return "Sorry, I couldn't retrieve your balance. Please try again later."
    
    async def _handle_transaction_history(self, state: ConversationState) -> str:
        """Handle transaction history inquiry"""
        from app.services.backend import transaction_service
        
        if not state.account_id:
            account = await account_service.get_account_by_phone(state.phone_number)
            if account:
                state.account_id = account.id
            else:
                return "You don't have an account yet. Would you like to create one?"
        
        try:
            transactions = await transaction_service.get_recent_transactions(
                state.account_id,
                limit=5,
            )
            
            if not transactions:
                return "You don't have any transactions yet."
            
            # Format transactions
            lines = ["Your recent transactions:"]
            for t in transactions:
                lines.append(f"• {t.type.value}: {t.amount:.0f} {settings.CURRENCY} ({t.status.value})")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            return "Sorry, I couldn't retrieve your transactions. Please try again later."