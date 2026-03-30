"""POST /chat and /chat/stream endpoints."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from livins_report_agent.config import get_settings
from livins_report_agent.dependencies import get_graph, get_semaphore
from livins_report_agent.models import ChatRequest, ChatResponse, FileInfo

logger = logging.getLogger(__name__)
router = APIRouter()

# Human-readable tool name mapping
_TOOL_LABELS: dict[str, str] = {
    "load_skill": "加载技能",
    "query_database": "查询数据库",
    "execute_code": "执行代码",
}


def _to_langchain_messages(messages: list) -> list:
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


def _sse_event(event: str, data: dict | list) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_files(messages: list) -> list[dict]:
    """Extract file references from the LAST successful execute_code call.

    Each execute_code runs in a separate sandbox; only the final call's
    files matter (earlier calls are retries / intermediate attempts).
    """
    last_files: list[dict] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name == "execute_code":
            try:
                tool_result = json.loads(msg.content)
                batch = tool_result.get("files", [])
                if batch:
                    last_files = [
                        {"file_id": f["file_id"], "filename": f["filename"]}
                        for f in batch
                    ]
            except (json.JSONDecodeError, KeyError):
                pass
    return last_files


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
    files = _extract_files(result["messages"])

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        files=[FileInfo(**f) for f in files] if files else None,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint that emits tool call steps and final reply."""
    settings = get_settings()
    graph = await get_graph()
    semaphore = await get_semaphore()

    session_id = request.session_id or str(uuid.uuid4())
    lc_messages = _to_langchain_messages(request.messages)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send session_id immediately
        yield _sse_event("session", {"session_id": session_id})

        async with semaphore:
            try:
                all_messages: list = []
                text_buffer: list[str] = []  # buffer text between tool calls

                async for event in graph.astream_events(
                    {"messages": lc_messages},
                    config={"recursion_limit": settings.max_agent_steps},
                    version="v2",
                ):
                    kind = event.get("event")
                    name = event.get("name", "")

                    if kind == "on_tool_start":
                        # Flush buffered text as "thinking" (intermediate reasoning)
                        thinking_text = "".join(text_buffer).strip()
                        if thinking_text:
                            logger.info(
                                "Emitting thinking (%d chars): %.80s...",
                                len(thinking_text), thinking_text,
                            )
                            yield _sse_event("thinking", {
                                "content": thinking_text,
                            })
                        else:
                            logger.info(
                                "No thinking text buffered before tool_start: %s",
                                name,
                            )
                        text_buffer.clear()
                        tool_input = event.get("data", {}).get("input", {})
                        display_input = _summarize_tool_input(name, tool_input)
                        yield _sse_event("tool_start", {
                            "name": name,
                            "label": _TOOL_LABELS.get(name, name),
                            "input": display_input,
                        })

                    elif kind == "on_tool_end":
                        output_msg = event.get("data", {}).get("output")
                        if isinstance(output_msg, ToolMessage):
                            all_messages.append(output_msg)
                            # Emit files immediately when execute_code finishes
                            if name == "execute_code":
                                files = _extract_files([output_msg])
                                if files:
                                    yield _sse_event("files", {"files": files})
                        yield _sse_event("tool_end", {
                            "name": name,
                            "label": _TOOL_LABELS.get(name, name),
                        })

                    elif kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            text = _extract_text_from_chunk(chunk.content)
                            if text:
                                text_buffer.append(text)

                # Remaining buffer is the final response → emit as tokens
                if text_buffer:
                    yield _sse_event("token", {"content": "".join(text_buffer)})

                files = _extract_files(all_messages)
                yield _sse_event("done", {"files": files})

            except Exception as exc:
                logger.exception("Agent streaming failed")
                yield _sse_event("error", {"detail": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _extract_text_from_chunk(content) -> str:
    """Extract text from an AIMessageChunk content field.

    Handles all formats:
    - str: plain text token
    - list of dicts: Anthropic content blocks (text, text_delta, tool_use, etc.)
    - other: skip
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            # text block (full or delta)
            if btype in ("text", "text_delta"):
                parts.append(block.get("text", ""))
            # Skip tool_use, tool_use_delta, input_json_delta, etc.
        return "".join(parts)
    return ""


def _summarize_tool_input(tool_name: str, tool_input: dict | str) -> str:
    """Create a concise display string for tool input."""
    if isinstance(tool_input, str):
        return tool_input[:200]
    if tool_name == "load_skill":
        return tool_input.get("name", str(tool_input))
    if tool_name == "query_database":
        sql = tool_input.get("sql", str(tool_input))
        return sql[:300] if isinstance(sql, str) else str(sql)[:300]
    if tool_name == "execute_code":
        code = tool_input.get("code", str(tool_input))
        return code[:100] + "..." if len(str(code)) > 100 else str(code)
    return str(tool_input)[:200]
