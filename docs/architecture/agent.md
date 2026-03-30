# Agent Design

## ReAct Agent

**职责**：推理循环 — 理解意图 → 加载所需Skill → 写SQL查询 → 分析数据 → 选择图表 → 设计报告结构

**实现**（aligned with rent_agent）：
```python
# agent/graph.py
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

def build_llm(settings: Settings) -> BaseChatModel:
    return init_chat_model(settings.llm_model, api_key=settings.anthropic_api_key)

def build_agent_graph(client, llm=None, settings=None):
    tools = create_all_tools(client)
    system_prompt = build_system_prompt()  # Skills通过load_skill tool的docstring暴露
    return create_agent(model=llm, tools=tools, system_prompt=system_prompt)
```

**State**：
```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: int
```

**模型配置**：`init_chat_model("provider:model")`
- 生产：`anthropic:claude-sonnet-4-20250514` / `openai:gpt-4o`
- 开发：`anthropic:claude-haiku-4-5-20251001`

## DI & Concurrency

Singleton pattern with `asyncio.Lock`，和 rent_agent 一致：

```python
# dependencies.py
_graph: CompiledStateGraph | None = None
_graph_lock = asyncio.Lock()
_invoke_semaphore: asyncio.Semaphore | None = None

async def get_graph() -> CompiledStateGraph:
    global _graph
    if _graph is not None:
        return _graph
    async with _graph_lock:
        if _graph is None:
            _graph = build_agent_graph(...)
    return _graph
```

## Tools (2个 + Code Execution)

**Text-to-SQL 范式**：Agent 自己写 SQL，通过 data_service API 的 `/query/execute` endpoint 执行。安全校验（AST解析、白名单、只读、超时）下沉到 API 层，Agent 不感知。

Factory Closure Pattern — `create_X_tool(client)` → `@tool` 闭包：

```python
def create_skill_tool():
    @tool
    async def load_skill(name: str) -> str:
        """Load a skill guide on demand. Available skills:
        - data_query: DB schema + SQL patterns
        - chart_generation: chart type selection + style specs
        - report_building: report structure + PDF layout specs

        Args:
            name: skill name (e.g. "data_query")
        """
        path = SKILLS_DIR / name / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        return strip_frontmatter(content)
    return load_skill

def create_query_tool(client: DataClientProtocol):
    @tool
    async def query_database(sql: str) -> str:
        """Execute a read-only SQL query against the Livins property database.
        The API layer validates SQL safety (AST parsing, whitelist, timeout).

        Args:
            sql: SELECT query (e.g. "SELECT borough, AVG(price) FROM listings
                 JOIN buildings ON listings.building_id = buildings.id
                 GROUP BY borough")
        """
        result = await client.execute_query(sql)
        return json.dumps(result)
    return query_database
```

| Tool | 输入 | 输出 | 用途 |
|------|------|------|------|
| `load_skill(name)` | skill名称 | Skill内容（Markdown） | 按需加载Schema/规范/指南 |
| `query_database(sql)` | SELECT SQL | 查询结果 JSON | 所有数据查询（聚合、JOIN、子查询） |
| Code Execution（沙盒） | LLM 自动生成 Python 代码 | 文件（PNG/PDF） | 图表生成 + PDF 报告组装 |

