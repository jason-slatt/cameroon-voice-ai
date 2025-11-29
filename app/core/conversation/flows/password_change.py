"""Password Change flow"""

from typing import Tuple, Optional

from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.services.backend.accounts import account_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PasswordChangeFlow(BaseFlow):
    """
    Handles password change flow:
      1) Ask for current password
      2) Ask for new password
      3) Confirm new password
      4) Complete: call POST /api/change-password
    """

    FLOW_NAME = "password_change"

    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.prompts = FLOW_PROMPTS.get("password_change", {})

    def _get_prompt(self, key: str, **kwargs) -> str:
        """Get prompt in user's language"""
        lang = self.state.lang or "en"
        prompt_key = f"{key}_{lang}"
        
        prompt = self.prompts.get(prompt_key)
        if prompt is None:
            prompt = self.prompts.get(f"{key}_en", "")
        
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
            "start_en": "I'll help you change your password. Please enter your current password:",
            "start_fr": "Je vais vous aider à changer votre mot de passe. Veuillez entrer votre mot de passe actuel :",
            "ask_new_password_en": "Now please enter your new password (minimum 6 characters):",
            "ask_new_password_fr": "Maintenant, veuillez entrer votre nouveau mot de passe (minimum 6 caractères) :",
            "ask_confirm_password_en": "Please confirm your new password by entering it again:",
            "ask_confirm_password_fr": "Veuillez confirmer votre nouveau mot de passe en le saisissant à nouveau :",
            "password_mismatch_en": "The passwords don't match. Please enter your new password again:",
            "password_mismatch_fr": "Les mots de passe ne correspondent pas. Veuillez entrer à nouveau votre nouveau mot de passe :",
            "password_too_short_en": "Password must be at least 6 characters. Please try again:",
            "password_too_short_fr": "Le mot de passe doit contenir au moins 6 caractères. Veuillez réessayer :",
            "invalid_password_en": "Please enter a valid password:",
            "invalid_password_fr": "Veuillez entrer un mot de passe valide :",
            "success_en": "✅ Your password has been changed successfully!",
            "success_fr": "✅ Votre mot de passe a été changé avec succès !",
            "error_en": "Sorry, I couldn't change your password. The current password may be incorrect. Please try again.",
            "error_fr": "Désolé, je n'ai pas pu changer votre mot de passe. Le mot de passe actuel est peut-être incorrect. Veuillez réessayer.",
            "cancelled_en": "Password change cancelled. How else can I help you?",
            "cancelled_fr": "Changement de mot de passe annulé. Comment puis-je vous aider autrement ?",
            "max_attempts_en": "Too many failed attempts. Please try again later.",
            "max_attempts_fr": "Trop de tentatives échouées. Veuillez réessayer plus tard.",
            "no_account_en": "You don't have an account yet. Would you like to create one?",
            "no_account_fr": "Vous n'avez pas encore de compte. Souhaitez-vous en créer un ?",
        }
        return defaults.get(f"{key}_{lang}", defaults.get(f"{key}_en", ""))

    async def start(self) -> str:
        """Start password change flow"""
        lang = self.state.lang or "en"
        
        # Ensure user has an account
        if not self.state.account_id:
            account = await account_service.get_account_by_phone(self.state.phone_number)
            if account:
                self.state.account_id = account.id
            else:
                return self._get_prompt("no_account")

        # Start the flow
        self.state.start_flow(FlowType.PASSWORD_CHANGE, FlowStep.ASK_OLD_PASSWORD)
        
        # Clear collected data
        self.state.collected_data = self.state.collected_data or {}
        self.state.collected_data.clear()

        return self._get_prompt("start")

    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for password change"""
        step = self.state.flow_step

        if step == FlowStep.ASK_OLD_PASSWORD:
            return await self._process_old_password(user_input)

        elif step == FlowStep.ASK_NEW_PASSWORD:
            return await self._process_new_password(user_input)

        elif step == FlowStep.CONFIRM_PASSWORD:
            return await self._process_confirm_password(user_input)

        if step == FlowStep.COMPLETE:
            return "", True

        return "", False

    async def _process_old_password(self, user_input: str) -> Tuple[str, bool]:
        """Process current password input"""
        password = (user_input or "").strip()

        if password and len(password) >= 4:
            self.state.add_data("old_password", password)
            self.state.next_step(FlowStep.ASK_NEW_PASSWORD)
            return self._get_prompt("ask_new_password"), False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("invalid_password"), False

    async def _process_new_password(self, user_input: str) -> Tuple[str, bool]:
        """Process new password input"""
        password = (user_input or "").strip()

        if password and len(password) >= 6:
            self.state.add_data("new_password", password)
            self.state.next_step(FlowStep.CONFIRM_PASSWORD)
            return self._get_prompt("ask_confirm_password"), False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("password_too_short"), False

    async def _process_confirm_password(self, user_input: str) -> Tuple[str, bool]:
        """Process password confirmation"""
        confirm_password = (user_input or "").strip()
        new_password = self.state.get_data("new_password")

        if confirm_password == new_password:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True

        # Passwords don't match - go back to new password step
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        self.state.next_step(FlowStep.ASK_NEW_PASSWORD)
        self.state.collected_data.pop("new_password", None)
        return self._get_prompt("password_mismatch"), False

    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete password change by calling backend"""
        phone_number = self.state.phone_number
        old_password = self.state.get_data("old_password")
        new_password = self.state.get_data("new_password")

        try:
            result = await account_service.change_password(
                phone_number=phone_number,
                old_password=old_password,
                new_password=new_password,
            )

            self.state.reset_flow()

            if result.success:
                return self._get_prompt("success"), {
                    "success": True,
                    "message": result.message,
                }
            else:
                return self._get_prompt("error"), {
                    "success": False,
                    "error": result.message,
                }

        except Exception as e:
            logger.error(f"Password change failed: {e}")
            self.state.reset_flow()
            return self._get_prompt("error"), {"error": str(e)}