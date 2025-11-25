"""Conversation state management"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum, auto


class FlowType(str, Enum):
    NONE = "none"
    ACCOUNT_CREATION = "account_creation"
    WITHDRAWAL = "withdrawal"
    TOPUP = "topup"
    BALANCE_INQUIRY = "balance_inquiry"
    TRANSACTION_HISTORY = "transaction_history"


class FlowStep(str, Enum):
    # Common
    INIT = "init"
    CONFIRM = "confirm"
    COMPLETE = "complete"
    
    # Account creation
    ASK_NAME = "ask_name"
    
    # Transactions
    ASK_AMOUNT = "ask_amount"


@dataclass
class ConversationState:
    """State of a conversation session"""
    conversation_id: str
    user_id: str
    phone_number: str
    
    # Flow state
    flow_type: FlowType = FlowType.NONE
    flow_step: Optional[FlowStep] = None
    
    # Collected data
    collected_data: Dict[str, Any] = field(default_factory=dict)
    
    # Account info (loaded from backend)
    account_id: Optional[str] = None
    account_balance: Optional[float] = None
    
    # Retry tracking
    attempts: int = 0
    max_attempts: int = 3
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def reset_flow(self):
        """Reset the current flow"""
        self.flow_type = FlowType.NONE
        self.flow_step = None
        self.collected_data = {}
        self.attempts = 0
        self.updated_at = datetime.utcnow()
    
    def start_flow(self, flow_type: FlowType, step: FlowStep = FlowStep.INIT):
        """Start a new flow"""
        self.flow_type = flow_type
        self.flow_step = step
        self.collected_data = {}
        self.attempts = 0
        self.updated_at = datetime.utcnow()
    
    def next_step(self, step: FlowStep):
        """Move to the next step"""
        self.flow_step = step
        self.attempts = 0
        self.updated_at = datetime.utcnow()
    
    def add_data(self, key: str, value: Any):
        """Add collected data"""
        self.collected_data[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get collected data"""
        return self.collected_data.get(key, default)
    
    def is_in_flow(self) -> bool:
        """Check if currently in a flow"""
        return self.flow_type != FlowType.NONE
    
    def increment_attempts(self) -> bool:
        """Increment attempts, return True if max reached"""
        self.attempts += 1
        self.updated_at = datetime.utcnow()
        return self.attempts >= self.max_attempts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "phone_number": self.phone_number,
            "flow_type": self.flow_type.value,
            "flow_step": self.flow_step.value if self.flow_step else None,
            "collected_data": self.collected_data,
            "account_id": self.account_id,
            "account_balance": self.account_balance,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """Create from dictionary"""
        return cls(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            phone_number=data["phone_number"],
            flow_type=FlowType(data.get("flow_type", "none")),
            flow_step=FlowStep(data["flow_step"]) if data.get("flow_step") else None,
            collected_data=data.get("collected_data", {}),
            account_id=data.get("account_id"),
            account_balance=data.get("account_balance"),
            attempts=data.get("attempts", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )