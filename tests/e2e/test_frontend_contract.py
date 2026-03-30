"""E2E: Frontend contract tests — verify API responses match frontend expectations.

Tests the API contract from the frontend's perspective:
- Response shape matches frontend types.ts (ChatResponse, FileRef)
- Session ID lifecycle (auto-generate, round-trip)
- Files field presence/absence in response
- Multi-turn conversation (localStorage replay pattern)
"""

from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from langchain_core.messages import AIMessage

from livins_report_agent.main import create_app

# Patch targets — must patch where the name is USED, not where it's DEFINED
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


# ── Response shape matches frontend ChatResponse ──


async def test_response_has_all_frontend_fields(app_client):
    """Response must have reply, session_id; files is optional (null when absent)."""
    mock_graph = _mock_graph_with("分析完成")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "分析租金趋势"}],
                "session_id": "frontend-test-session",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    # Frontend ChatResponse requires: reply (str), session_id (str), files (optional)
    assert isinstance(data["reply"], str)
    assert isinstance(data["session_id"], str)
    assert "files" in data  # field must exist even if null
    assert data["files"] is None  # no files in basic chat


async def test_response_files_shape_when_present():
    """When files are present, each must have file_id and filename (matching FileRef)."""
    from livins_report_agent.models import ChatResponse, FileInfo

    resp_obj = ChatResponse(
        reply="报告已生成",
        session_id="test",
        files=[FileInfo(file_id="file-abc123", filename="report.pdf")],
    )
    data = resp_obj.model_dump()

    assert data["files"] is not None
    assert len(data["files"]) == 1
    file_ref = data["files"][0]
    # Must match frontend FileRef: { file_id: string, filename: string }
    assert "file_id" in file_ref
    assert "filename" in file_ref
    assert isinstance(file_ref["file_id"], str)
    assert isinstance(file_ref["filename"], str)


# ── Session ID lifecycle ──


async def test_session_id_round_trip(app_client):
    """Frontend sends session_id, server echoes it back unchanged."""
    mock_graph = _mock_graph_with("ok")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "session_id": "my-uuid-from-browser",
            },
        )
    assert resp.json()["session_id"] == "my-uuid-from-browser"


async def test_session_id_auto_generated_when_missing(app_client):
    """Frontend may omit session_id on first message; server generates UUID."""
    mock_graph = _mock_graph_with("ok")
    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        resp = await app_client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    sid = resp.json()["session_id"]
    assert sid  # non-empty
    assert len(sid) == 36  # UUID format


# ── Multi-turn conversation (localStorage replay) ──


async def test_multi_turn_messages(app_client):
    """Frontend sends full message history each turn (localStorage pattern)."""
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
                "session_id": "multi-turn-test",
            },
        )
    assert resp.status_code == 200
    assert "对比" in resp.json()["reply"]


# ── Report download endpoint ──


async def test_report_endpoint_returns_404_for_unknown_file(app_client):
    """GET /reports/{file_id} — unknown file_id returns 404."""
    resp = await app_client.get("/reports/nonexistent-file-id")
    assert resp.status_code in (404, 501)


# ── Validation: frontend error handling ──


async def test_empty_content_rejected(app_client):
    """Frontend should prevent empty messages; server rejects if they slip through."""
    resp = await app_client.post(
        "/chat",
        json={
            "messages": [{"role": "user", "content": ""}],
            "session_id": "test",
        },
    )
    assert resp.status_code == 422


async def test_missing_messages_rejected(app_client):
    """Request without messages field is rejected."""
    resp = await app_client.post("/chat", json={"session_id": "test"})
    assert resp.status_code == 422
