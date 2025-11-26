"""Transfer flow (send tokens/money)"""

from typing import Tuple, Optional
import re

from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.services.backend import account_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS


class TransferFlow(BaseFlow):
    """
    Handles transfer flow:
      1) Ask receiver phone number
      2) Ask amount
      3) Ask PIN
      4) Confirm
      5) Complete: call POST /api/transfer
    """

    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.prompts = FLOW_PROMPTS["transfer"]

    async def start(self) -> str:
        """Start transfer flow"""
        # Ensure user has an account (same pattern as TopUpFlow)
        if not self.state.account_id:
            account = await account_service.get_account_by_phone(self.state.phone_number)
            if account:
                self.state.account_id = account.id
                self.state.account_balance = account.balance
            else:
                return "You don't have an account yet. Would you like to create one?"

        # Start the flow
        self.state.start_flow(FlowType.TRANSFER, FlowStep.ASK_RECEIVER)

        # Clear collected data for this transaction
        self.state.collected_data = self.state.collected_data or {}
        self.state.collected_data.clear()

        return self.prompts["start"]

    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for transfer"""
        step = self.state.flow_step

        if step == FlowStep.ASK_RECEIVER:
            return await self._process_receiver(user_input)

        elif step == FlowStep.ASK_AMOUNT:
            return await self._process_amount(user_input)

        elif step == FlowStep.ASK_PIN:
            return await self._process_pin(user_input)

        elif step == FlowStep.CONFIRM:
            return await self._process_confirmation(user_input)

        return "", False

    async def _process_receiver(self, user_input: str) -> Tuple[str, bool]:
        receiver = self._extract_phone(user_input)

        if receiver:
            self.state.add_data("receiverPhoneNumber", receiver)
            self.state.next_step(FlowStep.ASK_AMOUNT)
            return self.prompts["ask_amount"], False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I couldn't understand the receiver phone number. Let's try again later.", True

        return self.prompts["ask_receiver_retry"], False

    async def _process_amount(self, user_input: str) -> Tuple[str, bool]:
        amount = self._extract_amount(user_input)

        if amount is not None:
            if amount <= 0:
                return "Amount must be greater than 0.", False

            # Optional guard: balance check if known
            if self.state.account_balance is not None and amount > float(self.state.account_balance):
                return (
                    f"Insufficient balance. Your balance is {self.state.account_balance:.0f} "
                    f"{settings.CURRENCY}. Please enter a smaller amount."
                ), False

            self.state.add_data("amount", str(amount))  # backend expects string
            self.state.next_step(FlowStep.ASK_PIN)
            return self.prompts["ask_pin"], False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return "I couldn't understand the amount. Let's try again later.", True

        return self.prompts["ask_amount_retry"].format(currency=settings.CURRENCY), False

    async def _process_pin(self, user_input: str) -> Tuple[str, bool]:
        pin = self._extract_pin(user_input)

        if pin:
            self.state.add_data("pin", pin)
            self.state.next_step(FlowStep.CONFIRM)

            receiver = self.state.get_data("receiverPhoneNumber")
            amount = self.state.get_data("amount")

            return self.prompts["confirm"].format(
                amount=amount,
                currency=settings.CURRENCY,
                receiver=receiver,
            ), False

        if self.state.increment_attempts():
            self.state.reset_flow()
            return "Too many failed attempts. Transfer cancelled.", True

        return self.prompts["ask_pin_retry"], False

    async def _process_confirmation(self, user_input: str) -> Tuple[str, bool]:
        lowered = (user_input or "").strip().lower()

        yes = {"yes", "y", "ok", "okay", "confirm", "go ahead", "proceed"}
        no = {"no", "n", "cancel", "stop"}

        if lowered in yes:
            self.state.next_step(FlowStep.COMPLETE)
            return "", True

        if lowered in no:
            # Go back to amount (or receiver) — your choice
            self.state.next_step(FlowStep.ASK_AMOUNT)
            self.state.collected_data.pop("amount", None)
            self.state.collected_data.pop("pin", None)
            return "Okay. How much do you want to send instead?", False

        receiver = self.state.get_data("receiverPhoneNumber")
        amount = self.state.get_data("amount")
        return self.prompts["confirm_retry"].format(
            amount=amount,
            currency=settings.CURRENCY,
            receiver=receiver,
        ), False

    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete transfer by calling backend"""
        phone_number = self.state.phone_number
        receiver = self.state.get_data("receiverPhoneNumber")
        amount = self.state.get_data("amount")
        pin = self.state.get_data("pin")

        try:
            result = await account_service.transfer(
                phone_number=phone_number,
                receiver_phone_number=receiver,
                pin=pin,
                amount=amount,
            )

            # Optional: refresh balance after transfer
            try:
                balance = await account_service.get_balance(self.state.account_id)
                self.state.account_balance = balance.balance
            except Exception:
                pass

            self.state.reset_flow()

            ref = getattr(result, "reference", None) or "N/A"
            return (
                self.prompts["success"].format(reference=ref),
                (getattr(result, "raw", None) or {}),
            )

        except Exception as e:
            self.state.reset_flow()
            return self.prompts["error"], {"error": str(e)}

    # --------------------
    # Helpers (local rules)
    # --------------------

    def _extract_phone(self, text: str) -> Optional[str]:
        # keep digits only, support formats like +237 6xx xx xx xx
        digits = "".join(ch for ch in (text or "") if ch.isdigit())
        if len(digits) < 8:
            return None
        return digits

    def _extract_amount(self, text: str) -> Optional[int]:
        # Accept: "10 000", "10000", "10,000", "10.000", "10000 XAF"
        cleaned = (text or "").lower()
        cleaned = cleaned.replace("xof", "").replace("xaf", "").replace("fcfa", "").replace("francs", "")
        cleaned = cleaned.replace(" ", "").replace(",", "").replace(".", "")
        m = re.search(r"(\d+)", cleaned)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def _extract_pin(self, text: str) -> Optional[str]:
        pin = (text or "").strip().replace(" ", "")
        if pin.isdigit() and len(pin) in (4, 5, 6):
            return pin
        return None
