"""Tests for MockDataClient."""

import pytest

from livins_report_agent.apartment_client.mock_client import MockDataClient


@pytest.fixture
def client():
    return MockDataClient()


async def test_select_returns_data(client):
    result = await client.execute_query(
        "SELECT borough, AVG(price) FROM listings JOIN buildings ON listings.building_id = buildings.id GROUP BY borough"
    )
    assert "columns" in result
    assert "rows" in result
    assert "row_count" in result
    assert result["row_count"] > 0


async def test_trend_query(client):
    result = await client.execute_query(
        "SELECT DATE_TRUNC('month', listed_at), AVG(price) FROM listings GROUP BY 1"
    )
    assert "month" in result["columns"][1] or result["row_count"] > 0


async def test_ml_query(client):
    result = await client.execute_query(
        "SELECT condition_level, AVG(aesthetic_score) FROM ml_listings GROUP BY condition_level"
    )
    assert result["row_count"] == 5


async def test_write_query_rejected(client):
    result = await client.execute_query("DROP TABLE listings")
    assert "error" in result


async def test_insert_rejected(client):
    result = await client.execute_query("INSERT INTO listings (price) VALUES (100)")
    assert "error" in result


async def test_default_fallback(client):
    result = await client.execute_query("SELECT * FROM listings LIMIT 5")
    assert "columns" in result
    assert result["row_count"] > 0
