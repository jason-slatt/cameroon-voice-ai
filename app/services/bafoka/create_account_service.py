from __future__ import annotations

from app.clients import get_bafoka_client
from app.models.bafoka import AccountCreationRequest, AccountCreationResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def create_account(
    phone_number: str,
    full_name: str,
    age: int,
    groupement: str,
) -> AccountCreationResponse:
    """
    Create an account via BAFOKA backend.
    """
    req = AccountCreationRequest(
        phone_number=phone_number,
        full_name=full_name,
        age=age,
        groupement=groupement,
    )
    logger.info("Creating account in BAFOKA for phone_number=%s", phone_number)

    client = get_bafoka_client()
    resp = await client.post(
        "/api/account-creation",
        data=req,
        response_model=AccountCreationResponse,
    )
    return resp