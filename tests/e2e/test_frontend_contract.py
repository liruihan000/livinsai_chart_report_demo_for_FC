"""E2E: Frontend contract tests — verify API responses match frontend type definitions.

Only tests that are NOT covered by test_chat_flow.py / test_report_download.py.
Validates response shape matches frontend types.ts (ChatResponse, FileRef).
"""

from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from langchain_core.messages import AIMessage

from livins_report_agent.main import create_app

_PATCH_GRAPH = "livins_report_agent.api.chat.get_graph"
_PATCH_SEMAPHORE = "livins_report_agent.api.chat.get_semaphore"


@pytest.fixture
async def app_client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ── Response shape matches frontend ChatResponse ──


async def test_response_has_all_frontend_fields(app_client):
    """Response must have reply, session_id; files is optional (null when absent)."""
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"messages": [AIMessage(content="分析完成")]}
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
