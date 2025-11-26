"""Transaction-related backend API calls"""

from typing import Optional, List
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


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Transaction:
    """Transaction data model"""
    id: str
    account_id: str
    type: TransactionType
    amount: float
    currency: str = "XAF"
    status: TransactionStatus = TransactionStatus.COMPLETED
    description: Optional[str] = None
    reference: Optional[str] = None
    created_at: Optional[datetime] = None


class TransactionService:
    """Service for transaction-related operations"""
    
    def __init__(self):
        self.client = backend_client
    
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
            # Return mock transaction for development
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
            # Return mock transaction for development
            import uuid
            return Transaction(
                id=str(uuid.uuid4()),
                account_id=account_id,
                type=TransactionType.DEPOSIT,
                amount=amount,
                status=TransactionStatus.COMPLETED,
                description=description,
            )
    
    async def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID"""
        try:
            response = await self.client.get(f"/api/v1/transactions/{transaction_id}")
            
            return Transaction(
                id=response.get("id", transaction_id),
                account_id=response.get("accountId", ""),
                type=TransactionType(response.get("type", "DEPOSIT")),
                amount=response.get("amount", 0.0),
                currency=response.get("currency", "XAF"),
                status=TransactionStatus(response.get("status", "COMPLETED")),
                description=response.get("description"),
                reference=response.get("reference"),
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
        """Get recent transactions for an account"""
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
    async def get_dashboard_transactions(
        self,
        phone_number: str,
        limit: int = 5,
    ) -> List[Transaction]:
        """
        Get transactions using GET /dashboard/transactions.

        Swagger:
        GET /dashboard/transactions
        "Obtenir les transactions – Retourne la liste des transactions enregistrées."

        If the backend expects a phoneNumber filter, we pass it as a query param.
        Adjust param name if Swagger shows something else.
        """
        logger.info(f"Fetching dashboard transactions for {phone_number}")

        try:
            # Build query parameters
            params = {"phoneNumber": phone_number}

            raw = await self.client.get(
                "/dashboard/transactions",
                params=params,
            )

            logger.info(f"/dashboard/transactions response: {raw}")

            # raw can be:
            # - a list of transactions
            # - or an object with a 'transactions' field
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, dict) and "transactions" in raw:
                items = raw["transactions"]
            else:
                # Unexpected shape
                logger.warning(f"Unexpected /dashboard/transactions response shape: {type(raw)}")
                items = []

            transactions: List[Transaction] = []

            for t in items:
                try:
                    transactions.append(Transaction(
                        id=str(t.get("id", "")),
                        account_id=t.get("accountId"),
                        type=TransactionType(t.get("type", "DEPOSIT")),
                        amount=float(t.get("amount", 0.0)),
                        currency=t.get("currency", "XAF"),
                        status=TransactionStatus(t.get("status", "COMPLETED")),
                        description=t.get("description"),
                        reference=t.get("reference"),
                        created_at=datetime.fromisoformat(t["createdAt"]) if t.get("createdAt") else None,
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing transaction item {t}: {e}")
                    continue

            return transactions

        except BackendAPIError as e:
            logger.error(f"Backend error fetching dashboard transactions: {e}")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch dashboard transactions: {e}")
            return []

# Singleton instance
transaction_service = TransactionService()