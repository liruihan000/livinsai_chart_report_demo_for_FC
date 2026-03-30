"""Application settings via pydantic-settings + .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_model: str = "anthropic:claude-haiku-4-5-20251001"
    anthropic_api_key: str = ""
    use_mock_client: bool = True
    data_service_url: str = "http://localhost:8002"
    max_agent_steps: int = 15
    max_concurrent_invocations: int = 5
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    report_output_dir: str = "./reports"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()
