#!/bin/bash
# Environment initialization for agent sessions
# Reference: Anthropic "Effective Harnesses for Long-Running Agents"

set -e

# Install dependencies
pip install -e ".[dev]" --quiet

# Create reports output directory
mkdir -p reports

# Verify environment
python -c "import livins_report_agent; print('Package OK')" 2>/dev/null || echo "Package not installed yet"

echo "Environment ready. Run: USE_MOCK_CLIENT=true uvicorn livins_report_agent.main:app --reload"
