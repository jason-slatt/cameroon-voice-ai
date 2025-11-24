# src/api/v1/endpoints/botpress.py
from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.core.dependencies import get_llama_service
from src.core.logging import logger

router = APIRouter()


class Message(BaseModel):
    conversationId: str
    userId: str
    text: str


@router.post("/webhook")
async def webhook(request: Request):
    """Receive from Botpress, send response"""
    
    data = await request.json()
    logger.info(f"Received: {data}")
    
    # Extract message
    text = data.get("message", {}).get("payload", {}).get("text", "")
    conv_id = data.get("conversationId")
    user_id = data.get("userId")
    
    if not text:
        return {"status": "ignored"}
    
    # Get AI response
    llama = get_llama_service()
    response = await llama.generate_response(text, conv_id)
    
    logger.info(f"Response: {response}")
    
    # Return to Botpress
    return {
        "responses": [{
            "type": "text",
            "text": response
        }]
    }