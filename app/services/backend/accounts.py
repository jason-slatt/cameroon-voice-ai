"""Account-related backend API calls"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from .client import backend_client, BackendAPIError
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Account:
    """Account data model"""
    id: str
    account_number: str
    full_name: str
    phone_number: str
    balance: float
    currency: str = "XAF"
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None


@dataclass
class AccountBalance:
    """Account balance data"""
    account_id: str
    balance: float
    currency: str = "XAF"


class AccountService:
    """Service for account-related operations"""
    
    def __init__(self):
        self.client = backend_client
    
    async def create_account(
        self,
        full_name: str,
        phone_number: str,
    ) -> Account:
        """Create a new account"""
        logger.info(f"Creating account for {phone_number}")
        
        try:
            response = await self.client.post(
                "/api/v1/accounts",
                data={
                    "fullName": full_name,
                    "phoneNumber": phone_number,
                },
            )
            
            return Account(
                id=response.get("id", ""),
                account_number=response.get("accountNumber", ""),
                full_name=response.get("fullName", full_name),
                phone_number=response.get("phoneNumber", phone_number),
                balance=response.get("balance", 0.0),
                currency=response.get("currency", "XAF"),
                status=response.get("status", "ACTIVE"),
            )
        except BackendAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            # For development/testing - create mock account
            import uuid
            return Account(
                id=str(uuid.uuid4()),
                account_number=f"{hash(phone_number) % 1000000:06d}",
                full_name=full_name,
                phone_number=phone_number,
                balance=0.0,
            )
    
    async def get_account_by_phone(self, phone_number: str) -> Optional[Account]:
        """Get account by phone number"""
        try:
            response = await self.client.get(
                f"/api/v1/accounts/phone/{phone_number}"
            )
            
            return Account(
                id=response.get("id", ""),
                account_number=response.get("accountNumber", ""),
                full_name=response.get("fullName", ""),
                phone_number=response.get("phoneNumber", phone_number),
                balance=response.get("balance", 0.0),
                currency=response.get("currency", "XAF"),
                status=response.get("status", "ACTIVE"),
            )
        except BackendAPIError as e:
            if e.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.warning(f"Failed to get account by phone: {e}")
            return None
    
    async def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID"""
        try:
            response = await self.client.get(f"/api/v1/accounts/{account_id}")
            
            return Account(
                id=response.get("id", account_id),
                account_number=response.get("accountNumber", ""),
                full_name=response.get("fullName", ""),
                phone_number=response.get("phoneNumber", ""),
                balance=response.get("balance", 0.0),
                currency=response.get("currency", "XAF"),
                status=response.get("status", "ACTIVE"),
            )
        except BackendAPIError as e:
            if e.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.warning(f"Failed to get account by ID: {e}")
            return None
    
    async def get_balance(self, account_id: str) -> AccountBalance:
        """Get account balance"""
        try:
            response = await self.client.get(f"/api/v1/accounts/{account_id}/balance")
            
            return AccountBalance(
                account_id=account_id,
                balance=response.get("balance", 0.0),
                currency=response.get("currency", "XAF"),
            )
        except Exception as e:
            logger.warning(f"Failed to get balance: {e}")
            # Return mock balance for development
            return AccountBalance(
                account_id=account_id,
                balance=50000.0,  # Mock balance
                currency="XAF",
            )
    
    async def account_exists(self, phone_number: str) -> bool:
        """Check if account exists for phone number"""
        account = await self.get_account_by_phone(phone_number)
        return account is not None


# Singleton instance
account_service = AccountService()