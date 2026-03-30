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
        logger.info("query_database ← SQL:\n%s", sql)
        try:
            result = await client.execute_query(sql)
            row_count = result.get("row_count", "?")
            columns = result.get("columns", [])
            error = result.get("error")
            if error:
                logger.warning("query_database → API error: %s", error)
            else:
                logger.info(
                    "query_database → %s rows, columns=%s", row_count, columns
                )
                # Log first 3 rows for debugging
                rows = result.get("rows", [])
                for i, row in enumerate(rows[:3]):
                    logger.debug("  row[%d]: %s", i, row)
                if len(rows) > 3:
                    logger.debug("  ... (%d more rows)", len(rows) - 3)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            logger.exception("query_database → exception: %s", exc)
            return json.dumps({"error": str(exc)})

    return query_database
