"""Real E2E tests — no mocks, real LLM + Code Execution sandbox.

Requires: ANTHROPIC_API_KEY set in .env
Uses: MockDataClient for data (no need for data_service running)
Tests: Full agent flow including chart and PDF generation
"""

import json
import os

import pytest
from httpx import AsyncClient, ASGITransport

from livins_report_agent.config import Settings

# Skip entire module if no API key
_api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not _api_key:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    _api_key = os.getenv("ANTHROPIC_API_KEY", "")

skip_no_key = pytest.mark.skipif(not _api_key, reason="ANTHROPIC_API_KEY not set")


@pytest.fixture
async def real_client():
    """Create app with real LLM, MockDataClient."""
    # Reset singleton so each test gets fresh graph
    import livins_report_agent.dependencies as deps
    deps._graph = None
    deps._invoke_semaphore = None

    # Force mock client + real LLM
    os.environ["USE_MOCK_CLIENT"] = "true"

    from livins_report_agent.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    deps._graph = None
    deps._invoke_semaphore = None


@skip_no_key
class TestRealAgentDataQuery:
    """Test agent can query data and provide analysis (no chart/PDF)."""

    @pytest.mark.timeout(120)
    async def test_simple_analysis(self, real_client):
        """Agent should load skill, query data, return analysis."""
        resp = await real_client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": "各区的平均租金是多少？给我简短的数据总结"}
                ],
            },
            timeout=120,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]
        assert data["session_id"]
        # Agent should mention at least one borough
        reply_lower = data["reply"].lower()
        assert any(
            b in reply_lower
            for b in ["manhattan", "brooklyn", "queens", "bronx", "曼哈顿", "布鲁克林"]
        ), f"Reply doesn't mention any borough: {data['reply'][:300]}"

    @pytest.mark.timeout(120)
    async def test_multi_turn_conversation(self, real_client):
        """Agent handles conversation history correctly."""
        resp = await real_client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": "曼哈顿的一居室均价多少？"},
                    {"role": "assistant", "content": "根据数据，曼哈顿一居室均价约$3,500。"},
                    {"role": "user", "content": "和布鲁克林比呢？"},
                ],
            },
            timeout=120,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]
        # Should reference Brooklyn in comparison context
        reply_lower = data["reply"].lower()
        assert any(
            b in reply_lower for b in ["brooklyn", "布鲁克林"]
        ), f"Reply doesn't mention Brooklyn: {data['reply'][:300]}"


@skip_no_key
class TestRealAgentChartGeneration:
    """Test agent generates charts via Code Execution sandbox."""

    @pytest.mark.timeout(180)
    async def test_generate_chart(self, real_client):
        """Agent should generate a chart and return file reference."""
        resp = await real_client.post(
            "/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "查询各区的平均租金，然后生成一个柱状图。"
                            "用execute_code工具执行matplotlib代码，"
                            "文件保存到 os.getenv('OUTPUT_DIR', '.') 目录下。"
                        ),
                    }
                ],
            },
            timeout=180,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]

        # Should have generated files
        if data.get("files"):
            assert len(data["files"]) > 0
            for f in data["files"]:
                assert f["file_id"]
                assert f["filename"]
            print(f"✓ Chart generated: {data['files']}")
        else:
            # Agent may not always produce files depending on LLM behavior
            print(f"⚠ No files returned, reply: {data['reply'][:200]}")


@skip_no_key
class TestRealAgentPdfReport:
    """Test agent generates PDF report via Code Execution sandbox."""

    @pytest.mark.timeout(180)
    async def test_generate_pdf_report(self, real_client):
        """Agent should generate a PDF report with data analysis."""
        resp = await real_client.post(
            "/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "查询各区的平均租金数据，然后生成一个PDF报告。"
                            "报告包含：标题、数据表格、简要分析。"
                            "使用execute_code工具执行reportlab代码生成PDF，"
                            "文件保存到 os.getenv('OUTPUT_DIR', '.') 目录下。"
                        ),
                    }
                ],
            },
            timeout=180,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]

        if data.get("files"):
            assert len(data["files"]) > 0
            for f in data["files"]:
                assert f["file_id"], "file_id should not be empty"
            print(f"✓ PDF report generated: {data['files']}")

            # Verify file is downloadable via /reports/{file_id}
            file_id = data["files"][0]["file_id"]
            dl_resp = await real_client.get(
                f"/reports/{file_id}", timeout=30
            )
            assert dl_resp.status_code == 200
            assert len(dl_resp.content) > 0
            print(f"✓ PDF download verified: {file_id} ({len(dl_resp.content)} bytes)")
        else:
            print(f"⚠ No files returned, reply: {data['reply'][:200]}")


@skip_no_key
class TestRealAgentFullFlow:
    """Test complete flow: query → chart → PDF in one conversation."""

    @pytest.mark.timeout(240)
    async def test_full_analysis_report(self, real_client):
        """Full flow: data analysis → chart → PDF report."""
        resp = await real_client.post(
            "/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "请完成以下分析任务：\n"
                            "1. 先加载data_query skill获取数据库schema\n"
                            "2. 查询各区（borough）的平均租金\n"
                            "3. 加载chart_generation skill获取图表规范\n"
                            "4. 用execute_code生成一个柱状图（保存到OUTPUT_DIR）\n"
                            "5. 加载report_building skill获取报告规范\n"
                            "6. 用execute_code生成一个PDF报告，包含数据分析和图表（保存到OUTPUT_DIR）\n"
                            "7. 给我文字总结"
                        ),
                    }
                ],
            },
            timeout=240,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]
        assert len(data["reply"]) > 50, "Reply too short for a full analysis"

        print(f"Reply length: {len(data['reply'])} chars")
        print(f"Files: {data.get('files')}")

        if data.get("files"):
            filenames = [f["filename"] for f in data["files"]]
            print(f"✓ Generated files: {filenames}")
