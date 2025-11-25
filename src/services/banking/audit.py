# src/services/banking/audit.py
"""
Audit logging for compliance and security
All banking operations must be logged
"""
from typing import Dict, Any, List
from datetime import datetime
import json
from pathlib import Path

from src.core.logging import logger
from src.core.config import settings


class AuditLogger:
    """
    Comprehensive audit logging for banking operations
    Ensures compliance with banking regulations
    """

    def __init__(self) -> None:
        # Allow override from settings, fall back to local path
        base_dir = getattr(settings, "AUDIT_LOG_DIR", "./logs/audit")
        self.audit_dir = Path(base_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Separate log files for different types
        self.command_log = self.audit_dir / "commands.jsonl"
        self.transaction_log = self.audit_dir / "transactions.jsonl"
        self.security_log = self.audit_dir / "security.jsonl"
        self.error_log = self.audit_dir / "errors.jsonl"

    async def log_command(
        self,
        user_id: str,
        intent: str,
        entities: Dict[str, Any],
        timestamp: datetime,
        **metadata: Any,
    ) -> None:
        """
        Log user command/request

        Records:
        - Who made the request (user_id)
        - What they requested (intent + entities)
        - When (timestamp)
        - Additional context
        """

        log_entry: Dict[str, Any] = {
            "log_type": "command",
            "user_id": user_id,
            "intent": intent,
            "entities": entities,
            "timestamp": timestamp.isoformat(),
            **metadata,
        }

        self._write_log(self.command_log, log_entry)
        logger.info("📝 Audit: Command logged - %s by %s", intent, user_id)

    async def log_result(
        self,
        user_id: str,
        intent: str,
        result: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Log command result/outcome"""

        log_entry: Dict[str, Any] = {
            "log_type": "result",
            "user_id": user_id,
            "intent": intent,
            "status": result.get("status"),
            "timestamp": timestamp.isoformat(),
            "response_preview": (result.get("response") or "")[:200],
        }

        # If transaction, log to transaction log
        if "transaction_id" in result:
            await self.log_transaction(
                user_id=user_id,
                transaction_id=result["transaction_id"],
                intent=intent,
                amount=result.get("amount"),
                status=result.get("status"),
                timestamp=timestamp,
            )

        self._write_log(self.command_log, log_entry)

    async def log_transaction(
        self,
        user_id: str,
        transaction_id: str,
        intent: str,
        amount: float | None = None,
        status: str | None = None,
        timestamp: datetime | None = None,
        **details: Any,
    ) -> None:
        """
        Log financial transaction
        Critical for compliance and fraud investigation
        """

        safe_timestamp = timestamp or datetime.utcnow()

        log_entry: Dict[str, Any] = {
            "log_type": "transaction",
            "user_id": user_id,
            "transaction_id": transaction_id,
            "intent": intent,
            "amount": amount,
            "status": status,
            "timestamp": safe_timestamp.isoformat(),
            **details,
        }

        self._write_log(self.transaction_log, log_entry)
        logger.info("💰 Audit: Transaction logged - %s", transaction_id)

    async def log_security_event(
        self,
        user_id: str,
        event_type: str,
        details: Dict[str, Any],
        risk_level: str = "info",
    ) -> None:
        """
        Log security events (OTP, 2FA, fraud detection, etc.)
        """

        log_entry: Dict[str, Any] = {
            "log_type": "security",
            "user_id": user_id,
            "event_type": event_type,
            "risk_level": risk_level,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._write_log(self.security_log, log_entry)

        if risk_level in {"high", "critical"}:
            logger.warning("🚨 Security event: %s - %s", event_type, user_id)

    async def log_error(
        self,
        user_id: str,
        intent: str,
        error: str,
        timestamp: datetime,
        **context: Any,
    ) -> None:
        """Log errors and failures"""

        log_entry: Dict[str, Any] = {
            "log_type": "error",
            "user_id": user_id,
            "intent": intent,
            "error": error,
            "timestamp": timestamp.isoformat(),
            **context,
        }

        self._write_log(self.error_log, log_entry)
        logger.error("❌ Audit: Error logged - %s - %s", intent, error)

    def _write_log(self, log_file: Path, entry: Dict[str, Any]) -> None:
        """Write log entry to JSONL file"""
        try:
            with open(log_file, "a", encoding="utf-8") as file_handle:
                file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write audit log: %s", exc)

    async def get_user_audit_trail(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for a user
        Used for compliance reviews and investigations
        Returns the most recent `limit` entries.
        """

        audit_trail: List[Dict[str, Any]] = []

        if self.command_log.exists():
            with open(self.command_log, "r", encoding="utf-8") as file_handle:
                for line in file_handle:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if entry.get("user_id") == user_id:
                        audit_trail.append(entry)

        # Return latest `limit` entries
        if limit <= 0:
            return []

        return audit_trail[-limit:]
