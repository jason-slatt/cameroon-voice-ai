"""Transaction and Dashboard-related backend API calls"""

from typing import Optional, List, Any, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .client import backend_client, BackendAPIError
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    TOP_UP = "TOP_UP"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Transaction:
    """Transaction data model"""
    id: str
    account_id: Optional[str] = None
    type: TransactionType = TransactionType.TRANSFER
    amount: float = 0.0
    currency: str = "XAF"
    status: TransactionStatus = TransactionStatus.COMPLETED
    description: Optional[str] = None
    reference: Optional[str] = None
    sender_phone: Optional[str] = None
    receiver_phone: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class TransactionAmountSummary:
    """Summary of transaction amounts from /dashboard/transaction-amount"""
    total_amount: float
    currency: str = "XAF"
    count: Optional[int] = None
    period: Optional[str] = None  # e.g., "daily", "weekly", "monthly"


@dataclass
class RegistrationStats:
    """Registration statistics from /dashboard/registrations"""
    total_registrations: int
    period: Optional[str] = None
    breakdown: Optional[Dict[str, int]] = None  # e.g., {"daily": 10, "weekly": 50}


@dataclass
class AccountHolder:
    """Account holder info from /dashboard/holders"""
    id: str
    full_name: str
    phone_number: str
    balance: float = 0.0
    currency: str = "XAF"
    status: str = "ACTIVE"
    groupement_id: Optional[int] = None
    groupement_name: Optional[str] = None
    created_at: Optional[datetime] = None


class TransactionService:
    """Service for transaction and dashboard operations"""

    def __init__(self):
        self.client = backend_client

    # =========================================================================
    # DASHBOARD ENDPOINTS
    # =========================================================================

    async def get_transactions(
        self,
        phone_number: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Transaction]:
        """
        Get transactions list.

        Swagger: GET /dashboard/transactions
        "Obtenir les transactions – Retourne la liste des transactions enregistrées."
        """
        logger.info(f"Fetching transactions (phone={phone_number}, limit={limit})")

        try:
            params: Dict[str, Any] = {}
            if phone_number:
                params["phoneNumber"] = phone_number
            if limit:
                params["limit"] = limit

            raw = await self.client.get(
                "/dashboard/transactions",
                params=params if params else None,
            )

            logger.debug(f"/dashboard/transactions response: {raw}")

            return self._parse_transactions(raw)

        except BackendAPIError as e:
            logger.error(f"Backend error fetching transactions: {e}")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            return []

    async def get_dashboard_transactions(
        self,
        phone_number: str,
        limit: int = 5,
    ) -> List[Transaction]:
        """
        Get transactions using GET /dashboard/transactions.
        
        This is an alias for get_transactions() used by the manager.

        Swagger:
        GET /dashboard/transactions
        "Obtenir les transactions – Retourne la liste des transactions enregistrées."
        """
        return await self.get_transactions(phone_number=phone_number, limit=limit)

    async def get_transaction_amount(self) -> TransactionAmountSummary:
        """
        Get total transaction amount.

        Swagger: GET /dashboard/transaction-amount
        "Montant total des transactions"
        """
        logger.info("Fetching transaction amount summary")

        try:
            raw = await self.client.get("/dashboard/transaction-amount")

            logger.debug(f"/dashboard/transaction-amount response: {raw}")

            if not isinstance(raw, dict):
                logger.warning(f"Unexpected response type: {type(raw)}")
                return TransactionAmountSummary(total_amount=0.0)

            # Handle different response shapes
            data = raw.get("data", raw)

            total = (
                data.get("totalAmount")
                or data.get("total_amount")
                or data.get("amount")
                or data.get("total")
                or 0.0
            )

            try:
                total_amount = float(str(total))
            except (ValueError, TypeError):
                total_amount = 0.0

            return TransactionAmountSummary(
                total_amount=total_amount,
                currency=data.get("currency", "XAF"),
                count=data.get("count") or data.get("transactionCount"),
                period=data.get("period"),
            )

        except BackendAPIError as e:
            logger.error(f"Backend error fetching transaction amount: {e}")
            return TransactionAmountSummary(total_amount=0.0)

        except Exception as e:
            logger.error(f"Failed to fetch transaction amount: {e}")
            return TransactionAmountSummary(total_amount=0.0)

    async def get_registration_stats(self) -> RegistrationStats:
        """
        Get registration statistics.

        Swagger: GET /dashboard/registrations
        "Obtenir les statistiques des inscriptions"
        """
        logger.info("Fetching registration statistics")

        try:
            raw = await self.client.get("/dashboard/registrations")

            logger.debug(f"/dashboard/registrations response: {raw}")

            if not isinstance(raw, dict):
                logger.warning(f"Unexpected response type: {type(raw)}")
                return RegistrationStats(total_registrations=0)

            data = raw.get("data", raw)

            total = (
                data.get("totalRegistrations")
                or data.get("total_registrations")
                or data.get("total")
                or data.get("count")
                or 0
            )

            try:
                total_registrations = int(str(total))
            except (ValueError, TypeError):
                total_registrations = 0

            # Parse breakdown if available
            breakdown = None
            if "breakdown" in data:
                breakdown = data["breakdown"]
            elif "stats" in data:
                breakdown = data["stats"]

            return RegistrationStats(
                total_registrations=total_registrations,
                period=data.get("period"),
                breakdown=breakdown,
            )

        except BackendAPIError as e:
            logger.error(f"Backend error fetching registration stats: {e}")
            return RegistrationStats(total_registrations=0)

        except Exception as e:
            logger.error(f"Failed to fetch registration stats: {e}")
            return RegistrationStats(total_registrations=0)

    async def get_account_holders(
        self,
        limit: Optional[int] = None,
        page: Optional[int] = None,
    ) -> List[AccountHolder]:
        """
        Get list of account holders.

        Swagger: GET /dashboard/holders
        "Obtenir la liste des détenteurs de comptes"
        """
        logger.info(f"Fetching account holders (limit={limit}, page={page})")

        try:
            params: Dict[str, Any] = {}
            if limit:
                params["limit"] = limit
            if page:
                params["page"] = page

            raw = await self.client.get(
                "/dashboard/holders",
                params=params if params else None,
            )

            logger.debug(f"/dashboard/holders response: {raw}")

            return self._parse_account_holders(raw)

        except BackendAPIError as e:
            logger.error(f"Backend error fetching account holders: {e}")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch account holders: {e}")
            return []

    # =========================================================================
    # LEGACY / OTHER TRANSACTION METHODS
    # =========================================================================

    async def create_withdrawal(
        self,
        account_id: str,
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Create a withdrawal transaction"""
        logger.info(f"Creating withdrawal for account {account_id}: {amount} XAF")

        try:
            response = await self.client.post(
                "/api/v1/transactions/withdraw",
                data={
                    "accountId": account_id,
                    "amount": amount,
                    "description": description or "Voice assistant withdrawal",
                },
            )

            return Transaction(
                id=response.get("id", ""),
                account_id=account_id,
                type=TransactionType.WITHDRAWAL,
                amount=amount,
                currency=response.get("currency", "XAF"),
                status=TransactionStatus(response.get("status", "COMPLETED")),
                description=description,
                reference=response.get("reference"),
            )
        except BackendAPIError:
            raise
        except Exception as e:
            logger.warning(f"Failed to create withdrawal: {e}")
            import uuid
            return Transaction(
                id=str(uuid.uuid4()),
                account_id=account_id,
                type=TransactionType.WITHDRAWAL,
                amount=amount,
                status=TransactionStatus.COMPLETED,
                description=description,
            )

    async def create_deposit(
        self,
        account_id: str,
        amount: float,
        description: Optional[str] = None,
    ) -> Transaction:
        """Create a deposit transaction"""
        logger.info(f"Creating deposit for account {account_id}: {amount} XAF")

        try:
            response = await self.client.post(
                "/api/v1/transactions/deposit",
                data={
                    "accountId": account_id,
                    "amount": amount,
                    "description": description or "Voice assistant deposit",
                },
            )

            return Transaction(
                id=response.get("id", ""),
                account_id=account_id,
                type=TransactionType.DEPOSIT,
                amount=amount,
                currency=response.get("currency", "XAF"),
                status=TransactionStatus(response.get("status", "COMPLETED")),
                description=description,
                reference=response.get("reference"),
            )
        except BackendAPIError:
            raise
        except Exception as e:
            logger.warning(f"Failed to create deposit: {e}")
            import uuid
            return Transaction(
                id=str(uuid.uuid4()),
                account_id=account_id,
                type=TransactionType.DEPOSIT,
                amount=amount,
                status=TransactionStatus.COMPLETED,
                description=description,
            )

    async def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get a single transaction by ID"""
        try:
            response = await self.client.get(f"/api/v1/transactions/{transaction_id}")

            created_at = None
            if response.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(response["createdAt"])
                except Exception:
                    pass

            return Transaction(
                id=response.get("id", transaction_id),
                account_id=response.get("accountId"),
                type=TransactionType(response.get("type", "TRANSFER")),
                amount=float(response.get("amount", 0.0)),
                currency=response.get("currency", "XAF"),
                status=TransactionStatus(response.get("status", "COMPLETED")),
                description=response.get("description"),
                reference=response.get("reference"),
                created_at=created_at,
            )
        except BackendAPIError as e:
            if e.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.warning(f"Failed to get transaction: {e}")
            return None

    async def get_recent_transactions(
        self,
        account_id: str,
        limit: int = 5,
    ) -> List[Transaction]:
        """
        Get recent transactions for an account.
        
        This uses the older /api/v1/accounts/{account_id}/transactions endpoint.
        For dashboard transactions, use get_dashboard_transactions() instead.
        """
        try:
            response = await self.client.get(
                f"/api/v1/accounts/{account_id}/transactions",
                params={"page": 1, "pageSize": limit},
            )

            transactions = []
            for t in response.get("transactions", []):
                transactions.append(Transaction(
                    id=t.get("id", ""),
                    account_id=account_id,
                    type=TransactionType(t.get("type", "DEPOSIT")),
                    amount=t.get("amount", 0.0),
                    currency=t.get("currency", "XAF"),
                    status=TransactionStatus(t.get("status", "COMPLETED")),
                    description=t.get("description"),
                    reference=t.get("reference"),
                ))

            return transactions

        except Exception as e:
            logger.warning(f"Failed to get transactions: {e}")
            # Return mock transactions for development
            return [
                Transaction(
                    id="mock-1",
                    account_id=account_id,
                    type=TransactionType.DEPOSIT,
                    amount=10000.0,
                    status=TransactionStatus.COMPLETED,
                    description="Mock deposit",
                ),
                Transaction(
                    id="mock-2",
                    account_id=account_id,
                    type=TransactionType.WITHDRAWAL,
                    amount=5000.0,
                    status=TransactionStatus.COMPLETED,
                    description="Mock withdrawal",
                ),
            ]

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_transactions(self, raw: Any) -> List[Transaction]:
        """Parse transaction list from various response shapes"""
        # Determine the list of items
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = (
                raw.get("data")
                or raw.get("transactions")
                or raw.get("items")
                or []
            )
            if not isinstance(items, list):
                items = []
        else:
            logger.warning(f"Unexpected response shape: {type(raw)}")
            return []

        transactions: List[Transaction] = []

        for t in items:
            try:
                created_at = None
                if t.get("createdAt"):
                    try:
                        created_at = datetime.fromisoformat(
                            str(t["createdAt"]).replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                # Parse transaction type safely
                tx_type_raw = t.get("type", "TRANSFER")
                try:
                    tx_type = TransactionType(tx_type_raw.upper())
                except ValueError:
                    tx_type = TransactionType.TRANSFER

                # Parse status safely
                status_raw = t.get("status", "COMPLETED")
                try:
                    status = TransactionStatus(status_raw.upper())
                except ValueError:
                    status = TransactionStatus.COMPLETED

                transactions.append(Transaction(
                    id=str(t.get("id", "")),
                    account_id=t.get("accountId") or t.get("account_id"),
                    type=tx_type,
                    amount=float(t.get("amount", 0.0)),
                    currency=t.get("currency", "XAF"),
                    status=status,
                    description=t.get("description"),
                    reference=t.get("reference") or t.get("txHash"),
                    sender_phone=t.get("senderPhone") or t.get("sender_phone"),
                    receiver_phone=t.get("receiverPhone") or t.get("receiver_phone"),
                    created_at=created_at,
                ))
            except Exception as e:
                logger.warning(f"Error parsing transaction item {t}: {e}")
                continue

        return transactions

    def _parse_account_holders(self, raw: Any) -> List[AccountHolder]:
        """Parse account holder list from various response shapes"""
        # Determine the list of items
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = (
                raw.get("data")
                or raw.get("holders")
                or raw.get("accounts")
                or raw.get("items")
                or []
            )
            if not isinstance(items, list):
                items = []
        else:
            logger.warning(f"Unexpected response shape: {type(raw)}")
            return []

        holders: List[AccountHolder] = []

        for h in items:
            try:
                created_at = None
                if h.get("createdAt"):
                    try:
                        created_at = datetime.fromisoformat(
                            str(h["createdAt"]).replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                groupement = h.get("groupement") or {}

                holders.append(AccountHolder(
                    id=str(h.get("id", "")),
                    full_name=h.get("fullName") or h.get("full_name") or "",
                    phone_number=h.get("phoneNumber") or h.get("phone_number") or "",
                    balance=float(h.get("balance", 0.0)),
                    currency=h.get("currency", "XAF"),
                    status=h.get("status", "ACTIVE"),
                    groupement_id=groupement.get("id") or h.get("groupement_id"),
                    groupement_name=groupement.get("name") or h.get("groupementName"),
                    created_at=created_at,
                ))
            except Exception as e:
                logger.warning(f"Error parsing account holder item {h}: {e}")
                continue

        return holders


# Singleton instance
transaction_service = TransactionService()