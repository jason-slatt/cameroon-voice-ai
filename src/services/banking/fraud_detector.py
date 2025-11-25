# src/services/banking/fraud_detector.py
"""
Fraud detection and risk assessment
"""
from typing import Dict
from datetime import datetime, timedelta
import hashlib

from src.core.logging import logger


class FraudDetector:
    """
    Detect suspicious banking activities
    Uses rule-based and pattern analysis
    """

    # Risk thresholds
    HIGH_AMOUNT_THRESHOLD = 1000.00
    VELOCITY_LIMIT = 3  # Max transfers in window
    VELOCITY_WINDOW_MINUTES = 10

    # Risk scores (0-100)
    RISK_LOW = 0
    RISK_MEDIUM = 50
    RISK_HIGH = 75
    RISK_CRITICAL = 90

    # Internal constants
    VELOCITY_HIGH_RISK_POINTS = 40
    VELOCITY_MEDIUM_RISK_POINTS = 20
    UNUSUAL_TIME_HIGH_RISK_POINTS = 15
    UNUSUAL_TIME_MEDIUM_RISK_POINTS = 10
    ROUND_AMOUNT_MIN = 500
    ROUND_AMOUNT_POINTS = 10
    NEW_BENEFICIARY_POINTS = 20
    HIGH_AMOUNT_POINTS = 30
    VELOCITY_KEY_TEMPLATE = "fraud:velocity:{user_id}"
    BENEFICIARIES_KEY_TEMPLATE = "fraud:beneficiaries:{user_id}"
    ALERTS_KEY_TEMPLATE = "fraud:alerts:{user_id}"
    VELOCITY_EXPIRY_SECONDS = 3600
    BENEFICIARY_EXPIRY_SECONDS = 86400 * 90
    ALERT_EXPIRY_SECONDS = 86400 * 30

    def __init__(self) -> None:
        self.redis = None

    async def _get_redis(self):
        """Get Redis connection"""
        if self.redis is None:
            from src.core.dependencies import get_redis

            self.redis = await get_redis()
        return self.redis

    async def assess_risk(
        self,
        user_id: str,
        amount: float,
        beneficiary: str,
        conversation_id: str,  # noqa: ARG002  (reserved for future patterns)
        **context: Dict,
    ) -> int:
        """
        Calculate risk score for transaction

        Returns:
            Risk score (0-100)
            0-25: Low risk
            26-50: Medium risk
            51-75: High risk
            76-100: Critical risk
        """

        risk_score = self.RISK_LOW
        risk_factors: list[str] = []

        # FACTOR 1: Large amount
        if amount > self.HIGH_AMOUNT_THRESHOLD:
            risk_score += self.HIGH_AMOUNT_POINTS
            risk_factors.append(f"High amount: {amount}")

        # FACTOR 2: Velocity check (multiple transfers quickly)
        velocity_risk = await self._check_velocity(user_id)
        risk_score += velocity_risk
        if velocity_risk > 0:
            risk_factors.append(f"High velocity: {velocity_risk} points")

        # FACTOR 3: New beneficiary
        is_new_beneficiary = await self._is_new_beneficiary(user_id, beneficiary)
        if is_new_beneficiary:
            risk_score += self.NEW_BENEFICIARY_POINTS
            risk_factors.append("New beneficiary")

        # FACTOR 4: Unusual time (e.g., 2 AM transfers)
        time_risk = self._check_unusual_time()
        risk_score += time_risk
        if time_risk > 0:
            risk_factors.append("Unusual time")

        # FACTOR 5: Round numbers (common in fraud)
        if amount % 100 == 0 and amount >= self.ROUND_AMOUNT_MIN:
            risk_score += self.ROUND_AMOUNT_POINTS
            risk_factors.append("Round amount")

        # Cap at 100
        risk_score = min(risk_score, 100)

        logger.info(
            "🔍 Risk assessment for %s: %s/100 (%s)",
            user_id,
            risk_score,
            ", ".join(risk_factors) if risk_factors else "No factors",
        )

        # Store transaction attempt for velocity tracking
        await self._record_transaction_attempt(user_id)

        return risk_score

    async def _check_velocity(self, user_id: str) -> int:
        """
        Check if user is making too many transfers too quickly

        Returns:
            Risk points (0-40)
        """
        redis = await self._get_redis()

        velocity_key = self.VELOCITY_KEY_TEMPLATE.format(user_id=user_id)
        now_ts = datetime.utcnow().timestamp()
        window_start_ts = (datetime.utcnow() - timedelta(minutes=self.VELOCITY_WINDOW_MINUTES)).timestamp()

        count = await redis.zcount(velocity_key, window_start_ts, now_ts)

        if count >= self.VELOCITY_LIMIT:
            logger.warning("⚠️ High velocity detected for %s: %s transfers", user_id, count)
            return self.VELOCITY_HIGH_RISK_POINTS
        if count >= 2:
            return self.VELOCITY_MEDIUM_RISK_POINTS

        return 0

    async def _record_transaction_attempt(self, user_id: str) -> None:
        """Record transaction attempt for velocity tracking"""
        redis = await self._get_redis()

        velocity_key = self.VELOCITY_KEY_TEMPLATE.format(user_id=user_id)
        timestamp = datetime.utcnow().timestamp()

        # Add to sorted set (timestamp as score)
        await redis.zadd(velocity_key, {str(timestamp): timestamp})

        # Expire after 1 hour
        await redis.expire(velocity_key, self.VELOCITY_EXPIRY_SECONDS)

    async def _is_new_beneficiary(self, user_id: str, beneficiary: str) -> bool:
        """Check if beneficiary is new (never used before)"""
        redis = await self._get_redis()

        beneficiary_hash = hashlib.md5(beneficiary.lower().encode(), usedforsecurity=False).hexdigest()
        beneficiaries_key = self.BENEFICIARIES_KEY_TEMPLATE.format(user_id=user_id)

        exists = await redis.sismember(beneficiaries_key, beneficiary_hash)

        if not exists:
            await redis.sadd(beneficiaries_key, beneficiary_hash)
            await redis.expire(beneficiaries_key, self.BENEFICIARY_EXPIRY_SECONDS)
            return True

        return False

    def _check_unusual_time(self) -> int:
        """
        Check if current time is unusual for banking

        Returns:
            Risk points (0-15)
        """
        current_hour = datetime.utcnow().hour

        # High risk: 12 AM - 5 AM
        if 0 <= current_hour < 5:
            return self.UNUSUAL_TIME_HIGH_RISK_POINTS

        # Medium risk: 10 PM - 12 AM
        if 22 <= current_hour < 24:
            return self.UNUSUAL_TIME_MEDIUM_RISK_POINTS

        return 0

    async def report_suspicious_activity(
        self,
        user_id: str,
        activity_type: str,
        details: Dict,
    ) -> None:
        """Report suspicious activity for review"""

        logger.warning(
            "🚨 SUSPICIOUS ACTIVITY REPORTED:\n  User: %s\n  Type: %s\n  Details: %s",
            user_id,
            activity_type,
            details,
        )

        redis = await self._get_redis()
        alert_key = self.ALERTS_KEY_TEMPLATE.format(user_id=user_id)

        alert_data = {
            "type": activity_type,
            "details": str(details),
            "timestamp": datetime.utcnow().isoformat(),
        }

        await redis.rpush(alert_key, str(alert_data))
        await redis.expire(alert_key, self.ALERT_EXPIRY_SECONDS)
