"""Shared fixtures: mock_client, settings."""

from __future__ import annotations

import pytest

from livins_report_agent.apartment_client.mock_client import MockDataClient
from livins_report_agent.config import Settings


@pytest.fixture
def mock_client():
    return MockDataClient()


@pytest.fixture
def settings():
    return Settings(
        llm_model="anthropic:claude-haiku-4-5-20251001",
        anthropic_api_key="test-key",
        use_mock_client=True,
    )
