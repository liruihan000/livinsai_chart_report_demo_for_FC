"""E2E: GET /reports/{file_id} — download, streaming, error handling."""

from __future__ import annotations

import io
import sys
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport
from langchain_core.messages import AIMessage, ToolMessage

from livins_report_agent.main import create_app

# Patch targets for chat (used in cross-endpoint test)
_PATCH_GRAPH = "livins_report_agent.api.chat.get_graph"
_PATCH_SEMAPHORE = "livins_report_agent.api.chat.get_semaphore"


@pytest.fixture
async def app_client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _mock_anthropic_module(filename: str, content: bytes):
    """Create a fake anthropic module with mocked Files API."""
    mock_metadata = MagicMock()
    mock_metadata.filename = filename

    mock_client_instance = MagicMock()
    mock_client_instance.beta.files.retrieve_metadata.return_value = mock_metadata
    mock_client_instance.beta.files.download.return_value = io.BytesIO(content)

    mock_module = MagicMock()
    mock_module.Anthropic.return_value = mock_client_instance
    return mock_module


async def test_report_not_found(app_client):
    """Non-existent file_id returns 404 (or 501 if anthropic not installed)."""
    resp = await app_client.get("/reports/nonexistent_file_id")
    assert resp.status_code in (404, 501)


async def test_report_download_success(app_client):
    """Mock Anthropic Files API → 200, correct Content-Type and Content-Disposition."""
    pdf_bytes = b"%PDF-1.4 fake content"
    mock_module = _mock_anthropic_module("rental_report.pdf", pdf_bytes)

    with patch.dict(sys.modules, {"anthropic": mock_module}):
        resp = await app_client.get("/reports/file-abc123")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "rental_report.pdf" in resp.headers["content-disposition"]
    assert len(resp.content) > 0


async def test_report_streaming(app_client):
    """Response body is non-empty (streamed content arrives)."""
    pdf_bytes = b"%PDF-1.4 streaming test content here"
    mock_module = _mock_anthropic_module("chart.pdf", pdf_bytes)

    with patch.dict(sys.modules, {"anthropic": mock_module}):
        resp = await app_client.get("/reports/file-xyz789")

    assert resp.status_code == 200
    assert len(resp.content) == len(pdf_bytes)


async def test_report_sdk_not_installed(app_client):
    """anthropic import fails → 501."""
    # Remove anthropic from sys.modules so the local import raises ImportError
    saved = sys.modules.pop("anthropic", None)
    try:
        with patch.dict(sys.modules, {"anthropic": None}):
            resp = await app_client.get("/reports/file-test")
    finally:
        if saved is not None:
            sys.modules["anthropic"] = saved

    assert resp.status_code == 501
    assert "not installed" in resp.json()["detail"]


# ── Cross-endpoint: chat → download ──


async def test_chat_then_download(app_client):
    """POST /chat returns file_id → GET /reports/{file_id} downloads it."""
    import json

    # Step 1: chat returns a file reference
    tool_msg = ToolMessage(
        content=json.dumps({
            "files": [{"file_id": "file-report-001", "filename": "analysis.pdf"}]
        }),
        name="execute_code",
        tool_call_id="call-1",
    )
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {
        "messages": [tool_msg, AIMessage(content="报告已生成，请下载")]
    }

    with (
        patch(_PATCH_GRAPH, new_callable=AsyncMock, return_value=mock_graph),
        patch(_PATCH_SEMAPHORE, new_callable=AsyncMock, return_value=AsyncMock()),
    ):
        chat_resp = await app_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "生成曼哈顿租金报告"}],
            },
        )

    assert chat_resp.status_code == 200
    file_id = chat_resp.json()["files"][0]["file_id"]
    assert file_id == "file-report-001"

    # Step 2: download the file using the file_id from chat response
    pdf_bytes = b"%PDF-1.4 full report"
    mock_module = _mock_anthropic_module("analysis.pdf", pdf_bytes)

    with patch.dict(sys.modules, {"anthropic": mock_module}):
        download_resp = await app_client.get(f"/reports/{file_id}")

    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert "analysis.pdf" in download_resp.headers["content-disposition"]
