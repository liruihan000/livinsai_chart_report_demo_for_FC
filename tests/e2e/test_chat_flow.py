"""E2E: POST /chat → reply (mock LLM, real API flow)."""

from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from langchain_core.messages import AIMessage

from livins_report_agent.main import create_app

# Patch where the name is USED (api.chat), not where it's DEFINED (dependencies)
_PATCH_GRAPH = "livins_report_agent.api.chat.get_graph"
_PATCH_SEMAPHORE = "livins_report_agent.api.chat.get_semaphore"


@pytest.fixture
async def app_client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _mock_graph_with(content: str):
    """Helper: create a mock graph that returns an AIMessage with given content."""
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"messages": [AIMessage(content=content)]}
    return mock_graph


async def test_health(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_chat_success(app_client):
    mock_graph = _mock_graph_with("曼哈顿一居室均价$3,500")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "分析曼哈顿租金"}],
                "session_id": "test-session",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["session_id"] == "test-session"
    assert "曼哈顿" in data["reply"]


async def test_chat_generates_session_id(app_client):
    mock_graph = _mock_graph_with("ok")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp.status_code == 200
    assert resp.json()["session_id"]  # auto-generated UUID


async def test_chat_empty_messages(app_client):
    resp = await app_client.post("/chat", json={"messages": []})
    assert resp.status_code == 422


async def test_chat_invalid_role(app_client):
    resp = await app_client.post(
        "/chat",
        json={"messages": [{"role": "system", "content": "hi"}]},
    )
    assert resp.status_code == 422


async def test_chat_missing_messages_field(app_client):
    """Request body without messages field → 422."""
    resp = await app_client.post("/chat", json={"session_id": "test"})
    assert resp.status_code == 422


async def test_chat_multi_turn(app_client):
    """Multi-turn messages (user/assistant alternating) → Agent receives full context."""
    mock_graph = _mock_graph_with("对比结果如下")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": "分析曼哈顿租金"},
                    {"role": "assistant", "content": "曼哈顿一居室均价$3,500"},
                    {"role": "user", "content": "和布鲁克林对比呢"},
                ],
                "session_id": "multi-turn",
            },
        )
    assert resp.status_code == 200
    # Verify agent received all 3 messages
    call_args = mock_graph.ainvoke.call_args
    lc_messages = call_args[0][0]["messages"]
    assert len(lc_messages) == 3


async def test_chat_with_files(app_client):
    """Agent returns file attachments → response files field populated."""
    mock_graph = AsyncMock()
    from langchain_core.messages import ToolMessage
    import json

    tool_msg = ToolMessage(
        content=json.dumps({
            "files": [{"file_id": "file-abc123", "filename": "report.pdf"}]
        }),
        name="execute_code",
        tool_call_id="call-1",
    )
    mock_graph.ainvoke.return_value = {
        "messages": [tool_msg, AIMessage(content="报告已生成")]
    }
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "生成租金报告"}],
                "session_id": "file-test",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["files"] is not None
    assert len(data["files"]) == 1
    assert data["files"][0]["file_id"] == "file-abc123"
    assert data["files"][0]["filename"] == "report.pdf"


async def test_chat_agent_error(app_client):
    """Agent invocation raises exception → 500 with error detail."""
    mock_graph = AsyncMock()
    mock_graph.ainvoke.side_effect = RuntimeError("LLM provider unavailable")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "分析租金"}],
                "session_id": "error-test",
            },
        )
    assert resp.status_code == 500
    assert "LLM provider unavailable" in resp.json()["detail"]


async def test_chat_agent_empty_response(app_client):
    """Agent returns no AIMessage → 500."""
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"messages": []}  # no AIMessage
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "session_id": "empty-test",
            },
        )
    assert resp.status_code == 500
    assert "no response" in resp.json()["detail"].lower()


async def test_chat_concurrency_limit(app_client):
    """Semaphore gates concurrent invocations — requests are serialized, not rejected."""
    import asyncio

    call_order = []

    async def slow_invoke(*args, **kwargs):
        call_order.append("start")
        await asyncio.sleep(0.05)
        call_order.append("end")
        return {"messages": [AIMessage(content="ok")]}

    mock_graph = AsyncMock()
    mock_graph.ainvoke.side_effect = slow_invoke

    # Use a semaphore with capacity 1 to force serialization
    real_semaphore = asyncio.Semaphore(1)

    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=real_semaphore),
    ):
        payload = {"messages": [{"role": "user", "content": "hi"}]}
        tasks = [app_client.post("/chat", json=payload) for _ in range(3)]
        responses = await asyncio.gather(*tasks)

    assert all(r.status_code == 200 for r in responses)
    # With semaphore(1), calls are serialized: start/end pairs don't interleave
    assert call_order == ["start", "end", "start", "end", "start", "end"]
