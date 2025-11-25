# src/services/banking/security.py
"""
2FA and OTP management for secure banking operations
"""
import hashlib
import secrets
from typing import Dict
from datetime import datetime

from src.core.dependencies import get_redis
from src.core.logging import logger


class OTPService:
    """
    One-Time Password service for 2FA
    Uses Redis for temporary storage
    """

    OTP_LENGTH = 6
    OTP_VALIDITY_MINUTES = 5
    MAX_ATTEMPTS = 3

    def __init__(self) -> None:
        self.redis = None

    async def _get_redis(self):
        """Get Redis connection"""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    def _generate_otp_code(self) -> str:
        """Generate numeric OTP with fixed length"""
        return "".join(str(secrets.randbelow(10)) for _ in range(self.OTP_LENGTH))

    def _hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()

    async def generate_otp(
        self,
        user_id: str,
        conversation_id: str,
        action: str,
        **metadata,
    ) -> str:
        """
        Generate and store OTP

        Args:
            user_id: User identifier
            conversation_id: Conversation ID
            action: Action requiring OTP (virement, bloquer_carte, etc.)
            **metadata: Additional context (amount, beneficiary, etc.)

        Returns:
            OTP code (6 digits)
        """
        redis = await self._get_redis()

        otp_code = self._generate_otp_code()
        otp_hash = self._hash_otp(otp_code)

        redis_key = f"otp:{user_id}:{conversation_id}"

        otp_data: Dict[str, str] = {
            "otp_hash": otp_hash,
            "action": action,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": "0",
            **{k: str(v) for k, v in metadata.items()},
        }

        await redis.hset(redis_key, mapping=otp_data)
        await redis.expire(redis_key, self.OTP_VALIDITY_MINUTES * 60)

        logger.info("🔐 OTP generated for %s - Action: %s", user_id, action)

        # TODO: Send OTP via SMS/WhatsApp in production
        # For prototype, return it (will be removed in production)
        return otp_code

    async def verify_otp(
        self,
        user_id: str,
        conversation_id: str,
        otp_code: str,
    ) -> Dict[str, object]:
        """
        Verify OTP

        Returns:
            {
                "valid": bool,
                "action": str (if valid),
                "metadata": dict (if valid),
                "error": str (if invalid)
            }
        """
        redis = await self._get_redis()
        redis_key = f"otp:{user_id}:{conversation_id}"

        otp_data = await redis.hgetall(redis_key)

        if not otp_data:
            logger.warning("🔐 OTP not found or expired for %s", user_id)
            return {
                "valid": False,
                "error": "OTP expiré ou invalide",
            }

        attempts = int(otp_data.get("attempts", "0"))

        if attempts >= self.MAX_ATTEMPTS:
            logger.warning("🔐 Max OTP attempts exceeded for %s", user_id)
            await redis.delete(redis_key)
            return {
                "valid": False,
                "error": "Nombre maximum de tentatives atteint",
            }

        otp_hash = self._hash_otp(otp_code)
        stored_hash = otp_data.get("otp_hash")

        if otp_hash != stored_hash:
            await redis.hincrby(redis_key, "attempts", 1)
            remaining_attempts = self.MAX_ATTEMPTS - attempts - 1
            logger.warning(
                "🔐 Invalid OTP for %s. Attempts left: %s",
                user_id,
                remaining_attempts,
            )
            return {
                "valid": False,
                "error": f"Code incorrect. {remaining_attempts} tentatives restantes",
            }

        logger.info("✅ OTP verified for %s - Action: %s", user_id, otp_data.get("action"))

        await redis.delete(redis_key)

        metadata = {
            key: value
            for key, value in otp_data.items()
            if key not in {"otp_hash", "attempts", "created_at", "action"}
        }

        return {
            "valid": True,
            "action": otp_data.get("action"),
            "metadata": metadata,
        }

    async def cancel_otp(self, user_id: str, conversation_id: str) -> None:
        """Cancel/invalidate OTP"""
        redis = await self._get_redis()
        redis_key = f"otp:{user_id}:{conversation_id}"
        await redis.delete(redis_key)

        logger.info("🔐 OTP cancelled for %s", user_id)
