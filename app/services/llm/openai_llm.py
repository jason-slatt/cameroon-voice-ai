from __future__ import annotations
from typing import List
from openai import OpenAI

from app.config.settings import settings
from app.models.conversation import ChatMessage


_client = OpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
)


def generate_assistant_output(messages: List[ChatMessage]) -> str:
    """
    Call the LLM with the current conversation messages.
    Returns raw content (could be tool-call JSON or normal text).
    """
    payload = [m.model_dump() for m in messages]

    resp = _client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=payload,
        temperature=0.3,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""