> **Demo 阶段**：图表和 PDF 通过 LLM `code_execution_20250825` 沙盒生成（matplotlib + reportlab/weasyprint），通过 Files API 取回。
>
> **后续升级**：图表改用 [antvis/mcp-server-chart](https://github.com/antvis/mcp-server-chart)（更快、免费），PDF 改用 Jinja2 + Playwright（warm 模式 13ms）。详见 `decisions.md` 第5条。

### 为什么用 Text-to-SQL？（业界标准范式）

这是 Databricks AI/BI、Snowflake Cortex Analyst、AWS QuickSight Q 等主流产品采用的方案。

- **灵活**：任意聚合/JOIN/子查询，不需要为每种分析需求预定义 endpoint
- **业界验证**：Spider/Bird benchmark + 大厂产品验证了 LLM 写 SQL 的可靠性
- **安全可控**：校验逻辑下沉到 API 层（sqlglot AST + 白名单表 + 只读 + 超时 + 行数限制）
- **Skill 按需加载**：Agent 需要时才加载 Schema 和规范，不占 System Prompt token

### 安全校验（在 data_service API 层实现）

```python
# data_service 侧 — POST /query/execute
def validate_sql(sql: str) -> None:
    """AST-level SQL validation. Raises ValueError on unsafe queries."""
    tree = sqlglot.parse_one(sql)
    # 1. 必须是 SELECT
    if not isinstance(tree, exp.Select):
        raise ValueError("Only SELECT queries allowed")
    # 2. 禁止写操作
    for node_type in (exp.Drop, exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Alter):
        if tree.find(node_type):
            raise ValueError(f"{node_type.__name__} not allowed")
    # 3. 白名单表
    tables = {t.name for t in tree.find_all(exp.Table)}
    allowed = {"buildings", "listings", "ml_listings", "building_isochrones"}
    if not tables.issubset(allowed):
        raise ValueError(f"Unauthorized tables: {tables - allowed}")
    # 4. 只读连接 + 超时 + 行数限制（在执行层）
```

### data_service API 需要新增的 Endpoint

| Endpoint | Method | 请求体 | 返回 | 说明 |
|----------|--------|--------|------|------|
| `/query/execute` | POST | `{"sql": "SELECT ..."}` | `{"columns": [...], "rows": [...], "row_count": N}` | 执行只读 SQL，内置 AST 校验 |

## Skills (SKILL.md) — 按需加载

**System Prompt 不包含任何 Skill 内容。** Skill 索引通过 `load_skill` Tool 的 docstring 自动暴露给 LLM：

```python
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
        path = SKILLS_DIR / name / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        return strip_frontmatter(content)
    return load_skill
```

LangGraph 自动将 Tool 的函数签名 + docstring 暴露给 LLM，无需在 System Prompt 中重复。

| Skill | 按需加载的内容 |
|-------|----------------|
| `data_query/SKILL.md` | 4张表完整字段+类型+关系 + JOIN路径 + SQL编写规范 + 常用查询模式 |
| `chart_generation/SKILL.md` | 图表类型选择（趋势→line, 对比→bar, 分布→pie）、样式规范 |
| `report_building/SKILL.md` | 报告结构设计、PDF布局规范 |

## Client Abstraction

Protocol-based（structural typing）：

```python
class DataClientProtocol(Protocol):
    async def execute_query(self, sql: str) -> dict: ...
```

| 实现 | 用途 | 说明 |
|------|------|------|
| `MockDataClient` | Dev/Test | 内存中模拟查询结果 |
| `HttpDataClient` | Production | `httpx.AsyncClient` → data_service `/query/execute` |

## Conversation History（Demo 阶段）

**浏览器管状态，服务端管推理。** 对话历史存浏览器 localStorage，每轮请求携带完整消息数组，服务端不持久化（与 rent_agent 一致）。

```
浏览器 (localStorage)                      服务端 (Stateless)
┌──────────────────────┐                  ┌──────────────────────┐
│ localStorage:        │   POST /chat     │ ChatRequest:         │
│  messages[]          │ ─────────────→   │  messages[]          │
│  session_id          │  {messages,      │  session_id          │
│                      │   session_id}    │                      │
│ 每轮对话:            │                  │ 转换:                │
│ 1. 读历史            │                  │ messages → [         │
│ 2. 追加新消息        │                  │   HumanMessage(...), │
│ 3. 发送全量          │   ChatResponse   │   AIMessage(...),    │
│ 4. 收到回复存回      │ ←─────────────   │ ] → Agent.invoke()   │
│                      │  {reply,         │                      │
│ 清除: 清空 localStorage│  session_id}   │ 不存储任何对话历史    │
└──────────────────────┘                  └──────────────────────┘
```

**与 rent_agent 一致**：相同的 localStorage 模式，相同的无状态服务端设计。

## 文件交付（图表/PDF，harness engineering）

**Anthropic Files API 是临时中转，不是存储。** 服务端立即取回文件，转发给前端。

```
Code Execution 沙盒                服务端 (Stateless)               浏览器
┌─────────────────┐              ┌─────────────────────┐         ┌──────────────┐
│ matplotlib →    │              │                     │         │              │
│   chart.png     │  file_id     │ Files API 取回文件   │  响应    │ Blob URL     │
│ reportlab →     │ ──────────→  │ （立即下载，不依赖   │ ──────→ │ 触发下载      │
│   report.pdf    │              │  30天有效期）        │         │ 或内联预览    │
│                 │              │                     │         │              │
│ 容器30天后过期   │              │ 两种交付方式:        │         │ localStorage │
│ 文件随容器删除   │              │ A. 流式转发(推荐Demo)│         │ 只存 file_id │
└─────────────────┘              │ B. 存临时目录+URL   │         │ 不存文件本身  │
                                 └─────────────────────┘         └──────────────┘
```

**Demo 实现（流式转发，最简单）**：
```python
@app.get("/reports/{file_id}")
async def download_report(file_id: str):
    file_metadata = anthropic_client.beta.files.retrieve_metadata(file_id)
    file_content = anthropic_client.beta.files.download(file_id)
    return StreamingResponse(
        file_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={file_metadata.filename}"}
    )
```

**前端**：对话历史中存文件引用（`{type: "file", file_id, filename}`），点击时请求 `/reports/{file_id}` 下载。

**原则**：
- Anthropic Files API 当中转，服务端收到 `file_id` 后立即可用，不缓存不持久化
- `localStorage` 只存文本消息和文件引用（file_id + filename），不存二进制
- 后续升级：需要持久化文件时，服务端取回后存 S3/MinIO，返回自己的 URL

## Data Flow Example

```
用户: "分析曼哈顿一居室过去3个月的租金趋势，对比布鲁克林"

Thought: 需要写SQL查询，先加载数据库Schema和SQL规范
Action: load_skill("data_query")
→ (返回完整Schema：4张表字段+关系+JOIN路径+SQL规范)

Thought: 需要按月聚合曼哈顿和布鲁克林一居室的均价
Action: query_database(
  "SELECT b.borough, DATE_TRUNC('month', l.listed_at) AS month,
          AVG(l.price) AS avg_price, COUNT(*) AS count
   FROM listings l JOIN buildings b ON l.building_id = b.id
   WHERE b.borough IN ('Manhattan', 'Brooklyn')
     AND l.bedrooms = 1
     AND l.listed_at >= CURRENT_DATE - INTERVAL '3 months'
   GROUP BY b.borough, month ORDER BY month"
)
→ [{borough: "Manhattan", month: "2026-01", avg_price: 3450, count: 892}, ...]

Thought: 生成图表前加载图表规范
Action: load_skill("chart_generation")
→ (返回图表类型选择指南+样式规范)

Thought: 再查价格分布对比数据
Action: query_database(
  "SELECT b.borough, AVG(l.price) AS avg, MIN(l.price) AS min,
          MAX(l.price) AS max, COUNT(*) AS count
   FROM listings l JOIN buildings b ON l.building_id = b.id
   WHERE l.bedrooms = 1 GROUP BY b.borough"
)
→ [{borough: "Manhattan", avg: 3500, min: 2100, max: 8500, count: 2341}, ...]

Thought: 加载报告规范，然后用 Code Execution 一次性生成图表和PDF
Action: load_skill("report_building")
→ (返回报告结构+PDF布局规范)

Thought: 在沙盒中用之前查到的数据生成图表和PDF报告
Action: code_execution("""
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer

# 数据来自前面 query_database 的返回（Agent 自动将 JSON 写入代码）
trend_data = [
    {"borough": "Manhattan", "month": "2026-01", "avg_price": 3450},
    {"borough": "Manhattan", "month": "2026-02", "avg_price": 3520},
    {"borough": "Brooklyn", "month": "2026-01", "avg_price": 2680},
    ...
]
compare_data = [
    {"borough": "Manhattan", "avg": 3500, "min": 2100, "max": 8500},
    {"borough": "Brooklyn", "avg": 2700, "min": 1800, "max": 5200},
]

# 1. 生成趋势折线图（存容器磁盘）
plt.figure()
plt.plot(months, manhattan, label='Manhattan')
plt.plot(months, brooklyn, label='Brooklyn')
plt.savefig('chart_trend.png')

# 2. 生成区域对比柱状图（存容器磁盘）
plt.figure()
plt.bar(boroughs, avg_prices)
plt.savefig('chart_compare.png')

# 3. 组装 PDF（引用容器内的图片文件）
doc = SimpleDocTemplate('report.pdf', pagesize=A4)
doc.build([title, summary, Image('chart_trend.png'), analysis,
           Image('chart_compare.png'), recommendation])
""")
→ 响应包含 file_id 列表: [file_trend, file_compare, file_report]

--- 以下是 Harness（服务端）处理，Agent 不感知 ---

服务端: 从响应中提取 file_id，返回给前端
→ ChatResponse: {reply: "报告已生成，包含租金趋势和区域对比分析",
                 files: [{file_id: "file_xxx", filename: "report.pdf"}]}

前端: localStorage 存消息 + 文件引用，展示下载按钮
→ 用户点击下载 → GET /reports/file_xxx → 服务端流式转发 → 浏览器下载 report.pdf
```
