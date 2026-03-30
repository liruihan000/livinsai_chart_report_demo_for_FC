"""HttpDataClient — calls data_service /query/execute over HTTP."""

from __future__ import annotations

import httpx


class HttpDataClient:
    """Production client that forwards SQL to the data_service API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def execute_query(self, sql: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/query/execute",
                json={"sql": sql},
            )
            resp.raise_for_status()
            return resp.json()
