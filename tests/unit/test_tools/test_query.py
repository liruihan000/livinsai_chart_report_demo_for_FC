"""Tests for query_database tool."""

import json

import pytest

from livins_report_agent.apartment_client.mock_client import MockDataClient
from livins_report_agent.tools.query import create_query_tool


@pytest.fixture
def query_tool(mock_client):
    return create_query_tool(mock_client)


async def test_select_query(query_tool):
    result = await query_tool.ainvoke({
        "sql": "SELECT borough, AVG(price) FROM listings JOIN buildings ON listings.building_id = buildings.id GROUP BY borough"
    })
    data = json.loads(result)
    assert "columns" in data
    assert "rows" in data


async def test_write_query_rejected(query_tool):
    result = await query_tool.ainvoke({"sql": "DROP TABLE listings"})
    data = json.loads(result)
    assert "error" in data


async def test_result_is_json_string(query_tool):
    result = await query_tool.ainvoke({
        "sql": "SELECT * FROM listings LIMIT 5"
    })
    # Should be valid JSON string
    data = json.loads(result)
    assert isinstance(data, dict)
