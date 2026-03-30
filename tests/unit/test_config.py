"""Tests for Settings config."""

from livins_report_agent.config import Settings


def test_default_settings():
    s = Settings(anthropic_api_key="test")
    assert s.use_mock_client is True
    assert s.max_agent_steps == 15
    assert s.api_port == 8000


def test_settings_override():
    s = Settings(
        llm_model="openai:gpt-4o",
        anthropic_api_key="key",
        use_mock_client=False,
        max_agent_steps=25,
    )
    assert s.llm_model == "openai:gpt-4o"
    assert s.use_mock_client is False
    assert s.max_agent_steps == 25
