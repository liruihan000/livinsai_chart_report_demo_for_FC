"""load_skill tool — on-demand skill loading via factory closure."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def create_skill_tool():
    @tool
    async def load_skill(name: str) -> str:
        """Load a skill guide on demand. Available skills:
        - data_query: DB schema (4 tables, columns, relationships) + SQL patterns
        - chart_generation: chart type selection + style specs
        - report_building: report structure + PDF layout specs

        Args:
            name: skill name (e.g. "data_query")
        """
        logger.info("load_skill ← %s", name)
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            logger.warning("load_skill → skill '%s' not found", name)
            return f"Error: skill '{name}' not found. Available: data_query, chart_generation, report_building"
        content = path.read_text(encoding="utf-8")
        result = strip_frontmatter(content)
        logger.info("load_skill → %s (%d chars)", name, len(result))
        return result

    return load_skill
