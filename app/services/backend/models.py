"""Backend API data models"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ============ Account Models ============

class CreateAccountRequest(BaseModel):
    """Request to create a new account"""
    full_name: str = Field(..., alias="fullName")
    phone_number: str = Field(..., alias="phoneNumber")
    
    class Config:
        populate_by_name = True


class AccountResponse(BaseModel):
    """Account information from backend"""
    id: str
    account_number: str = Field(..., alias="accountNumber")
    full_name: str = Field(..., alias="fullName")
    phone_number: str = Field(..., alias="phoneNumber")
    balance: float
    currency: str = "XAF"
    status: AccountStatus
    created_at: datetime = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True


class AccountBalanceResponse(BaseModel):
    """Account balance response"""
    account_id: str = Field(..., alias="accountId")
    balance: float
    currency: str = "XAF"
    last_updated: datetime = Field(..., alias="lastUpdated")
    
    class Config:
        populate_by_name = True


# ============ Transaction Models ============

class CreateWithdrawalRequest(BaseModel):
    """Request to create a withdrawal"""
    account_id: str = Field(..., alias="accountId")
    amount: float
    description: Optional[str] = None
    
    class Config:
        populate_by_name = True


class CreateDepositRequest(BaseModel):
    """Request to create a deposit"""
    account_id: str = Field(..., alias="accountId")
    amount: float
    description: Optional[str] = None
    
    class Config:
        populate_by_name = True


class TransactionResponse(BaseModel):
    """Transaction information from backend"""
    id: str
    account_id: str = Field(..., alias="accountId")
    type: TransactionType
    amount: float
    currency: str = "XAF"
    status: TransactionStatus
    description: Optional[str] = None
    reference: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    
    class Config:
        populate_by_name = True


class TransactionListResponse(BaseModel):
    """List of transactions"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    
    class Config:
        populate_by_name = True