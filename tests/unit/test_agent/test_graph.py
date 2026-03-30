"""Tests for agent graph compilation (no LLM execution)."""

from unittest.mock import MagicMock

from livins_report_agent.agent.graph import create_all_tools, SYSTEM_PROMPT
from livins_report_agent.apartment_client.mock_client import MockDataClient


def test_create_all_tools():
    client = MockDataClient()
    tools = create_all_tools(client)
    assert len(tools) == 2
    names = {t.name for t in tools}
    assert "load_skill" in names
    assert "query_database" in names


def test_system_prompt_not_empty():
    assert len(SYSTEM_PROMPT) > 100


def test_system_prompt_contains_workflow():
    assert "load_skill" in SYSTEM_PROMPT
    assert "query_database" in SYSTEM_PROMPT
