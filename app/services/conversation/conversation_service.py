from __future__ annotations

import json
import logging
from typing import Dict, Any, Optional

from app.models.conversation import ConversationState, ChatMessage
from app.models.tool_call import ToolCall
from app.models.bafoka import ValidAccountResponse, AccountCreationResponse
from app.services.llm import SYSTEM_PROMPT, generate_assistant_output
from app.services.bafoka import valid_account_service, create_account_service
from app.utils.tool_parser import parse_tool_call

logger = logging.getLogger(__name__)

_SESSIONS: Dict[str, ConversationState] = {}
MAX_TOOL_TURNS = 4


async def get_or_create_state(session_id: Optional[str]) -> ConversationState:
    if session_id and session_id in _SESSIONS:
        return _SESSIONS[session_id]

    state = ConversationState()
    state.messages.append(ChatMessage(role="system", content=SYSTEM_PROMPT))
    _SESSIONS[state.session_id] = state
    logger.info("Created new conversation session: %s", state.session_id)
    return state


async def handle_user_text(
    session: ConversationState,
    user_text: str,
) -> Dict[str, Any]:
    """
    Handle one user utterance:
      - Append user text
      - Run LLM + potential tool calls
      - Return assistant_text & session_id
    """
    logger.info("User (%s): %s", session.session_id, user_text)
    session.messages.append(ChatMessage(role="user", content=user_text))

    for _ in range(MAX_TOOL_TURNS):
        assistant_output = generate_assistant_output(session.messages)
        tool_call = parse_tool_call(assistant_output)

        if tool_call:
            await _handle_tool_call(session, tool_call, assistant_output)
            continue

        # Normal assistant reply
        session.messages.append(
            ChatMessage(role="assistant", content=assistant_output)
        )
        logger.info("Assistant (%s): %s", session.session_id, assistant_output)
        return {
            "assistant_text": assistant_output,
            "session_id": session.session_id,
        }

    # Fallback after many tool turns
    session.messages.append(ChatMessage(role="assistant", content=assistant_output))
    logger.warning(
        "Max tool turns exceeded for session %s; returning last output", session.session_id
    )
    return {
        "assistant_text": assistant_output,
        "session_id": session.session_id,
    }


async def _handle_tool_call(
    session: ConversationState,
    tool_call: ToolCall,
    raw_json_text: str,
) -> None:
    logger.info(
        "Tool requested in session %s: %s args=%s",
        session.session_id,
        tool_call.tool,
        tool_call.arguments,
    )

    # Store raw JSON tool call
    session.messages.append(ChatMessage(role="assistant", content=raw_json_text))

    tool_result = await _execute_tool(tool_call)

    # Feed tool result back as synthetic user message
    content = f"[tool_result name={tool_call.tool}] {json.dumps(tool_result)}"
    session.messages.append(ChatMessage(role="user", content=content))


async def _execute_tool(tool_call: ToolCall) -> Dict[str, Any]:
    name = tool_call.tool
    args = tool_call.arguments or {}

    if name == "check_valid_account":
        return await _tool_check_valid_account(args)
    if name == "create_account":
        return await _tool_create_account(args)

    logger.error("Unknown tool requested: %s", name)
    return {"error": f"Unknown tool: {name}", "received_arguments": args}


async def _tool_check_valid_account(args: Dict[str, Any]) -> Dict[str, Any]:
    phone = args.get("phone_number")
    if not phone:
        return {"error": "phone_number argument missing"}

    resp: ValidAccountResponse = await valid_account_service.check_valid_account(phone)
    return resp.model_dump()


async def _tool_create_account(args: Dict[str, Any]) -> Dict[str, Any]:
    phone = args.get("phone_number")
    full_name = args.get("full_name")
    age = args.get("age")
    groupement = args.get("groupement")

    missing = [k for k in ("phone_number", "full_name", "age", "groupement") if args.get(k) is None]
    if missing:
        return {"error": "Missing required arguments", "missing": missing, "received": args}

    try:
        age_int = int(age)
    except (TypeError, ValueError):
        return {"error": "age must be an integer", "received": args}

    resp: AccountCreationResponse = await create_account_service.create_account(
        phone_number=phone,
        full_name=full_name,
        age=age_int,
        groupement=groupement,
    )
    return resp.model_dump()