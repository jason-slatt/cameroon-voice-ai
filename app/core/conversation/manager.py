# app/core/conversation/manager.py

from typing import Optional, Tuple, Dict, Any

from app.core.conversation.flows.transfer import TransferFlow
from app.core.conversation.flows.dashboard import DashboardFlow
from app.core.conversation.flows.password_reset import PasswordResetFlow
from app.core.conversation.flows.password_change import PasswordChangeFlow
from app.core.conversation.flows.whatsapp_link import WhatsAppLinkFlow
from .state import ConversationState, FlowType, FlowStep
from .flows.account import AccountCreationFlow
from .flows.withdrawal import WithdrawalFlow
from .flows.topup import TopUpFlow
from app.core.intent import IntentClassifier, Intent
from app.core.extraction import DataExtractor
from app.config.prompts import FLOW_PROMPTS
from app.config import settings
from app.services.backend.accounts import account_service
from app.services.backend.transactions import (
    transaction_service,
    TransactionType,
)
from app.storage import ConversationStore
from app.utils.logging import get_logger
from app.utils.lang import detect_language

logger = get_logger(__name__)


class ConversationManager:
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
        state = await self.store.get(conversation_id)
        
        if state is None:
            state = ConversationState(
                conversation_id=conversation_id,
                user_id=user_id,
                phone_number=phone_number,
            )

        return state

    async def process_message(
        self,
        conversation_id: str,
        user_id: str,
        phone_number: str,
        text: str,
    ) -> Tuple[str, Dict[str, Any]]:
        state = await self.get_or_create_state(conversation_id, user_id, phone_number)

        # Detect language once per conversation
        if not state.lang:
            state.lang = detect_language(text)

        metadata: Dict[str, Any] = {
            "intent": None,
            "flow": {
                "flow_type": state.flow_type.value,
                "step": state.flow_step.value if state.flow_step else None,
                "is_complete": False,
            },
            "transaction_data": None,
        }

        # Flow continuation
        if state.is_in_flow():
            response, tx_data = await self._process_flow(state, text)
            metadata["flow"]["flow_type"] = state.flow_type.value
            metadata["flow"]["step"] = state.flow_step.value if state.flow_step else None
            metadata["flow"]["is_complete"] = not state.is_in_flow()
            metadata["transaction_data"] = tx_data
            await self.store.save(state)
            return response, metadata

        # Classify intent
        intent, confidence = self.intent_classifier.classify(text)
        metadata["intent"] = {"intent": intent.value, "confidence": confidence}
        logger.info(f"Classified intent: {intent.value} ({confidence:.2f})")

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
            FlowType.TRANSFER: TransferFlow,
            FlowType.DASHBOARD: DashboardFlow,
            FlowType.PASSWORD_RESET: PasswordResetFlow,
            FlowType.PASSWORD_CHANGE: PasswordChangeFlow,
            FlowType.WHATSAPP_LINK: WhatsAppLinkFlow,
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

        # 1) Account creation
        if intent == Intent.ACCOUNT_CREATION:
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

            if exists:
                return (
                    f"You already have an account with {settings.COMPANY_NAME}. "
                    "I can help you view your account, check your balance, make a withdrawal, "
                    "or top up your balance. What would you like to do?"
                )

            flow = AccountCreationFlow(state)
            return await flow.start()

        # 2) View account
        elif intent == Intent.VIEW_ACCOUNT:
            return await self._handle_view_account(state)
        
        # 3) Balance inquiry
        elif intent == Intent.BALANCE_INQUIRY:
            return await self._handle_balance_inquiry(state)
        
        # 4) Transaction history
        elif intent == Intent.TRANSACTION_HISTORY:
            return await self._handle_transaction_history(state)

        # 5) Withdrawals
        elif intent == Intent.WITHDRAWAL:
            if not state.account_exists:
                return "You need an account to make a withdrawal. Would you like to view your account or create one?"
            flow = WithdrawalFlow(state)
            return await flow.start()

        # 6) Top-ups
        elif intent == Intent.TOPUP:
            if not state.account_exists:
                return "You need an account to make a deposit. Would you like to view your account or create one?"
            flow = TopUpFlow(state)
            return await flow.start()
        
        # 7) Transfer
        elif intent == Intent.TRANSFER:
            flow = TransferFlow(state)
            return await flow.start()
        
        # 8) Dashboard
        elif intent == Intent.DASHBOARD:
            flow = DashboardFlow(state)
            return await flow.start()

        # 9) Password Reset
        elif intent == Intent.PASSWORD_RESET:
            flow = PasswordResetFlow(state)
            return await flow.start()

        # 10) Password Change
        elif intent == Intent.PASSWORD_CHANGE:
            flow = PasswordChangeFlow(state)
            return await flow.start()

        # 11) WhatsApp Link
        elif intent == Intent.WHATSAPP_LINK:
            flow = WhatsAppLinkFlow(state)
            return await flow.start()
        
        # 12) Help
        elif intent == Intent.GENERAL_SUPPORT:
            return self._get_help_message(state)
        
        # 13) Greeting
        elif intent == Intent.GREETING:
            return self._get_greeting_message(state)
        
        # 14) Goodbye
        elif intent == Intent.GOODBYE:
            return self._get_goodbye_message(state)

        # 15) Confirmation/Denial outside of flow
        elif intent in (Intent.CONFIRMATION, Intent.DENIAL):
            return self._get_help_message(state)
        
        # 16) Off-topic
        elif intent == Intent.OFF_TOPIC:
            return self._get_off_topic_message(state)
        
        # Default
        else:
            return self._get_unknown_message(state)
    
    async def _handle_view_account(self, state: ConversationState) -> str:
        """Handle view account request"""
        try:
            account = await account_service.get_my_account(state.phone_number)
            
            if not account:
                return (
                    "I couldn't find an account with this phone number. "
                    "Would you like to create an account?"
                )
            
            state.account_id = account.id
            state.account_balance = account.balance
            
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
        phone = state.phone_number

        try:
            phone_check = await account_service.check_phone_number(phone)
            state.mark_phone_checked(phone_check.exists)

            if not state.account_exists:
                return (
                    "I couldn't find an account with this phone number. "
                    "Would you like to create an account?"
                )

            wallet_balance = await account_service.get_balance(phone)
            state.account_balance = wallet_balance.balance

            return (
                f"Your current wallet balance is "
                f"{wallet_balance.balance:.4f} {wallet_balance.currency}. "
                "Is there anything else I can help you with?"
            )

        except Exception as e:
            logger.error(f"Failed to handle balance inquiry: {e}")
            return (
                "Sorry, I couldn't retrieve your wallet balance right now. "
                "Please try again later."
            )
    
    async def _handle_transaction_history(self, state: ConversationState) -> str:
        """Handle transaction history inquiry"""
        phone = state.phone_number

        try:
            phone_check = await account_service.check_phone_number(phone)
            state.mark_phone_checked(phone_check.exists)

            if not state.account_exists:
                return (
                    "I couldn't find an account with this phone number. "
                    "Would you like to create an account?"
                )

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

    # =========================================================================
    # HELPER METHODS FOR RESPONSES
    # =========================================================================

    def _get_help_message(self, state: ConversationState) -> str:
        """Get help message in user's language"""
        lang = state.lang or "en"
        if lang == "fr":
            return (
                "Je peux vous aider à :\n"
                "• Créer un compte\n"
                "• Voir votre compte\n"
                "• Faire un retrait\n"
                "• Faire un dépôt\n"
                "• Vérifier votre solde\n"
                "• Voir l'historique des transactions\n"
                "• Envoyer de l'argent (transfert)\n"
                "• Voir le tableau de bord\n"
                "• Réinitialiser votre mot de passe\n"
                "• Changer votre mot de passe\n"
                "• Lier votre compte WhatsApp\n\n"
                "Que souhaitez-vous faire ?"
            )
        return (
            "I can help you with:\n"
            "• Create an account\n"
            "• View your account\n"
            "• Make a withdrawal\n"
            "• Make a deposit\n"
            "• Check your balance\n"
            "• View transaction history\n"
            "• Send money (transfer)\n"
            "• View dashboard & statistics\n"
            "• Reset your password\n"
            "• Change your password\n"
            "• Link your WhatsApp account\n\n"
            "What would you like to do?"
        )

    def _get_greeting_message(self, state: ConversationState) -> str:
        """Get greeting message in user's language"""
        lang = state.lang or "en"
        if lang == "fr":
            return f"Bienvenue chez {settings.COMPANY_NAME} ! Comment puis-je vous aider aujourd'hui ?"
        return f"Welcome to {settings.COMPANY_NAME}! How can I help you today?"

    def _get_goodbye_message(self, state: ConversationState) -> str:
        """Get goodbye message in user's language"""
        lang = state.lang or "en"
        if lang == "fr":
            return "Merci d'utiliser notre service. Bonne journée !"
        return "Thank you for using our service. Have a great day!"

    def _get_unknown_message(self, state: ConversationState) -> str:
        """Get unknown intent message in user's language"""
        lang = state.lang or "en"
        if lang == "fr":
            return "Je suis désolé, je n'ai pas compris. Pourriez-vous reformuler ?"
        return "I'm sorry, I didn't understand that. Could you please rephrase?"

    def _get_off_topic_message(self, state: ConversationState) -> str:
        """Get off-topic message in user's language"""
        lang = state.lang or "en"
        if lang == "fr":
            return (
                f"Je suis l'assistant de {settings.COMPANY_NAME} et je ne peux vous aider "
                "qu'avec les services liés à votre compte. Comment puis-je vous aider avec votre compte ?"
            )
        return (
            f"I'm the {settings.COMPANY_NAME} assistant and I can only help with "
            "account-related services. How can I help you with your account?"
        )