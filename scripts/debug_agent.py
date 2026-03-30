"""Debug script — run agent with full logging, print every step."""

import asyncio
import json
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# Full logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)

from livins_report_agent.config import Settings
from livins_report_agent.apartment_client import HttpDataClient, MockDataClient
from livins_report_agent.agent.graph import build_agent_graph
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


async def main():
    settings = Settings()
    print(f"\n{'='*60}")
    print(f"Model: {settings.llm_model}")
    print(f"Mock: {settings.use_mock_client}")
    print(f"Data Service: {settings.data_service_url}")
    print(f"Max Steps: {settings.max_agent_steps}")
    print(f"{'='*60}\n")

    if settings.use_mock_client:
        client = MockDataClient()
    else:
        client = HttpDataClient(settings.data_service_url)

    graph = build_agent_graph(client, settings=settings)

    query = sys.argv[1] if len(sys.argv) > 1 else "分析纽约各区的平均租金"

    print(f"User: {query}\n")

    step = 0
    async for event in graph.astream_events(
        {"messages": [HumanMessage(content=query)]},
        config={"recursion_limit": settings.max_agent_steps},
        version="v2",
    ):
        kind = event.get("event")
        name = event.get("name", "")

        if kind == "on_tool_start":
            step += 1
            tool_input = event.get("data", {}).get("input", {})
            print(f"\n{'─'*60}")
            print(f"Step {step} | Tool: {name}")
            if name == "query_database":
                print(f"  SQL: {tool_input.get('sql', '')}")
            elif name == "load_skill":
                print(f"  Skill: {tool_input.get('name', '')}")
            elif name == "execute_code":
                code = tool_input.get("code", "")
                print(f"  Code ({len(code)} chars): {code[:200]}...")
            else:
                print(f"  Input: {str(tool_input)[:300]}")

        elif kind == "on_tool_end":
            output = event.get("data", {}).get("output", "")
            content = output.content if hasattr(output, "content") else str(output)
            # Truncate long output
            if len(content) > 500:
                print(f"  Result ({len(content)} chars): {content[:500]}...")
            else:
                print(f"  Result: {content}")

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, str):
                    print(content, end="", flush=True)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            print(block["text"], end="", flush=True)

    print(f"\n\n{'='*60}")
    print(f"Done. Total tool calls: {step}")


if __name__ == "__main__":
    asyncio.run(main())
