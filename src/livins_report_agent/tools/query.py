"""query_database tool — executes read-only SQL via DataClient."""

from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

from livins_report_agent.apartment_client.protocol import DataClientProtocol

logger = logging.getLogger(__name__)


def create_query_tool(client: DataClientProtocol):
    @tool
    async def query_database(sql: str) -> str:
        """Execute a read-only SQL query against the Livins property database.
        The API layer validates SQL safety (AST parsing, whitelist, timeout).

        Args:
            sql: SELECT query (e.g. "SELECT borough, AVG(price) FROM listings
                 JOIN buildings ON listings.building_id = buildings.id
                 GROUP BY borough")
        """
        try:
            result = await client.execute_query(sql)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            logger.exception("query_database failed: %s", exc)
            return json.dumps({"error": str(exc)})

    return query_database
