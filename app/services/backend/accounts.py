"""Account-related backend API calls"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from .client import backend_client, BackendAPIError
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PhoneCheckResult:
    """Phone number check result"""
    exists: bool
    phone_number: str
    account_id: Optional[str] = None
    message: Optional[str] = None


@dataclass
class Account:
    """Account data model"""
    id: str
    account_number: str
    full_name: str
    phone_number: str
    balance: float
    age: Optional[str] = None
    sex: Optional[str] = None
    groupement_id: Optional[int] = None
    groupement_name: Optional[str] = None
    currency: str = "XAF"
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None


@dataclass
class AccountBalance:
    """Account balance data"""
    account_id: str
    balance: float
    currency: str = "XAF"

@dataclass
class TransferResult:
    """Transfer result data"""
    status: str = "SUCCESS"
    reference: Optional[str] = None
    message: Optional[str] = None
    raw: Optional[dict] = None



class AccountService:
    """Service for account-related operations"""
    
    def __init__(self):
        self.client = backend_client
    
    async def check_phone_number(self, phone_number: str) -> PhoneCheckResult:
        """
        Check if a phone number is associated with an account.

        Uses /api/valid-account

        API: POST /api/valid-account
        Body: { "phoneNumber": "string" }
        Returns: TRUE if the number exists, FALSE otherwise.
        """
        logger.info(f"Checking if phone number is valid for account: {phone_number}")

        try:
            # Call the backend
            raw = await self.client.post(
                "/api/valid-account",
                data={"phoneNumber": phone_number},
            )

            # /api/valid-account is documented as returning TRUE/FALSE.
            # Our BackendClient.post() returns whatever .json() gives:
            # - bool (True/False) if response is plain JSON `true`/`false`
            # - or possibly a dict if backend wraps it.
            if isinstance(raw, bool):
                exists = raw
                message = None
                account_id = None
            elif isinstance(raw, dict):
                # Be defensive: support several possible shapes
                if "valid" in raw:
                    exists = bool(raw["valid"])
                elif "exists" in raw:
                    exists = bool(raw["exists"])
                else:
                    # If no key, fallback to truthiness
                    exists = bool(raw)

                account_id = raw.get("accountId")
                message   = raw.get("message")
            else:
                # Fallback: try to interpret as string
                text = str(raw).strip().lower()
                exists = text in ("true", "1", "yes")
                account_id = None
                message = None

            logger.info(f"/api/valid-account for {phone_number}: exists={exists}")

            return PhoneCheckResult(
                exists=exists,
                phone_number=phone_number,
                account_id=account_id,
                message=message,
            )

        except BackendAPIError as e:
            logger.error(f"Error calling /api/valid-account: {e}")
            # If backend says 404 or similar, treat as not existing
            if e.status_code == 404:
                return PhoneCheckResult(
                    exists=False,
                    phone_number=phone_number,
                    message="Phone number not found",
                )
            # For other backend errors, default to "not exists" to avoid blocking flows
            return PhoneCheckResult(
                exists=False,
                phone_number=phone_number,
                message=f"Backend error: {e.message}",
            )

        except Exception as e:
            logger.error(f"Failed to check phone number via /api/valid-account: {e}")
            # Fail-open: treat as not existing; you can change this to True if you prefer fail-closed
            return PhoneCheckResult(
                exists=False,
                phone_number=phone_number,
                message=f"Error checking phone: {str(e)}",
            )
    async def create_account(
        self,
        full_name: str,
        phone_number: str,
        age: str,
        sex: str,
        groupement_id: int,
    ) -> Account:
        """Create a new account"""
        logger.info(f"Creating account for {phone_number}")
        
        # CHECK PHONE NUMBER FIRST (additional safety)
        phone_check = await self.check_phone_number(phone_number)
        if phone_check.exists:
            raise ValueError(
                f"An account with phone number {phone_number} already exists. "
                "Please use a different phone number or contact support."
            )
        
        try:
            response = await self.client.post(
                "/api/account-creation",
                data={
                    "phoneNumber": phone_number,
                    "fullName": full_name,
                    "age": age,
                    "sex": sex,
                    "groupement_id": groupement_id,
                },
            )
            
            return Account(
                id=response.get("id", ""),
                account_number=response.get("accountNumber", ""),
                full_name=response.get("fullName", full_name),
                phone_number=response.get("phoneNumber", phone_number),
                age=age,
                sex=sex,
                groupement_id=groupement_id,
                balance=response.get("balance", 0.0),
                currency=response.get("currency", "XAF"),
                status=response.get("status", "ACTIVE"),
            )
        except BackendAPIError as e:
            # Check if error is due to duplicate phone
            if e.status_code == 409 or "already exists" in str(e.message).lower():
                raise ValueError(f"Phone number {phone_number} is already registered.")
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
                age=age,
                sex=sex,
                groupement_id=groupement_id,
                balance=0.0,
            )
    
    async def get_my_account(self, phone_number: str) -> Optional[Account]:
        """
        Get account details using the /api/my-account endpoint.

        Swagger:
        POST /api/my-account
        Parameter: phoneNumber (query)
        """
        logger.info(f"Fetching account for {phone_number} via /api/my-account")

        try:
            raw = await self.client.post(
                "/api/my-account",
                params={"phoneNumber": phone_number},  # query param
            )

            logger.info(f"/api/my-account response for {phone_number}: {raw}")

            # Expecting shape: {"code": ..., "message": "...", "data": {...}, "success": ...}
            if not isinstance(raw, dict):
                logger.error(f"Unexpected /api/my-account response type: {type(raw)}")
                return None

            data = raw.get("data")
            if not isinstance(data, dict):
                logger.info(f"No 'data' field in /api/my-account for {phone_number}")
                return None

            groupement = data.get("groupement") or {}
            groupement_id = groupement.get("id")
            groupement_name = groupement.get("name")

            created_at = None
            if data.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(data["createdAt"])
                except Exception as e:
                    logger.warning(f"Could not parse createdAt: {e}")

            # BAFOKA doesn't show an explicit "accountNumber" here, so we can 
            # use the internal id as a surrogate account number string.
            account_id = str(data.get("id", ""))

            return Account(
                id=account_id,
                account_number=account_id,
                full_name=data.get("fullName", ""),
                phone_number=data.get("phoneNumber", phone_number),
                age=data.get("age"),
                sex=data.get("sex"),
                groupement_id=groupement_id,
                groupement_name=groupement_name,
                balance=0.0,  # /api/my-account doesn't include balance
                currency="XAF",
                status=str(data.get("status", "ACTIVE")),
                created_at=created_at,
            )

        except BackendAPIError as e:
            if e.status_code == 404:
                logger.info(f"No account found for {phone_number} (404 from /api/my-account)")
                return None
            logger.error(f"Error fetching account from /api/my-account: {e}")
            raise

        except Exception as e:
            logger.error(f"Failed to get account for {phone_number}: {e}")
            return None
        
    async def get_account_by_phone(self, phone_number: str) -> Optional[Account]:
        """Get account by phone number (alias for get_my_account)"""
        return await self.get_my_account(phone_number)
    
    async def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID"""
        try:
            response = await self.client.get(f"/api/accounts/{account_id}")
            
            return Account(
                id=response.get("id", account_id),
                account_number=response.get("accountNumber", ""),
                full_name=response.get("fullName", ""),
                phone_number=response.get("phoneNumber", ""),
                age=response.get("age"),
                sex=response.get("sex"),
                groupement_id=response.get("groupement_id"),
                groupement_name=response.get("groupementName"),
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
            response = await self.client.get(f"/api/accounts/{account_id}/balance")
            
            return AccountBalance(
                account_id=account_id,
                balance=response.get("balance", 0.0),
                currency=response.get("currency", "XAF"),
            )
        except Exception as e:
            logger.warning(f"Failed to get balance: {e}")
            return AccountBalance(
                account_id=account_id,
                balance=50000.0,
                currency="XAF",
            )
    
    async def account_exists(self, phone_number: str) -> bool:
        """Check if account exists for phone number"""
        account = await self.get_account_by_phone(phone_number)
        return account is not None
     

    async def transfer(
        self,
        phone_number: str,
        receiver_phone_number: str,
        pin: str,
        amount: str | float,
    ) -> TransferResult:
        """
        Transfer tokens to a receiver phone number.
        """
        logger.info(f"Transferring {amount} from {phone_number} to {receiver_phone_number}")

        payload = {
            "phoneNumber": phone_number,
            "receiverPhoneNumber": receiver_phone_number,
            "pin": pin,
            "amount": str(amount), 
        }

        try:
            response = await self.client.post("/api/transfer", data=payload)

            return TransferResult(
                status=response.get("status", "SUCCESS"),
                reference=response.get("reference") or response.get("txHash") or response.get("transactionHash"),
                message=response.get("message"),
                raw=response,
            )

        except BackendAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to transfer: {e}")
            # Dev fallback (mock)
            import uuid
            return TransferResult(
                status="MOCK_SUCCESS",
                reference=f"MOCK-{uuid.uuid4().hex[:10].upper()}",
                message="Mock transfer executed (backend unreachable).",
                raw=None,
            )


# Singleton instance
account_service = AccountService()