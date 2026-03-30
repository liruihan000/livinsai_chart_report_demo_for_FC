"""Complex E2E test — multiple chart types + PDF report, real LLM."""

import json
import os

import pytest
from httpx import AsyncClient, ASGITransport

_api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not _api_key:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
    _api_key = os.getenv("ANTHROPIC_API_KEY", "")

skip_no_key = pytest.mark.skipif(not _api_key, reason="ANTHROPIC_API_KEY not set")


@pytest.fixture
async def real_client():
    import livins_report_agent.dependencies as deps
    deps._graph = None
    deps._invoke_semaphore = None
    os.environ["USE_MOCK_CLIENT"] = "true"

    from livins_report_agent.main import create_app
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    deps._graph = None
    deps._invoke_semaphore = None


@skip_no_key
async def test_complex_multi_chart_report(real_client):
    """Full flow: 4 chart types + PDF report, all in English."""
    resp = await real_client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Do a comprehensive NYC rental analysis. Steps:\n"
                        "1. load_skill('data_query') to get schema\n"
                        "2. query_database: avg rent by borough (GROUP BY borough)\n"
                        "3. query_database: monthly trends (DATE_TRUNC)\n"
                        "4. query_database: ML condition_level vs price\n"
                        "5. load_skill('chart_generation') and load_skill('report_building')\n"
                        "6. Use ONE SINGLE execute_code call to do ALL of this together:\n"
                        "   - Generate 4 charts (bar, line, pie, scatter) saved to local disk\n"
                        "   - Build a PDF report embedding all 4 charts using reportlab Image()\n"
                        "   - Save the final PDF to os.getenv('OUTPUT_DIR','.') as report.pdf\n"
                        "   IMPORTANT: Charts and PDF MUST be in the same execute_code call!\n"
                        "   Each execute_code runs in a separate sandbox - files don't persist.\n"
                        "ALL text in charts and PDF MUST be English only (no Chinese).\n"
                        "Reply summary in Chinese."
                    ),
                }
            ],
        },
        timeout=300,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"]
    assert len(data["reply"]) > 50

    print(f"\n=== Reply ({len(data['reply'])} chars) ===")
    print(data["reply"][:600])
    print(f"\n=== Files ===")
    if data.get("files"):
        for f in data["files"]:
            print(f"  {f['file_id']}  {f['filename']}")
        assert len(data["files"]) >= 1, "Should generate at least 1 file"

        # Download and save all files
        import anthropic
        client = anthropic.Anthropic(api_key=_api_key)
        os.makedirs("reports", exist_ok=True)
        for i, f in enumerate(data["files"]):
            content = client.beta.files.download(f["file_id"])
            raw = content.read()
            name = f["filename"] if f["filename"] != "output" else f"output_{i}"
            path = f"reports/{name}"
            with open(path, "wb") as fp:
                fp.write(raw)
            print(f"  Saved: {path} ({len(raw)} bytes)")
    else:
        print(f"  No files returned")
