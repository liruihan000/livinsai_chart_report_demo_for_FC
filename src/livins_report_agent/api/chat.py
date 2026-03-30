"""POST /chat endpoint."""

from __future__ import annotations

import logging
import uuid

import json

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from livins_report_agent.config import get_settings
from livins_report_agent.dependencies import get_graph, get_semaphore
from livins_report_agent.models import ChatRequest, ChatResponse, FileInfo

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_langchain_messages(messages: list) -> list:
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    settings = get_settings()
    graph = await get_graph()
    semaphore = await get_semaphore()

    session_id = request.session_id or str(uuid.uuid4())
    lc_messages = _to_langchain_messages(request.messages)

    async with semaphore:
        try:
            result = await graph.ainvoke(
                {"messages": lc_messages},
                config={"recursion_limit": settings.max_agent_steps},
            )
        except Exception as exc:
            logger.exception("Agent invocation failed")
            raise HTTPException(status_code=500, detail=str(exc))

    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    if not ai_messages:
        raise HTTPException(status_code=500, detail="Agent produced no response")

    reply = ai_messages[-1].content

    # Extract file references from execute_code tool results
    files = []
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage) and msg.name == "execute_code":
            try:
                tool_result = json.loads(msg.content)
                for f in tool_result.get("files", []):
                    files.append(FileInfo(file_id=f["file_id"], filename=f["filename"]))
            except (json.JSONDecodeError, KeyError):
                pass

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        files=files if files else None,
    )
