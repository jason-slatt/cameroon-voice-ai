# app/core/conversation/state.py
"""Conversation state management"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class FlowType(str, Enum):
    NONE = "none"
    ACCOUNT_CREATION = "account_creation"
    WITHDRAWAL = "withdrawal"
    TOPUP = "topup"
    BALANCE_INQUIRY = "balance_inquiry"
    TRANSACTION_HISTORY = "transaction_history"
    TRANSFER = "transfer" 


class FlowStep(str, Enum):
    # Common
    INIT = "init"
    CONFIRM = "confirm"
    COMPLETE = "complete"

    # Account creation
    ASK_NAME = "ask_name"
    ASK_AGE = "ask_age"
    ASK_SEX = "ask_sex"
    ASK_GROUPEMENT = "ask_groupement"

    # Transactions
    ASK_AMOUNT = "ask_amount"

    #transfer
    ASK_RECEIVER = "ask_receiver"
    ASK_PIN = "ask_pin"


@dataclass
class ConversationState:
    """State of a conversation session"""
    conversation_id: str
    user_id: str
    phone_number: str

    # Flow state
    flow_type: FlowType = FlowType.NONE
    flow_step: Optional[FlowStep] = None

    # Collected data (name, age, sex, groupement_id, etc.)
    collected_data: Dict[str, Any] = field(default_factory=dict)

    # Account info (loaded from backend)
    account_id: Optional[str] = None
    account_balance: Optional[float] = None

    # GLOBAL PHONE CHECK FLAGS
    phone_checked: bool = False        # have we already called check-phone-number/api/my-account?
    account_exists: bool = False       # does this phone already have an account?

    # Retry tracking
    attempts: int = 0
    max_attempts: int = 3

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # ---------- Flow Management ----------

    def reset_flow(self):
        """Reset only the current flow, keep phone/account flags."""
        self.flow_type = FlowType.NONE
        self.flow_step = None
        self.collected_data = {}
        self.attempts = 0
        self.updated_at = datetime.utcnow()

    def start_flow(self, flow_type: FlowType, step: FlowStep = FlowStep.INIT):
        """Start a new flow."""
        self.flow_type = flow_type
        self.flow_step = step
        self.collected_data = {}
        self.attempts = 0
        self.updated_at = datetime.utcnow()

    def next_step(self, step: FlowStep):
        """Move to the next step in the flow."""
        self.flow_step = step
        self.attempts = 0
        self.updated_at = datetime.utcnow()

    # ---------- Data Management ----------

    def add_data(self, key: str, value: Any):
        """Store collected data in the conversation."""
        self.collected_data[key] = value
        self.updated_at = datetime.utcnow()

    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve collected data."""
        return self.collected_data.get(key, default)

    # ---------- Flow / Attempts ----------

    def is_in_flow(self) -> bool:
        """Check if currently in an active flow."""
        return self.flow_type != FlowType.NONE

    def increment_attempts(self) -> bool:
        """
        Increment attempts, return True if max attempts reached.
        """
        self.attempts += 1
        self.updated_at = datetime.utcnow()
        return self.attempts >= self.max_attempts

    # ---------- Phone / Account Flags ----------

    def mark_phone_checked(self, exists: bool):
        """
        Mark that we've checked this phone number and whether an account exists.
        """
        self.phone_checked = True
        self.account_exists = exists
        self.updated_at = datetime.utcnow()

    # ---------- Serialization ----------

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "phone_number": self.phone_number,
            "flow_type": self.flow_type.value,
            "flow_step": self.flow_step.value if self.flow_step else None,
            "collected_data": self.collected_data,
            "account_id": self.account_id,
            "account_balance": self.account_balance,
            "phone_checked": self.phone_checked,
            "account_exists": self.account_exists,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """Rebuild ConversationState from stored dict."""
        return cls(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            phone_number=data["phone_number"],
            flow_type=FlowType(data.get("flow_type", "none")),
            flow_step=FlowStep(data["flow_step"]) if data.get("flow_step") else None,
            collected_data=data.get("collected_data", {}),
            account_id=data.get("account_id"),
            account_balance=data.get("account_balance"),
            phone_checked=data.get("phone_checked", False),
            account_exists=data.get("account_exists", False),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 3),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )