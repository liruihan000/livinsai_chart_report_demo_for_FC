"""Tests for load_skill tool."""

import pytest

from livins_report_agent.tools.skill import create_skill_tool, strip_frontmatter


@pytest.fixture
def skill_tool():
    return create_skill_tool()


async def test_load_data_query(skill_tool):
    result = await skill_tool.ainvoke({"name": "data_query"})
    assert "buildings" in result
    assert "listings" in result
    # Frontmatter should be stripped
    assert "---" not in result.split("\n")[0]


async def test_load_chart_generation(skill_tool):
    result = await skill_tool.ainvoke({"name": "chart_generation"})
    assert "Chart Generation" in result
    assert "matplotlib" in result


async def test_load_report_building(skill_tool):
    result = await skill_tool.ainvoke({"name": "report_building"})
    assert "Report Building" in result
    assert "reportlab" in result


async def test_invalid_skill(skill_tool):
    result = await skill_tool.ainvoke({"name": "nonexistent"})
    assert "Error" in result or "not found" in result


def test_strip_frontmatter():
    text = "---\nname: test\n---\n# Content"
    assert strip_frontmatter(text) == "# Content"


def test_strip_frontmatter_no_frontmatter():
    text = "# Just content"
    assert strip_frontmatter(text) == "# Just content"
