from __future__ import annotations

from app.clients import get_bafoka_client
from app.models.bafoka import ValidAccountRequest, ValidAccountResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def check_valid_account(phone_number: str) -> ValidAccountResponse:
    """
    Check whether an account exists for the given phone number via BAFOKA.
    """
    req = ValidAccountRequest(phone_number=phone_number)
    logger.info("Checking valid account for phone_number=%s", phone_number)

    client = get_bafoka_client()
    resp = await client.post(
        "/api/valid-account",
        data=req,
        response_model=ValidAccountResponse,
    )
    return resp