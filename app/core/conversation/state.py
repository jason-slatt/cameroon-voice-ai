# app/core/conversation/state.py
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
    DASHBOARD = "dashboard"
    PASSWORD_RESET = "password_reset"     
    PASSWORD_CHANGE = "password_change"   
    WHATSAPP_LINK = "whatsapp_link"        


class FlowStep(str, Enum):
    INIT = "init"
    CONFIRM = "confirm"
    COMPLETE = "complete"
    
    # Registration steps
    ASK_NAME = "ask_name"
    ASK_AGE = "ask_age"
    ASK_SEX = "ask_sex"
    ASK_GROUPEMENT = "ask_groupement"
    
    # Transaction steps
    ASK_AMOUNT = "ask_amount"
    ASK_RECEIVER = "ask_receiver"
    ASK_PIN = "ask_pin"

    # Dashboard steps
    ASK_DASHBOARD_ACTION = "ask_dashboard_action"

    # Password change steps
    ASK_OLD_PASSWORD = "ask_old_password"     
    ASK_NEW_PASSWORD = "ask_new_password"      
    CONFIRM_PASSWORD = "confirm_password"      

    # WhatsApp linking steps
    ASK_WHATSAPP_CHOICE = "ask_whatsapp_choice"    
    ASK_WHATSAPP_NUMBER = "ask_whatsapp_number"   


@dataclass
class ConversationState:
    """State of a conversation session"""
    conversation_id: str
    user_id: str
    phone_number: str

    flow_type: FlowType = FlowType.NONE
    flow_step: Optional[FlowStep] = None

    collected_data: Dict[str, Any] = field(default_factory=dict)

    account_id: Optional[str] = None
    account_balance: Optional[float] = None

    phone_checked: bool = False
    account_exists: bool = False

    lang: Optional[str] = None  # 'en' or 'fr'

    attempts: int = 0
    max_attempts: int = 3

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def reset_flow(self):
        self.flow_type = FlowType.NONE
        self.flow_step = None
        self.collected_data = {}
        self.attempts = 0
        self.updated_at = datetime.utcnow()

    def start_flow(self, flow_type: FlowType, step: FlowStep = FlowStep.INIT):
        self.flow_type = flow_type
        self.flow_step = step
        self.collected_data = {}
        self.attempts = 0
        self.updated_at = datetime.utcnow()

    def next_step(self, step: FlowStep):
        self.flow_step = step
        self.attempts = 0
        self.updated_at = datetime.utcnow()

    def add_data(self, key: str, value: Any):
        self.collected_data[key] = value
        self.updated_at = datetime.utcnow()

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.collected_data.get(key, default)

    def is_in_flow(self) -> bool:
        return self.flow_type != FlowType.NONE

    def increment_attempts(self) -> bool:
        self.attempts += 1
        self.updated_at = datetime.utcnow()
        return self.attempts >= self.max_attempts

    def mark_phone_checked(self, exists: bool):
        self.phone_checked = True
        self.account_exists = exists
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
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
            "lang": self.lang,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
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
            lang=data.get("lang"),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 3),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )