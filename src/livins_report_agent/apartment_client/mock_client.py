"""MockDataClient — in-memory fake for dev/test. No network calls."""

from __future__ import annotations

import re


# Static sample data keyed by simple heuristics on the SQL text.
_BOROUGH_STATS = {
    "columns": ["borough", "avg_price", "min_price", "max_price", "count"],
    "rows": [
        ["Manhattan", 3500, 2100, 8500, 2341],
        ["Brooklyn", 2700, 1800, 5200, 1876],
        ["Queens", 2200, 1400, 4100, 1203],
        ["Bronx", 1800, 1100, 3200, 654],
        ["Staten Island", 1600, 1000, 2800, 321],
    ],
    "row_count": 5,
}

_TREND_DATA = {
    "columns": ["borough", "month", "avg_price", "count"],
    "rows": [
        ["Manhattan", "2026-01", 3450, 892],
        ["Manhattan", "2026-02", 3520, 910],
        ["Manhattan", "2026-03", 3480, 875],
        ["Brooklyn", "2026-01", 2680, 712],
        ["Brooklyn", "2026-02", 2720, 735],
        ["Brooklyn", "2026-03", 2690, 700],
    ],
    "row_count": 6,
}

_ML_STATS = {
    "columns": ["condition_level", "avg_aesthetic_score", "avg_price"],
    "rows": [
        [1, 3.2, 2100],
        [2, 4.5, 2500],
        [3, 5.8, 3000],
        [4, 7.1, 3800],
        [5, 8.6, 4500],
    ],
    "row_count": 5,
}

_DEFAULT = {
    "columns": ["id", "borough", "price", "bedrooms"],
    "rows": [
        [1, "Manhattan", 3200, 1],
        [2, "Brooklyn", 2600, 1],
        [3, "Queens", 2100, 2],
    ],
    "row_count": 3,
}

_WRITE_PATTERN = re.compile(
    r"\b(DROP|INSERT|UPDATE|DELETE|CREATE|ALTER|TRUNCATE)\b", re.IGNORECASE
)


class MockDataClient:
    """In-memory mock that returns static data based on SQL heuristics."""

    async def execute_query(self, sql: str) -> dict:
        upper = sql.upper()

        if _WRITE_PATTERN.search(sql):
            return {"error": "Only SELECT queries allowed"}

        if "DATE_TRUNC" in upper or "TREND" in upper:
            return _TREND_DATA
        if "CONDITION_LEVEL" in upper or "AESTHETIC" in upper or "ML_LISTINGS" in upper:
            return _ML_STATS
        if "GROUP BY" in upper and "BOROUGH" in upper:
            return _BOROUGH_STATS
        return _DEFAULT
