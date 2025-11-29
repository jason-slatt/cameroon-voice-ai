from __future__ import annotations
from typing import Optional
import json

from app.models.tool_call import ToolCall


def parse_tool_call(raw_text: str) -> Optional[ToolCall]:
    """
    Try to parse the LLM output as a ToolCall JSON.
    Expected format:
      {
        "tool": "check_valid_account",
        "arguments": { ... }
      }
    """
    text = raw_text.strip()
    if not text.startswith("{"):
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict) or "tool" not in data or "arguments" not in data:
        return None

    try:
        return ToolCall.model_validate(data)
    except Exception:
        return None