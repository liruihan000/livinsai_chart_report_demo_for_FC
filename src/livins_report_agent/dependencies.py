"""DI singletons — asyncio.Lock graph, Semaphore concurrency control."""

from __future__ import annotations

import asyncio

from langgraph.graph.state import CompiledStateGraph

from livins_report_agent.agent.graph import build_agent_graph
from livins_report_agent.apartment_client import MockDataClient, HttpDataClient
from livins_report_agent.config import Settings, get_settings

_graph: CompiledStateGraph | None = None
_graph_lock = asyncio.Lock()
_invoke_semaphore: asyncio.Semaphore | None = None


def _build_client(settings: Settings):
    if settings.use_mock_client:
        return MockDataClient()
    return HttpDataClient(settings.data_service_url)


async def get_graph() -> CompiledStateGraph:
    global _graph
    if _graph is not None:
        return _graph
    async with _graph_lock:
        if _graph is None:
            settings = get_settings()
            client = _build_client(settings)
            _graph = build_agent_graph(client, settings=settings)
    return _graph


async def get_semaphore() -> asyncio.Semaphore:
    global _invoke_semaphore
    if _invoke_semaphore is None:
        settings = get_settings()
        _invoke_semaphore = asyncio.Semaphore(settings.max_concurrent_invocations)
    return _invoke_semaphore
