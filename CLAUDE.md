# Livins Report Agent

房源数据分析报表助手。自然语言 → 查询房源DB → 图表 → PDF/Markdown报告。

## Architecture

单 ReAct Agent + 2 Tools + Code Execution + 3 Skills，**Text-to-SQL 范式**（业界标准）。详见 `docs/architecture/`。

Agent 自己写 SQL，通过 data_service API `/query/execute` 执行。安全校验（sqlglot AST + 白名单 + 只读 + 超时）下沉到 API 层。Skills 按需加载（System Prompt 只放索引）。图表+PDF 通过 Claude Code Execution 沙盒生成。

```
ReAct Agent (langchain.agents.create_agent + init_chat_model)
├── Tool: load_skill(name)          按需加载Skill内容（Schema/规范/指南）
├── Tool: query_database(sql)       执行只读SQL（/query/execute，API层AST校验）
└── Code Execution（沙盒）           matplotlib图表 + reportlab/weasyprint PDF

Skills (索引在load_skill docstring，内容按需加载):
├── data_query/SKILL.md             Schema全量（4张表字段+关系）+ SQL编写规范
├── chart_generation/SKILL.md       图表类型选择与样式规范
└── report_building/SKILL.md        报告结构设计与PDF布局规范

后续升级方案（更快更便宜，详见 decisions.md#5）:
├── 图表: antvis/mcp-server-chart   MCP Server，26+图表类型，~1-2秒，免费
└── PDF:  Jinja2 → Playwright       warm模式13ms，无沙盒费用
```

## Import Rules

`models → config → apartment_client → tools → agent → api → main` 永不反向。

## Conversation History（Demo 阶段）

浏览器 `localStorage` 管理对话历史，服务端无状态（与 rent_agent 一致）。

- 前端每轮：`localStorage` 读历史 → 追加新消息 → POST `/chat/stream` SSE 流式推送
- 服务端：`messages` → LangChain `HumanMessage`/`AIMessage` → Agent，不存储
- Session ID：浏览器 `crypto.randomUUID()`，存 `localStorage`，随请求发送
- 后续升级：需要跨设备同步时加 LangGraph Checkpointer

详见 `docs/architecture/decisions.md` 第6条。

## Frontend

Next.js 15 (App Router, `output: 'export'`) + React 19 + Tailwind CSS v4。纯静态导出，与 FastAPI 后端分离部署。

- **Stack**：Next.js 15 / React 19 / TypeScript 5 / Tailwind v4 / react-markdown / @react-pdf-viewer/core / pnpm
- **风格**：Warm Minimal（与 rent_agent 一致）— DM Sans 字体、暖白背景 #f8f7f5、860px 居中
- **布局**：单页 split-panel — 左 Chat（58%）+ 右 PDF 预览（42%，有报告时展开）
- **流式**：SSE 流式推送工具调用步骤（tool_start/tool_end）+ 文本逐 token 输出，详见 `decisions.md#8`
- **状态**：useState + custom hooks（useChat / useLocalStorage / usePdf），无 Redux/Zustand
- **PDF**：@react-pdf-viewer/core 浏览器内渲染，blob URL 缓存，toolbar（缩放/翻页/下载）
- **测试**：Vitest + React Testing Library（组件/hook 单元测试，无浏览器 E2E）
- **目录**：`frontend/src/{app,components,hooks,lib,config}/`

详见 `docs/architecture/frontend.md`、`decisions.md#7`。

## Patterns (aligned with rent_agent)

- **Agent**: `create_agent()` + `init_chat_model()` from `langchain`
- **Tools**: Factory closures — `create_X_tool(client)` → `@tool` (from `langchain_core.tools`), 2个: load_skill/query_database + Claude Code Execution 沙盒（图表+PDF）
- **Skills**: Skill 索引通过 `load_skill` 的 docstring 自动暴露，内容按需加载，System Prompt 无 Skill 内容
- **Client**: `DataClientProtocol` (Protocol, structural typing) + Mock/Http implementations
- **DI**: `dependencies.py` — `asyncio.Lock` singletons, `Semaphore` concurrency control
- **Config**: `Pydantic BaseSettings` + `.env` via `python-dotenv`

## Commands

```bash
pip install -e ".[dev]"                    # Install
USE_MOCK_CLIENT=true uvicorn livins_report_agent.main:app --reload  # Dev
pytest tests/unit/ -v                      # Unit tests (fast, no network)
pytest tests/e2e/ -v                       # E2E tests (mock LLM, real API flow)
pytest                                     # All tests (zero failures required)
ruff check src/ tests/                     # Lint
```

## Testing

两层：`tests/unit/`（MockDataClient, 无网络）+ `tests/e2e/`（mock LLM, 真实API链路）。
详见 `docs/testing.md`。

- 零失败：每次改动后 `pytest`，必须全绿
- 镜像结构：`src/.../tools/query.py` → `tests/unit/test_tools/test_query.py`
- 先写测试再写实现

## Conventions

- Python 3.12+, async/await, Pydantic v2, type hints on public functions
- `logging` module (not print), ruff line-length=100
- pytest-asyncio (asyncio_mode="auto")

## Key Docs

- `docs/architecture/overview.md` — 系统全景、技术栈、依赖分层
- `docs/architecture/agent.md` — Agent、Tools、Skills、Client 设计
- `docs/architecture/api.md` — Endpoints、请求/响应、错误码
- `docs/architecture/frontend.md` — 前端架构：Stack、组件、状态、视觉设计
- `docs/architecture/decisions.md` — 设计决策与理由
- `docs/testing.md` — 测试策略、Unit/E2E分层、测试模式
- `docs/data_schema.md` — 4张表完整字段、常用SQL模式
- `docs/deployment.md` — 部署配置
