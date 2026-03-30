"""Tests for SKILL.md loading and frontmatter stripping."""

from pathlib import Path

from livins_report_agent.tools.skill import SKILLS_DIR, strip_frontmatter


def test_skills_dir_exists():
    assert SKILLS_DIR.exists()


def test_data_query_skill_exists():
    path = SKILLS_DIR / "data_query" / "SKILL.md"
    assert path.exists()


def test_chart_generation_skill_exists():
    path = SKILLS_DIR / "chart_generation" / "SKILL.md"
    assert path.exists()


def test_report_building_skill_exists():
    path = SKILLS_DIR / "report_building" / "SKILL.md"
    assert path.exists()


def test_all_skills_have_frontmatter():
    for skill_name in ["data_query", "chart_generation", "report_building"]:
        path = SKILLS_DIR / skill_name / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---"), f"{skill_name} missing frontmatter"


def test_strip_removes_frontmatter():
    for skill_name in ["data_query", "chart_generation", "report_building"]:
        path = SKILLS_DIR / skill_name / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        stripped = strip_frontmatter(content)
        assert not stripped.startswith("---"), f"{skill_name} frontmatter not stripped"
        assert len(stripped) > 100, f"{skill_name} content too short after strip"
