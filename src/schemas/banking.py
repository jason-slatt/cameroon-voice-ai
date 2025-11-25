# src/schemas/banking.py
"""
Pydantic schemas for banking operations
"""
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class BankingCommand(BaseModel):
    """Validated banking command"""

    intent: str
    entities: Dict[str, Any]
    confidence: float
    user_id: str
    conversation_id: str


class BankingResponse(BaseModel):
    """Banking operation response"""

    response: str
    status: str  # success, pending, failed
    requires_otp: bool = False
    transaction_id: Optional[str] = None
    otp_code: Optional[str] = None  # Remove in production
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransactionRecord(BaseModel):
    """Transaction record for database"""

    transaction_id: str
    user_id: str
    intent: str
    amount: Optional[float] = None
    currency: str = "EUR"
    beneficiary: Optional[str] = None
    status: str
    risk_score: int
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditLog(BaseModel):
    """Audit log entry"""

    log_id: str
    log_type: str  # command, transaction, security, error
    user_id: str
    timestamp: datetime
    details: Dict[str, Any]
