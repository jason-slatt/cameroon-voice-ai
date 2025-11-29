"""Password Reset flow"""

from typing import Tuple, Optional

from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.services.backend.accounts import account_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PasswordResetFlow(BaseFlow):
    """
    Handles password reset flow:
      1) Confirm phone number
      2) Confirm action
      3) Complete: call POST /api/reset-password
    """

    FLOW_NAME = "password_reset"

    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.prompts = FLOW_PROMPTS.get("password_reset", {})

    def _get_prompt(self, key: str, **kwargs) -> str:
        """Get prompt in user's language"""
        lang = self.state.lang or "en"
        prompt_key = f"{key}_{lang}"
        
        prompt = self.prompts.get(prompt_key)
        if prompt is None:
            prompt = self.prompts.get(f"{key}_en", "")
        
        # Fallback defaults
        if not prompt:
            prompt = self._get_default_prompt(key, lang)
        
        if kwargs and prompt:
            try:
                return prompt.format(**kwargs)
            except KeyError:
                return prompt
        
        return prompt or ""

    def _get_default_prompt(self, key: str, lang: str) -> str:
        """Get default prompt if not in config"""
        defaults = {
            "start_en": "I'll help you reset your password. I'll send a reset link to your registered phone number {phone}. Do you want to proceed? (yes/no)",
            "start_fr": "Je vais vous aider à réinitialiser votre mot de passe. J'enverrai un lien de réinitialisation à votre numéro {phone}. Voulez-vous continuer ? (oui/non)",
            "confirm_retry_en": "Please say 'yes' to confirm the password reset or 'no' to cancel.",
            "confirm_retry_fr": "Veuillez dire 'oui' pour confirmer la réinitialisation ou 'non' pour annuler.",
            "success_en": "✅ Password reset initiated successfully! Please check your phone for instructions to set a new password.",
            "success_fr": "✅ Réinitialisation du mot de passe initiée avec succès ! Veuillez vérifier votre téléphone pour les instructions.",
            "error_en": "Sorry, I couldn't reset your password. Please try again later or contact support.",
            "error_fr": "Désolé, je n'ai pas pu réinitialiser votre mot de passe. Veuillez réessayer plus tard ou contacter le support.",
            "cancelled_en": "Password reset cancelled. How else can I help you?",
            "cancelled_fr": "Réinitialisation du mot de passe annulée. Comment puis-je vous aider autrement ?",
            "max_attempts_en": "Too many failed attempts. Please try again later.",
            "max_attempts_fr": "Trop de tentatives échouées. Veuillez réessayer plus tard.",
            "no_account_en": "You don't have an account yet. Would you like to create one?",
            "no_account_fr": "Vous n'avez pas encore de compte. Souhaitez-vous en créer un ?",
        }
        return defaults.get(f"{key}_{lang}", defaults.get(f"{key}_en", ""))

    async def start(self) -> str:
        """Start password reset flow"""
        lang = self.state.lang or "en"
        
        # Ensure user has an account
        if not self.state.account_id:
            account = await account_service.get_account_by_phone(self.state.phone_number)
            if account:
                self.state.account_id = account.id
            else:
                return self._get_prompt("no_account")

        # Start the flow
        self.state.start_flow(FlowType.PASSWORD_RESET, FlowStep.CONFIRM)
        
        # Clear collected data
        self.state.collected_data = self.state.collected_data or {}
        self.state.collected_data.clear()

        # Mask phone number for display
        phone = self.state.phone_number
        masked_phone = phone[:3] + "****" + phone[-3:] if len(phone) > 6 else phone

        return self._get_prompt("start", phone=masked_phone)

    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for password reset"""
        step = self.state.flow_step

        if step == FlowStep.CONFIRM:
            return await self._process_confirmation(user_input)

        if step == FlowStep.COMPLETE:
            return "", True

        return "", False

    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Process confirmation"""
        lowered = (user_input or "").strip().lower()

        yes_words = {"yes", "y", "ok", "okay", "confirm", "proceed", "oui", "o", "d'accord", "daccord"}
        no_words = {"no", "n", "cancel", "stop", "non", "annuler", "annule"}

        if lowered in yes_words:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True

        if lowered in no_words:
            self.state.reset_flow()
            return self._get_prompt("cancelled"), True

        # Didn't understand
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("confirm_retry"), False

    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete password reset by calling backend"""
        phone_number = self.state.phone_number

        try:
            result = await account_service.reset_password(phone_number)

            self.state.reset_flow()

            if result.success:
                return self._get_prompt("success"), {
                    "success": True,
                    "phone_number": phone_number,
                    "message": result.message,
                }
            else:
                return self._get_prompt("error"), {
                    "success": False,
                    "error": result.message,
                }

        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            self.state.reset_flow()
            return self._get_prompt("error"), {"error": str(e)}