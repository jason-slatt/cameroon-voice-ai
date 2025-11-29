"""WhatsApp Linking flow"""

from typing import Tuple, Optional
import re

from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.services.backend.accounts import account_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WhatsAppLinkFlow(BaseFlow):
    """
    Handles WhatsApp account linking flow:
      1) Ask if they want to link same number or different
      2) If different, ask for WhatsApp number
      3) Confirm
      4) Complete: call POST /api/link
    """

    FLOW_NAME = "whatsapp_link"

    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.prompts = FLOW_PROMPTS.get("whatsapp_link", {})

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
            "start_en": (
                "I'll help you link your WhatsApp account.\n\n"
                "Do you want to link your current phone number ({phone}) to WhatsApp?\n"
                "• Say 'yes' to use the same number\n"
                "• Say 'different' to enter a different WhatsApp number"
            ),
            "start_fr": (
                "Je vais vous aider à lier votre compte WhatsApp.\n\n"
                "Voulez-vous lier votre numéro actuel ({phone}) à WhatsApp ?\n"
                "• Dites 'oui' pour utiliser le même numéro\n"
                "• Dites 'différent' pour entrer un autre numéro WhatsApp"
            ),
            "ask_whatsapp_number_en": "Please enter your WhatsApp phone number:",
            "ask_whatsapp_number_fr": "Veuillez entrer votre numéro de téléphone WhatsApp :",
            "invalid_number_en": "I couldn't understand that number. Please enter a valid phone number (e.g., 690123456):",
            "invalid_number_fr": "Je n'ai pas compris ce numéro. Veuillez entrer un numéro valide (ex: 690123456) :",
            "confirm_en": "You want to link WhatsApp number {whatsapp} to your account. Is that correct? (yes/no)",
            "confirm_fr": "Vous voulez lier le numéro WhatsApp {whatsapp} à votre compte. Est-ce correct ? (oui/non)",
            "confirm_retry_en": "Please say 'yes' to confirm or 'no' to cancel.",
            "confirm_retry_fr": "Veuillez dire 'oui' pour confirmer ou 'non' pour annuler.",
            "success_en": "✅ WhatsApp account linked successfully! You can now receive notifications on WhatsApp.",
            "success_fr": "✅ Compte WhatsApp lié avec succès ! Vous pouvez maintenant recevoir des notifications sur WhatsApp.",
            "error_en": "Sorry, I couldn't link your WhatsApp account. Please try again later.",
            "error_fr": "Désolé, je n'ai pas pu lier votre compte WhatsApp. Veuillez réessayer plus tard.",
            "cancelled_en": "WhatsApp linking cancelled. How else can I help you?",
            "cancelled_fr": "Liaison WhatsApp annulée. Comment puis-je vous aider autrement ?",
            "max_attempts_en": "Too many failed attempts. Please try again later.",
            "max_attempts_fr": "Trop de tentatives échouées. Veuillez réessayer plus tard.",
            "no_account_en": "You don't have an account yet. Would you like to create one?",
            "no_account_fr": "Vous n'avez pas encore de compte. Souhaitez-vous en créer un ?",
            "already_linked_en": "Your account is already linked to WhatsApp. Would you like to update it?",
            "already_linked_fr": "Votre compte est déjà lié à WhatsApp. Souhaitez-vous le mettre à jour ?",
        }
        return defaults.get(f"{key}_{lang}", defaults.get(f"{key}_en", ""))

    async def start(self) -> str:
        """Start WhatsApp linking flow"""
        lang = self.state.lang or "en"
        
        # Ensure user has an account
        if not self.state.account_id:
            account = await account_service.get_account_by_phone(self.state.phone_number)
            if account:
                self.state.account_id = account.id
            else:
                return self._get_prompt("no_account")

        # Start the flow
        self.state.start_flow(FlowType.WHATSAPP_LINK, FlowStep.ASK_WHATSAPP_CHOICE)
        
        # Clear collected data
        self.state.collected_data = self.state.collected_data or {}
        self.state.collected_data.clear()

        # Mask phone number for display
        phone = self.state.phone_number
        masked_phone = phone[:3] + "****" + phone[-3:] if len(phone) > 6 else phone

        return self._get_prompt("start", phone=masked_phone)

    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for WhatsApp linking"""
        step = self.state.flow_step

        if step == FlowStep.ASK_WHATSAPP_CHOICE:
            return await self._process_choice(user_input)

        elif step == FlowStep.ASK_WHATSAPP_NUMBER:
            return await self._process_whatsapp_number(user_input)

        elif step == FlowStep.CONFIRM:
            return await self._process_confirmation(user_input)

        if step == FlowStep.COMPLETE:
            return "", True

        return "", False

    async def _process_choice(self, user_input: str) -> Tuple[str, bool]:
        """Process the user's choice - same number or different"""
        lowered = (user_input or "").strip().lower()

        # Use same number
        same_keywords = {"yes", "y", "ok", "same", "oui", "o", "même", "meme", "pareil"}
        # Use different number
        diff_keywords = {"different", "diff", "other", "no", "n", "différent", "autre", "non"}
        # Cancel
        cancel_keywords = {"cancel", "stop", "annuler", "annule"}

        if lowered in cancel_keywords:
            self.state.reset_flow()
            return self._get_prompt("cancelled"), True

        if lowered in same_keywords:
            # Use the same phone number
            self.state.add_data("whatsapp_number", self.state.phone_number)
            self.state.next_step(FlowStep.CONFIRM)
            
            phone = self.state.phone_number
            masked = phone[:3] + "****" + phone[-3:] if len(phone) > 6 else phone
            return self._get_prompt("confirm", whatsapp=masked), False

        if lowered in diff_keywords:
            # Ask for different number
            self.state.next_step(FlowStep.ASK_WHATSAPP_NUMBER)
            return self._get_prompt("ask_whatsapp_number"), False

        # Try to extract a phone number directly
        phone = self._extract_phone(user_input)
        if phone:
            self.state.add_data("whatsapp_number", phone)
            self.state.next_step(FlowStep.CONFIRM)
            masked = phone[:3] + "****" + phone[-3:] if len(phone) > 6 else phone
            return self._get_prompt("confirm", whatsapp=masked), False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("start", phone=self.state.phone_number), False

    async def _process_whatsapp_number(self, user_input: str) -> Tuple[str, bool]:
        """Process WhatsApp phone number input"""
        phone = self._extract_phone(user_input)

        if phone:
            self.state.add_data("whatsapp_number", phone)
            self.state.next_step(FlowStep.CONFIRM)
            masked = phone[:3] + "****" + phone[-3:] if len(phone) > 6 else phone
            return self._get_prompt("confirm", whatsapp=masked), False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("invalid_number"), False

    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Process confirmation"""
        lowered = (user_input or "").strip().lower()

        yes_words = {"yes", "y", "ok", "okay", "confirm", "oui", "o", "d'accord", "daccord"}
        no_words = {"no", "n", "cancel", "stop", "non", "annuler"}

        if lowered in yes_words:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True

        if lowered in no_words:
            self.state.reset_flow()
            return self._get_prompt("cancelled"), True

        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("confirm_retry"), False

    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete WhatsApp linking by calling backend"""
        phone_number = self.state.phone_number
        whatsapp_number = self.state.get_data("whatsapp_number")

        try:
            result = await account_service.link_whatsapp(
                phone_number=phone_number,
                whatsapp_number=whatsapp_number,
            )

            self.state.reset_flow()

            if result.success:
                return self._get_prompt("success"), {
                    "success": True,
                    "linked": result.linked,
                    "whatsapp_number": whatsapp_number,
                    "message": result.message,
                }
            else:
                return self._get_prompt("error"), {
                    "success": False,
                    "error": result.message,
                }

        except Exception as e:
            logger.error(f"WhatsApp linking failed: {e}")
            self.state.reset_flow()
            return self._get_prompt("error"), {"error": str(e)}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        # Keep digits only
        digits = "".join(ch for ch in (text or "") if ch.isdigit())
        
        # Valid phone number should have at least 8 digits
        if len(digits) >= 8:
            return digits
        
        return None