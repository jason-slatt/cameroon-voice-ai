# src/services/banking/validators.py
"""
Banking validation rules
"""
import re

from src.core.logging import logger


class BankingValidator:
    """Validate banking operations and data"""

    # Limits
    MIN_TRANSFER_AMOUNT = 0.01
    MAX_TRANSFER_AMOUNT = 50000.00
    MAX_DAILY_TRANSFER = 10000.00

    def validate_amount(self, amount: float | None) -> bool:
        """Validate transfer amount"""
        if amount is None:
            logger.warning("Amount is None")
            return False

        if amount < self.MIN_TRANSFER_AMOUNT:
            logger.warning("Amount too small: %s", amount)
            return False

        if amount > self.MAX_TRANSFER_AMOUNT:
            logger.warning("Amount too large: %s", amount)
            return False

        return True

    def validate_iban(self, iban: str | None) -> bool:
        """Validate IBAN format (French)"""
        if not iban:
            return False

        sanitized_iban = iban.replace(" ", "").upper()

        pattern = r"^FR\d{2}[A-Z0-9]{23}$"

        if not re.match(pattern, sanitized_iban):
            logger.warning("Invalid IBAN format: %s", sanitized_iban)
            return False

        # TODO: Add checksum validation for production
        return True

    def check_daily_limit(
        self,
        user_id: str,
        new_amount: float,
        today_total: float = 0,
    ) -> bool:
        """Check if transfer respects daily limit"""
        total = today_total + new_amount

        if total > self.MAX_DAILY_TRANSFER:
            logger.warning(
                "Daily limit exceeded for %s: %s EUR > %s EUR",
                user_id,
                total,
                self.MAX_DAILY_TRANSFER,
            )
            return False

        return True
