# src/services/banking/mock_api.py
"""
Mock Banking API - Simulates real banking operations
Replace with real API calls in production
"""
import uuid
from typing import Dict, List, Any
from datetime import datetime, timedelta
import random

from src.core.logging import logger


class MockBankingAPI:
    """
    Simulated banking API for prototype
    Returns realistic responses without actual banking operations
    """

    # Simulated user accounts
    MOCK_ACCOUNTS: Dict[str, Dict[str, Any]] = {
        "default": {
            "balance": 5000.00,
            "available": 4800.00,
            "account_holder": "Jean Dupont",
            "iban": "FR76 3000 3000 0100 0000 0123 456",
            "bic": "SOGEFRPP",
        }
    }

    # Simulated beneficiaries
    MOCK_BENEFICIARIES: Dict[str, List[str]] = {
        "default": ["Paul", "Marie", "Sophie"],
    }

    async def get_account_balance(self, user_id: str) -> float:
        """Get account balance"""
        account = self._get_account(user_id)
        balance = account["balance"]

        logger.info("💰 Balance for %s: %s EUR", user_id, balance)
        return balance

    async def get_available_balance(self, user_id: str) -> float:
        """Get available balance (minus pending)"""
        account = self._get_account(user_id)
        return account["available"]

    async def check_beneficiary(self, user_id: str, name: str) -> bool:
        """Check if beneficiary exists"""
        beneficiaries = self.MOCK_BENEFICIARIES.get(
            user_id,
            self.MOCK_BENEFICIARIES["default"],
        )
        exists = name in beneficiaries

        logger.info("👤 Beneficiary '%s' exists: %s", name, exists)
        return exists

    async def execute_transfer(
        self,
        user_id: str,
        amount: float,
        currency: str,
        beneficiary: str,
    ) -> Dict[str, Any]:
        """Execute money transfer"""

        import asyncio

        await asyncio.sleep(0.5)

        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"

        logger.info(
            "💸 Transfer executed: %s %s to %s (ID: %s)",
            amount,
            currency,
            beneficiary,
            transaction_id,
        )

        # Simulate 95% success rate
        if random.random() < 0.95:
            return {
                "success": True,
                "transaction_id": transaction_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

        return {
            "success": False,
            "error": "Insufficient funds or technical error",
        }

    async def get_user_cards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's cards"""
        # In real life, this would query a card API
        return [
            {
                "card_id": "CARD-001",
                "card_number": "**** **** **** 1234",
                "card_type": "Visa",
                "status": "active",
            }
        ]

    async def block_card(self, user_id: str, card_id: str) -> Dict[str, Any]:
        """Block a card"""
        logger.info("🔒 Blocking card %s for user %s", card_id, user_id)

        return {
            "success": True,
            "blocked_at": datetime.utcnow().isoformat(),
        }

    async def add_beneficiary(
        self,
        user_id: str,
        name: str,
        iban: str | None = None,
    ) -> Dict[str, Any]:
        """Add new beneficiary"""

        beneficiary_id = f"BEN-{uuid.uuid4().hex[:8].upper()}"

        logger.info("👤 Adding beneficiary: %s (ID: %s)", name, beneficiary_id)

        if user_id not in self.MOCK_BENEFICIARIES:
            self.MOCK_BENEFICIARIES[user_id] = []
        self.MOCK_BENEFICIARIES[user_id].append(name)

        return {
            "success": True,
            "beneficiary_id": beneficiary_id,
        }

    async def get_transaction_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get transaction history"""

        transactions: List[Dict[str, Any]] = []
        max_items = min(limit, 5)

        for index in range(max_items):
            date = datetime.utcnow() - timedelta(days=index * 3)
            transactions.append(
                {
                    "transaction_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
                    "date": date,
                    "amount": round(random.uniform(10, 500), 2),
                    "description": random.choice(
                        [
                            "Virement à Paul",
                            "Achat Carrefour",
                            "Paiement EDF",
                            "Retrait DAB",
                            "Virement reçu",
                        ]
                    ),
                    "type": random.choice(["debit", "credit"]),
                }
            )

        return transactions

    async def get_account_info(self, user_id: str) -> Dict[str, Any]:
        """Get account information"""
        return self._get_account(user_id)

    async def pay_bill(
        self,
        user_id: str,
        amount: float,
        biller: str,
    ) -> Dict[str, Any]:
        """Pay a bill"""

        reference = f"BILL-{uuid.uuid4().hex[:8].upper()}"

        logger.info("🧾 Bill payment: %s EUR to %s", amount, biller)

        return {
            "success": True,
            "reference": reference,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _get_account(self, user_id: str) -> Dict[str, Any]:
        """Return account info for a user, falling back to default"""
        return self.MOCK_ACCOUNTS.get(user_id, self.MOCK_ACCOUNTS["default"])
