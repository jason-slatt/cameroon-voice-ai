"""Account-related backend API calls"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

from .client import backend_client, BackendAPIError
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class PhoneCheckResult:
    """Phone number check result"""
    exists: bool
    phone_number: str
    account_id: Optional[str] = None
    message: Optional[str] = None


@dataclass
class Account:
    """Account data model (profile from /api/my-account)"""
    id: str
    account_number: str
    full_name: str
    phone_number: str
    balance: float
    age: Optional[str] = None
    sex: Optional[str] = None
    groupement_id: Optional[int] = None
    groupement_name: Optional[str] = None
    blockchain_address: Optional[str] = None
    currency: str = "XAF"
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None


@dataclass
class AccountBalance:
    """Wallet balance data from /api/get-balance (CELO)"""
    phone_number: str
    balance: float
    currency: str = "CELO"


@dataclass
class TransferResult:
    """Transfer result data"""
    status: str = "SUCCESS"
    reference: Optional[str] = None
    message: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class RecipientInfo:
    """Recipient information from /api/recipient-info"""
    phone_number: str
    full_name: Optional[str] = None
    exists: bool = False
    account_id: Optional[str] = None
    groupement_name: Optional[str] = None


@dataclass
class Groupement:
    """Groupement/Community data from /api/groupements"""
    id: int
    name: str
    token: Optional[str] = None
    description: Optional[str] = None


@dataclass
class PasswordResetResult:
    """Password reset result"""
    success: bool
    message: Optional[str] = None


@dataclass
class PasswordChangeResult:
    """Password change result"""
    success: bool
    message: Optional[str] = None


@dataclass
class WhatsAppLinkResult:
    """WhatsApp link result from /api/link"""
    success: bool
    message: Optional[str] = None
    linked: bool = False


# =============================================================================
# ACCOUNT SERVICE
# =============================================================================

class AccountService:
    """Service for account-related operations"""
    
    def __init__(self):
        self.client = backend_client
    
    # =========================================================================
    # ACCOUNT VERIFICATION
    # =========================================================================
    
    async def check_phone_number(self, phone_number: str) -> PhoneCheckResult:
        """
        Check if a phone number is associated with an account.

        Swagger: POST /api/valid-account
        Body: { "phoneNumber": "string" }
        Returns: TRUE if the number exists, FALSE otherwise.
        """
        logger.info(f"Checking if phone number is valid for account: {phone_number}")

        try:
            raw = await self.client.post(
                "/api/valid-account",
                data={"phoneNumber": phone_number},
            )

            if isinstance(raw, bool):
                exists = raw
                message = None
                account_id = None
            elif isinstance(raw, dict):
                if "valid" in raw:
                    exists = bool(raw["valid"])
                elif "exists" in raw:
                    exists = bool(raw["exists"])
                else:
                    exists = bool(raw)

                account_id = raw.get("accountId")
                message = raw.get("message")
            else:
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
            if e.status_code == 404:
                return PhoneCheckResult(
                    exists=False,
                    phone_number=phone_number,
                    message="Phone number not found",
                )
            return PhoneCheckResult(
                exists=False,
                phone_number=phone_number,
                message=f"Backend error: {e.message}",
            )

        except Exception as e:
            logger.error(f"Failed to check phone number via /api/valid-account: {e}")
            return PhoneCheckResult(
                exists=False,
                phone_number=phone_number,
                message=f"Error checking phone: {str(e)}",
            )

    async def check_account(self, phone_number: str) -> PhoneCheckResult:
        """
        Verify the existence of an account.

        Swagger: POST /api/check-account
        "Vérifier l'existence d'un compte"
        """
        logger.info(f"Checking account existence for: {phone_number}")

        try:
            raw = await self.client.post(
                "/api/check-account",
                data={"phoneNumber": phone_number},
            )

            logger.debug(f"/api/check-account response: {raw}")

            if isinstance(raw, bool):
                exists = raw
                account_id = None
                message = None
            elif isinstance(raw, dict):
                data = raw.get("data", raw)
                exists = bool(
                    data.get("exists")
                    or data.get("valid")
                    or data.get("found")
                    or raw.get("success")
                )
                account_id = data.get("accountId") or data.get("id")
                message = raw.get("message")
            else:
                exists = str(raw).strip().lower() in ("true", "1", "yes")
                account_id = None
                message = None

            return PhoneCheckResult(
                exists=exists,
                phone_number=phone_number,
                account_id=account_id,
                message=message,
            )

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/check-account: {e}")
            return PhoneCheckResult(
                exists=False,
                phone_number=phone_number,
                message=f"Backend error: {e.message}",
            )

        except Exception as e:
            logger.error(f"Failed to check account: {e}")
            return PhoneCheckResult(
                exists=False,
                phone_number=phone_number,
                message=f"Error: {str(e)}",
            )

    # =========================================================================
    # ACCOUNT CREATION & RETRIEVAL
    # =========================================================================

    async def create_account(
        self,
        full_name: str,
        phone_number: str,
        age: str,
        sex: str,
        groupement_id: int,
    ) -> Account:
        """
        Create a new account.

        Swagger: POST /api/account-creation
        "Créer un compte utilisateur"
        """
        logger.info(f"Creating account for {phone_number}")
        
        # Check if phone already exists
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
            if e.status_code == 409 or "already exists" in str(e.message).lower():
                raise ValueError(f"Phone number {phone_number} is already registered.")
            raise
        except Exception as e:
            logger.error(f"Failed to create account: {e}")
            # Mock for development
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
        Get account details.

        Swagger: POST /api/my-account
        "Obtenir les informations du compte"
        Parameter: phoneNumber (query)
        """
        logger.info(f"Fetching account for {phone_number} via /api/my-account")

        try:
            raw = await self.client.post(
                "/api/my-account",
                params={"phoneNumber": phone_number},
            )

            logger.debug(f"/api/my-account response for {phone_number}: {raw}")

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
                    created_at = datetime.fromisoformat(
                        str(data["createdAt"]).replace("Z", "+00:00")
                    )
                except Exception as e:
                    logger.warning(f"Could not parse createdAt: {e}")

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
                blockchain_address=data.get("blockchainAddress"),
                balance=0.0,
                currency="XAF",
                status=str(data.get("status", "ACTIVE")),
                created_at=created_at,
            )

        except BackendAPIError as e:
            msg_lower = str(e.message).lower() if hasattr(e, "message") else str(e).lower()

            if e.status_code in (400, 404) and "compte introuvable" in msg_lower:
                logger.info(f"No account found for {phone_number}")
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

    async def account_exists(self, phone_number: str) -> bool:
        """Check if account exists for phone number"""
        account = await self.get_account_by_phone(phone_number)
        return account is not None

    # =========================================================================
    # RECIPIENT INFO
    # =========================================================================

    async def get_recipient_info(self, phone_number: str) -> RecipientInfo:
        """
        Get recipient information for transfer.

        Swagger: POST /api/recipient-info
        "Récupérer les informations d'un destinataire"
        """
        logger.info(f"Fetching recipient info for: {phone_number}")

        try:
            raw = await self.client.post(
                "/api/recipient-info",
                data={"phoneNumber": phone_number},
            )

            logger.debug(f"/api/recipient-info response: {raw}")

            if not isinstance(raw, dict):
                logger.warning(f"Unexpected response type: {type(raw)}")
                return RecipientInfo(phone_number=phone_number, exists=False)

            data = raw.get("data", raw)

            # Check if recipient exists
            exists = bool(
                data.get("exists")
                or data.get("found")
                or data.get("fullName")
                or raw.get("success")
            )

            groupement = data.get("groupement") or {}

            return RecipientInfo(
                phone_number=data.get("phoneNumber", phone_number),
                full_name=data.get("fullName") or data.get("name"),
                exists=exists,
                account_id=data.get("id") or data.get("accountId"),
                groupement_name=groupement.get("name") or data.get("groupementName"),
            )

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/recipient-info: {e}")
            if e.status_code == 404:
                return RecipientInfo(phone_number=phone_number, exists=False)
            return RecipientInfo(phone_number=phone_number, exists=False)

        except Exception as e:
            logger.error(f"Failed to get recipient info: {e}")
            return RecipientInfo(phone_number=phone_number, exists=False)

    # =========================================================================
    # BALANCE
    # =========================================================================

    async def get_balance(self, phone_number: str) -> AccountBalance:
        """
        Get CELO wallet balance.

        Swagger: POST /api/get-balance
        "Obtenir le solde du wallet"
        """
        logger.info(f"Getting wallet balance for {phone_number}")

        # Get profile first
        account = await self.get_my_account(phone_number)
        if not account:
            logger.warning(f"Cannot get balance: no account profile for {phone_number}")
            return AccountBalance(phone_number=phone_number, balance=0.0)

        payload: Dict[str, Any] = {
            "phoneNumber": account.phone_number,
            "fullName": account.full_name or "",
            "age": account.age or "",
            "sex": account.sex or "",
            "groupement_id": account.groupement_id or 0,
            "blockchainAddress": account.blockchain_address or "",
        }

        try:
            raw = await self.client.post(
                "/api/get-balance",
                data=payload,
            )

            logger.debug(f"/api/get-balance response for {phone_number}: {raw}")

            if not isinstance(raw, dict):
                logger.error(f"Unexpected /api/get-balance response type: {type(raw)}")
                return AccountBalance(phone_number=phone_number, balance=0.0)

            data = raw.get("data", raw)

            balance_raw = (
                data.get("balance")
                or data.get("celoBalance")
                or data.get("walletBalance")
            )

            try:
                balance = float(str(balance_raw)) if balance_raw is not None else 0.0
            except Exception as e:
                logger.warning(f"Could not parse balance value {balance_raw}: {e}")
                balance = 0.0

            return AccountBalance(
                phone_number=phone_number,
                balance=balance,
                currency="CELO",
            )

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/get-balance: {e}")
            return AccountBalance(phone_number=phone_number, balance=0.0)

        except Exception as e:
            logger.error(f"Failed to get balance for {phone_number}: {e}")
            return AccountBalance(phone_number=phone_number, balance=0.0)

    # =========================================================================
    # TRANSFER
    # =========================================================================

    async def transfer(
        self,
        phone_number: str,
        receiver_phone_number: str,
        pin: str,
        amount: str | float,
    ) -> TransferResult:
        """
        Transfer tokens to a receiver.

        Swagger: POST /api/transfer
        "Transférer des tokens"
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
            import uuid
            return TransferResult(
                status="MOCK_SUCCESS",
                reference=f"MOCK-{uuid.uuid4().hex[:10].upper()}",
                message="Mock transfer executed (backend unreachable).",
                raw=None,
            )

    # =========================================================================
    # PASSWORD MANAGEMENT
    # =========================================================================

    async def reset_password(self, phone_number: str) -> PasswordResetResult:
        """
        Reset user password.

        Swagger: POST /api/reset-password
        "Réinitialiser le mot de passe"
        """
        logger.info(f"Resetting password for: {phone_number}")

        try:
            raw = await self.client.post(
                "/api/reset-password",
                data={"phoneNumber": phone_number},
            )

            logger.debug(f"/api/reset-password response: {raw}")

            if isinstance(raw, dict):
                success = bool(raw.get("success", True))
                message = raw.get("message")
            else:
                success = True
                message = None

            return PasswordResetResult(
                success=success,
                message=message,
            )

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/reset-password: {e}")
            return PasswordResetResult(
                success=False,
                message=f"Error: {e.message}",
            )

        except Exception as e:
            logger.error(f"Failed to reset password: {e}")
            return PasswordResetResult(
                success=False,
                message=f"Error: {str(e)}",
            )

    async def change_password(
        self,
        phone_number: str,
        old_password: str,
        new_password: str,
    ) -> PasswordChangeResult:
        """
        Change user password.

        Swagger: POST /api/change-password
        "Modifier le mot de passe"
        """
        logger.info(f"Changing password for: {phone_number}")

        try:
            raw = await self.client.post(
                "/api/change-password",
                data={
                    "phoneNumber": phone_number,
                    "oldPassword": old_password,
                    "newPassword": new_password,
                },
            )

            logger.debug(f"/api/change-password response: {raw}")

            if isinstance(raw, dict):
                success = bool(raw.get("success", True))
                message = raw.get("message")
            else:
                success = True
                message = None

            return PasswordChangeResult(
                success=success,
                message=message,
            )

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/change-password: {e}")
            return PasswordChangeResult(
                success=False,
                message=f"Error: {e.message}",
            )

        except Exception as e:
            logger.error(f"Failed to change password: {e}")
            return PasswordChangeResult(
                success=False,
                message=f"Error: {str(e)}",
            )

    # =========================================================================
    # WHATSAPP LINKING
    # =========================================================================

    async def link_whatsapp(
        self,
        phone_number: str,
        whatsapp_number: Optional[str] = None,
    ) -> WhatsAppLinkResult:
        """
        Link WhatsApp account.

        Swagger: POST /api/link
        "Lier le compte WhatsApp"
        """
        logger.info(f"Linking WhatsApp for: {phone_number}")

        try:
            payload: Dict[str, Any] = {"phoneNumber": phone_number}
            if whatsapp_number:
                payload["whatsappNumber"] = whatsapp_number

            raw = await self.client.post(
                "/api/link",
                data=payload,
            )

            logger.debug(f"/api/link response: {raw}")

            if isinstance(raw, dict):
                success = bool(raw.get("success", True))
                message = raw.get("message")
                linked = bool(raw.get("linked", success))
            else:
                success = True
                message = None
                linked = True

            return WhatsAppLinkResult(
                success=success,
                message=message,
                linked=linked,
            )

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/link: {e}")
            return WhatsAppLinkResult(
                success=False,
                message=f"Error: {e.message}",
                linked=False,
            )

        except Exception as e:
            logger.error(f"Failed to link WhatsApp: {e}")
            return WhatsAppLinkResult(
                success=False,
                message=f"Error: {str(e)}",
                linked=False,
            )

    # =========================================================================
    # GROUPEMENTS
    # =========================================================================

    async def get_groupements(self) -> List[Groupement]:
        """
        Get list of all groupements/communities.

        Swagger: GET /api/groupements
        "Liste tous les Groupements/Communautés"
        """
        logger.info("Fetching all groupements")

        try:
            raw = await self.client.get("/api/groupements")

            logger.debug(f"/api/groupements response: {raw}")

            # Determine the list of items
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, dict):
                items = (
                    raw.get("data")
                    or raw.get("groupements")
                    or raw.get("items")
                    or []
                )
                if not isinstance(items, list):
                    items = []
            else:
                logger.warning(f"Unexpected response shape: {type(raw)}")
                return []

            groupements: List[Groupement] = []

            for g in items:
                try:
                    groupements.append(Groupement(
                        id=int(g.get("id", 0)),
                        name=g.get("name", ""),
                        token=g.get("token"),
                        description=g.get("description"),
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing groupement item {g}: {e}")
                    continue

            return groupements

        except BackendAPIError as e:
            logger.error(f"Backend error from /api/groupements: {e}")
            return []

        except Exception as e:
            logger.error(f"Failed to fetch groupements: {e}")
            return []


# Singleton instance
account_service = AccountService()