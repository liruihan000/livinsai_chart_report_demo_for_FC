"""ReAct Agent graph — single agent with tools, aligned with rent_agent."""

from __future__ import annotations

import logging
from typing import Annotated

from langchain_core.messages import AnyMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from livins_report_agent.apartment_client.protocol import DataClientProtocol
from livins_report_agent.config import Settings
from livins_report_agent.tools.skill import create_skill_tool
from livins_report_agent.tools.query import create_query_tool
from livins_report_agent.tools.code_execution import create_code_execution_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是 Livins 房源数据分析助手。你可以帮用户分析纽约市房源数据、生成图表和 PDF 报告。

## 工作流程
1. 用户提出分析需求时，先用 `load_skill("data_query")` 加载数据库 Schema
2. 根据 Schema 编写 SQL，用 `query_database(sql)` 查询数据
3. 需要图表时，用 `load_skill("chart_generation")` 加载图表规范
4. 需要报告时，用 `load_skill("report_building")` 加载报告规范
5. 用 `execute_code(code)` 在沙盒中执行 Python 代码生成图表和 PDF
6. 文件必须保存到 `os.getenv('OUTPUT_DIR', '.')` 才能被取回
7. 给出文字总结

## 注意事项
- 只使用 SELECT 查询，API 层会自动拒绝写操作
- 所有价格单位为美元($)，面积单位为平方英尺(sqft)
- borough 在 buildings 表，price/bedrooms 在 listings 表，需要 JOIN
- bedrooms = 0 表示 Studio
- 默认只分析 status = 'open' 的在架房源
- 用中文回复用户
- 图表和PDF报告中的所有文字必须用英文（沙盒没有中文字体，中文会显示为乱码■□）

## execute_code 硬规则（必须遵守）
- **严禁多次调用 execute_code**。每次调用都是独立沙盒，文件不互通。
- **每次分析必须生成 PDF 报告**，不能只生成图表。PDF 是最终交付物。
- 图表 + PDF 在 **同一次 execute_code** 中完成：先 plt.savefig() → 再 reportlab Image() 引用 → doc.build()。
- 所有输出文件保存到 `os.getenv('OUTPUT_DIR', '.')`。
- 只调用一次 execute_code，把所有图表和 PDF 都在一个代码块里生成。
"""


def build_llm(settings: Settings) -> BaseChatModel:
    from langchain.chat_models import init_chat_model

    return init_chat_model(settings.llm_model, api_key=settings.anthropic_api_key)


def create_all_tools(client: DataClientProtocol, settings: Settings | None = None) -> list:
    tools = [create_skill_tool(), create_query_tool(client)]
    if settings and settings.anthropic_api_key:
        model_name = settings.llm_model.split(":")[-1] if ":" in settings.llm_model else settings.llm_model
        tools.append(create_code_execution_tool(settings.anthropic_api_key, model_name))
    return tools


def build_agent_graph(
    client: DataClientProtocol,
    llm: BaseChatModel | None = None,
    settings: Settings | None = None,
):
    if settings is None:
        settings = Settings()
    if llm is None:
        llm = build_llm(settings)

    tools = create_all_tools(client, settings)
    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    return graph
