"""Dashboard flow (view transactions, stats, holders)"""

from typing import Tuple, Optional
from enum import Enum

from ..state import ConversationState, FlowType, FlowStep
from .base import BaseFlow
from app.services.backend.accounts import account_service
from app.services.backend.transactions import transaction_service
from app.config import settings
from app.config.prompts import FLOW_PROMPTS
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DashboardAction(str, Enum):
    """Dashboard query actions"""
    VIEW_TRANSACTIONS = "view_transactions"
    VIEW_TRANSACTION_AMOUNT = "view_transaction_amount"
    VIEW_REGISTRATIONS = "view_registrations"
    VIEW_HOLDERS = "view_holders"


class DashboardFlow(BaseFlow):
    """
    Handles dashboard queries:
      1) Ask what info user wants (transactions, stats, holders)
      2) Fetch and display the requested data
    
    Endpoints used:
      - GET /dashboard/transactions
      - GET /dashboard/transaction-amount
      - GET /dashboard/registrations
      - GET /dashboard/holders
    """

    def __init__(self, state: ConversationState):
        super().__init__(state)
        self.prompts = FLOW_PROMPTS.get("dashboard", {})

    def _get_prompt(self, key: str, **kwargs) -> str:
        """Get prompt in user's language"""
        lang = self.state.lang or "en"
        prompt_key = f"{key}_{lang}"
        
        # Try language-specific key first
        prompt = self.prompts.get(prompt_key)
        
        # Fallback to English
        if prompt is None:
            prompt = self.prompts.get(f"{key}_en", "")
        
        # Format with kwargs if provided
        if kwargs and prompt:
            try:
                return prompt.format(**kwargs)
            except KeyError:
                return prompt
        
        return prompt or ""

    async def start(self) -> str:
        """Start dashboard flow"""
        lang = self.state.lang or "en"
        
        # Ensure user has an account
        if not self.state.account_id:
            account = await account_service.get_account_by_phone(self.state.phone_number)
            if account:
                self.state.account_id = account.id
                self.state.account_balance = account.balance
            else:
                if lang == "fr":
                    return "Vous n'avez pas encore de compte. Souhaitez-vous en créer un ?"
                return "You don't have an account yet. Would you like to create one?"

        # Start the flow
        self.state.start_flow(FlowType.DASHBOARD, FlowStep.ASK_DASHBOARD_ACTION)

        # Clear collected data
        self.state.collected_data = self.state.collected_data or {}
        self.state.collected_data.clear()

        return self._get_prompt("start")

    async def process(self, user_input: str) -> Tuple[str, bool]:
        """Process user input for dashboard queries"""
        step = self.state.flow_step

        if step == FlowStep.ASK_DASHBOARD_ACTION:
            return await self._process_action_selection(user_input)

        if step == FlowStep.COMPLETE:
            return "", True

        return "", False

    async def _process_action_selection(self, user_input: str) -> Tuple[str, bool]:
        """Process the user's dashboard action selection"""
        action = self._extract_action(user_input)

        if action:
            self.state.add_data("dashboard_action", action.value)
            self.state.next_step(FlowStep.COMPLETE)
            return "", True

        # Couldn't understand the action
        if self.state.increment_attempts():
            self.state.reset_flow()
            return self._get_prompt("max_attempts"), True

        return self._get_prompt("ask_action_retry"), False

    async def complete(self) -> Tuple[str, Optional[dict]]:
        """Complete dashboard query by fetching requested data"""
        action_str = self.state.get_data("dashboard_action")
        
        try:
            action = DashboardAction(action_str)
        except (ValueError, TypeError):
            self.state.reset_flow()
            return self._get_prompt("error"), None

        try:
            if action == DashboardAction.VIEW_TRANSACTIONS:
                return await self._fetch_transactions()

            elif action == DashboardAction.VIEW_TRANSACTION_AMOUNT:
                return await self._fetch_transaction_amount()

            elif action == DashboardAction.VIEW_REGISTRATIONS:
                return await self._fetch_registration_stats()

            elif action == DashboardAction.VIEW_HOLDERS:
                return await self._fetch_account_holders()

            else:
                self.state.reset_flow()
                return self._get_prompt("error"), None

        except Exception as e:
            logger.error(f"Dashboard flow error: {e}")
            self.state.reset_flow()
            return self._get_prompt("error"), {"error": str(e)}

    # =========================================================================
    # DATA FETCHING METHODS
    # =========================================================================

    async def _fetch_transactions(self) -> Tuple[str, Optional[dict]]:
        """Fetch and format transactions list"""
        lang = self.state.lang or "en"
        
        transactions = await transaction_service.get_transactions(
            phone_number=self.state.phone_number,
            limit=10,
        )

        self.state.reset_flow()

        if not transactions:
            return self._get_prompt("no_transactions"), {"transactions": []}

        # Format the response
        lines = [self._get_prompt("transactions_header"), ""]

        for i, tx in enumerate(transactions[:10], 1):
            # Format date
            date_str = ""
            if tx.created_at:
                date_str = tx.created_at.strftime("%d/%m/%Y %H:%M")

            # Format type with emoji
            type_emoji = self._get_transaction_emoji(tx.type.value)
            
            # Format amount
            amount_str = f"{tx.amount:,.0f} {tx.currency}"

            # Build line
            line = f"{i}. {type_emoji} **{tx.type.value}** - {amount_str}"
            if date_str:
                line += f" ({date_str})"
            if tx.reference:
                line += f"\n   Ref: `{tx.reference}`"

            lines.append(line)

        message = "\n".join(lines)

        return message, {
            "transactions": [
                {
                    "id": tx.id,
                    "type": tx.type.value,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "status": tx.status.value,
                    "reference": tx.reference,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None,
                }
                for tx in transactions
            ]
        }

    async def _fetch_transaction_amount(self) -> Tuple[str, Optional[dict]]:
        """Fetch and format transaction amount summary"""
        lang = self.state.lang or "en"
        
        summary = await transaction_service.get_transaction_amount()

        self.state.reset_flow()

        # Format the response
        amount_str = f"{summary.total_amount:,.0f}"

        lines = [
            self._get_prompt("amount_header"),
            "",
            self._get_prompt("total_amount", amount=amount_str, currency=summary.currency),
        ]

        if summary.count is not None:
            lines.append(self._get_prompt("total_count", count=f"{summary.count:,}"))

        if summary.period:
            period_label = "Period" if lang == "en" else "Période"
            lines.append(f"{period_label}: {summary.period}")

        message = "\n".join(lines)

        return message, {
            "total_amount": summary.total_amount,
            "currency": summary.currency,
            "count": summary.count,
            "period": summary.period,
        }

    async def _fetch_registration_stats(self) -> Tuple[str, Optional[dict]]:
        """Fetch and format registration statistics"""
        lang = self.state.lang or "en"
        
        stats = await transaction_service.get_registration_stats()

        self.state.reset_flow()

        lines = [
            self._get_prompt("registrations_header"),
            "",
            self._get_prompt("total_registrations", count=f"{stats.total_registrations:,}"),
        ]

        if stats.period:
            period_label = "Period" if lang == "en" else "Période"
            lines.append(f"{period_label}: {stats.period}")

        if stats.breakdown:
            lines.append("")
            lines.append(self._get_prompt("breakdown_header"))
            for key, value in stats.breakdown.items():
                lines.append(f"  • {key}: {value:,}")

        message = "\n".join(lines)

        return message, {
            "total_registrations": stats.total_registrations,
            "period": stats.period,
            "breakdown": stats.breakdown,
        }

    async def _fetch_account_holders(self) -> Tuple[str, Optional[dict]]:
        """Fetch and format account holders list"""
        lang = self.state.lang or "en"
        
        holders = await transaction_service.get_account_holders(limit=10)

        self.state.reset_flow()

        if not holders:
            return self._get_prompt("no_holders"), {"holders": []}

        lines = [self._get_prompt("holders_header"), ""]

        for i, holder in enumerate(holders[:10], 1):
            balance_str = f"{holder.balance:,.0f}"
            
            line = f"{i}. **{holder.full_name}**"
            line += f"\n   📱 {holder.phone_number}"
            line += f"\n   💵 {self._get_prompt('holder_balance', balance=balance_str, currency=holder.currency)}"
            
            if holder.groupement_name:
                line += f"\n   🏘️ {self._get_prompt('holder_group', group=holder.groupement_name)}"
            
            status_label = "Status" if lang == "en" else "Statut"
            line += f"\n   {status_label}: {holder.status}"

            lines.append(line)

        message = "\n".join(lines)

        return message, {
            "holders": [
                {
                    "id": h.id,
                    "full_name": h.full_name,
                    "phone_number": h.phone_number,
                    "balance": h.balance,
                    "currency": h.currency,
                    "status": h.status,
                    "groupement_name": h.groupement_name,
                }
                for h in holders
            ]
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _extract_action(self, text: str) -> Optional[DashboardAction]:
        """Extract dashboard action from user input (supports EN and FR)"""
        lowered = (text or "").strip().lower()

        # Transaction list keywords (EN + FR)
        transaction_keywords = {
            # English
            "transactions", "transaction", "history", "my transactions",
            "show transactions", "list transactions", "view transactions",
            # French
            "historique", "mes transactions", "voir transactions",
            "afficher transactions", "liste transactions",
            # Number
            "1",
        }

        # Transaction amount keywords (EN + FR)
        amount_keywords = {
            # English
            "amount", "total", "sum", "total amount", "transaction amount",
            # French
            "montant", "montant total", "somme", "total des transactions",
            # Number
            "2",
        }

        # Registration keywords (EN + FR)
        registration_keywords = {
            # English
            "registrations", "registration", "stats", "statistics",
            "signups", "sign ups", "signup stats",
            # French
            "inscriptions", "inscription", "statistiques", "stats inscription",
            "statistiques d'inscription",
            # Number
            "3",
        }

        # Holders keywords (EN + FR)
        holder_keywords = {
            # English
            "holders", "holder", "accounts", "account holders",
            "users", "members", "list holders",
            # French
            "détenteurs", "detenteurs", "titulaires", "comptes",
            "liste des comptes", "titulaires de comptes",
            # Number
            "4",
        }

        # Check each category
        for keyword in transaction_keywords:
            if keyword in lowered:
                return DashboardAction.VIEW_TRANSACTIONS

        for keyword in amount_keywords:
            if keyword in lowered:
                return DashboardAction.VIEW_TRANSACTION_AMOUNT

        for keyword in registration_keywords:
            if keyword in lowered:
                return DashboardAction.VIEW_REGISTRATIONS

        for keyword in holder_keywords:
            if keyword in lowered:
                return DashboardAction.VIEW_HOLDERS

        return None

    def _get_transaction_emoji(self, tx_type: str) -> str:
        """Get emoji for transaction type"""
        emoji_map = {
            "DEPOSIT": "📥",
            "WITHDRAWAL": "📤",
            "TRANSFER": "🔄",
            "TOP_UP": "📲",
        }
        return emoji_map.get(tx_type.upper(), "💳")