"""Conversation flow manager"""

from typing import Optional, Tuple, Dict, Any
from .state import ConversationState, FlowType, FlowStep
from .flows.account import AccountCreationFlow
from .flows.withdrawal import WithdrawalFlow
from .flows.topup import TopUpFlow
from app.core.intent import IntentClassifier, Intent
from app.core.extraction import DataExtractor
from app.services.backend import account_service, transaction_service
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
                account = await account_service.get_my_account(phone_number)
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
        """Process a user message and return response."""
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

        # 1) Account creation: enforce global "no creation if account exists"
        if intent == Intent.ACCOUNT_CREATION:
            # Ensure we know if this phone already has an account
            exists = state.account_exists

            if not state.phone_checked:
                try:
                    phone_check = await account_service.check_phone_number(state.phone_number)
                    exists = phone_check.exists
                    state.mark_phone_checked(exists)

                    if exists:
                        account = await account_service.get_my_account(state.phone_number)
                        if account:
                            state.account_id = account.id
                            state.account_balance = account.balance
                except Exception as e:
                    logger.warning(f"Phone check failed, defaulting to no account: {e}")
                    exists = False
                    state.mark_phone_checked(False)

            # If account already exists, NEVER start creation flow
            if exists:
                return (
                    f"You already have an account with {settings.COMPANY_NAME}. "
                    "I can help you view your account, check your balance, make a withdrawal, "
                    "or top up your balance. What would you like to do?"
                )

            # Only if no account: start account creation flow
            flow = AccountCreationFlow(state)
            return await flow.start()

        # 2) View account (we added this intent earlier)
        elif intent == Intent.VIEW_ACCOUNT:
            return await self._handle_view_account(state)
        
        # 3) Balance inquiry
        elif intent == Intent.TRANSACTION_HISTORY:
            return await self._handle_transaction_history(state)

        # 3) Withdrawals: require an account
        elif intent == Intent.WITHDRAWAL:
            if not state.account_exists:
                return "You need an account to make a withdrawal. Would you like to view your account or create one?"
            flow = WithdrawalFlow(state)
            return await flow.start()

        # 4) Top-ups: require an account
        elif intent == Intent.TOPUP:
            if not state.account_exists:
                return "You need an account to make a deposit. Would you like to view your account or create one?"
            flow = TopUpFlow(state)
            return await flow.start()
        
    async def _handle_view_account(self, state: ConversationState) -> str:
        """Handle view account request"""
        try:
            account = await account_service.get_my_account(state.phone_number)
            
            if not account:
                return (
                    "I couldn't find an account with this phone number. "
                    "Would you like to create an account?"
                )
            
            # Update state with account info
            state.account_id = account.id
            state.account_balance = account.balance
            
            # Format account details
            sex_display = "Male" if account.sex == "M" else "Female" if account.sex == "F" else "Not specified"
            
            response_lines = [
                f"Here are your account details:",
                f"• Name: {account.full_name}",
                f"• Account Number: {account.account_number}",
                f"• Phone: {account.phone_number}",
            ]
            
            if account.age:
                response_lines.append(f"• Age: {account.age}")
            
            if account.sex:
                response_lines.append(f"• Sex: {sex_display}")
            
            if account.groupement_name:
                response_lines.append(f"• Groupement: {account.groupement_name}")
            
            response_lines.append(f"• Balance: {account.balance:.0f} {settings.CURRENCY}")
            response_lines.append(f"• Status: {account.status}")
            
            response_lines.append("\nIs there anything else I can help you with?")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            logger.error(f"Error viewing account: {e}")
            return "Sorry, I couldn't retrieve your account information. Please try again later."
    
    async def _handle_balance_inquiry(self, state: ConversationState) -> str:
        """Handle balance inquiry"""
        if not state.account_id:
            account = await account_service.get_my_account(state.phone_number)
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

        phone = state.phone_number

        try:
            # OPTIONAL: Ensure user has an account first
            phone_check = await account_service.check_phone_number(phone)
            state.mark_phone_checked(phone_check.exists)

            if not state.account_exists:
                return (
                    "I couldn't find an account with this phone number. "
                    "Would you like to create an account?"
                )

            # Call GET /dashboard/transactions
            transactions = await transaction_service.get_dashboard_transactions(
                phone_number=phone,
                limit=5,
            )

            if not transactions:
                return "You don't have any transactions yet."

            lines = ["Here are your recent transactions:"]

            for t in transactions[:5]:
                type_label = (
                    "Deposit" if t.type == TransactionType.DEPOSIT else
                    "Withdrawal" if t.type == TransactionType.WITHDRAWAL else
                    t.type.value.title()
                )
                status_label = t.status.value.title()
                amount_str = f"{t.amount:.0f} {settings.CURRENCY}"

                if t.created_at:
                    date_str = t.created_at.strftime("%Y-%m-%d")
                    lines.append(f"• {date_str}: {type_label} of {amount_str} ({status_label})")
                else:
                    lines.append(f"• {type_label} of {amount_str} ({status_label})")

            lines.append("\nDo you want more details on any of these, or something else?")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return "Sorry, I couldn't retrieve your transactions right now. Please try again later."