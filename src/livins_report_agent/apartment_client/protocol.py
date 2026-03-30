"""DataClientProtocol — structural typing interface for data access."""

from __future__ import annotations

from typing import Protocol


class DataClientProtocol(Protocol):
    async def execute_query(self, sql: str) -> dict: ...
