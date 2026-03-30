# Architecture Overview

Livins Report Agent — 房源数据分析报表助手。自然语言 → 查询房源DB → 图表 → PDF/Markdown报告。

## 设计哲学

1. **Agent 只做推理** — 理解意图、探索 Schema、写 SQL、分析数据、设计报告结构
2. **安全校验下沉到 API 层** — SQL AST 校验、白名单、只读、超时，Agent 不感知
3. **Skill 按需加载** — System Prompt 只放索引，Agent 通过 `load_skill` 按需获取 Schema/规范
4. **Agent 决定"做什么"，Skill 封装"怎么做"** — 报告结构由 Agent 动态决定
5. **浏览器管状态，服务端管推理** — 对话历史由浏览器 localStorage 管理，服务端无状态（与 rent_agent 一致）

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Client (Browser)                                       │
│  localStorage: messages[] + session_id                  │
│  每轮对话: 读取历史 → 追加新消息 → POST /chat 发送全量  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  FastAPI Backend                                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │  ReAct Agent (LangGraph)                          │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │ Thought → Action → Observation → Thought ... │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  │       │          │          │                        │ │
│  │       ▼          ▼          ▼                        │ │
│  │  load        query       Code Execution             │ │
│  │  _skill      _database   (Anthropic沙盒)            │ │
│  └──────┼──────────┼──────────┼────────────────────────┘ │
│         │          │          │                           │
│  ┌──────▼──────────▼──────────▼────────────────────────┐ │
│  │  Tool Layer (Skill加载, SQL执行, 图表+PDF沙盒生成)   │ │
│  └──────────────────┬──────────────────────────────────┘ │
└─────────────────────┼──────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│  Livins AI Data Service (PostgreSQL + PostGIS)         │
│  Tables: buildings, listings, ml_listings, isochrones  │
└────────────────────────────────────────────────────────┘
```

## Dependency Layering

```
models → config → apartment_client → tools → agent → api → main
```

只能向左导入，永远不能反向。

## Technology Stack

### 核心（aligned with rent_agent）
| 包 | 版本 |
|----|------|
| `langgraph`, `langchain`, `langchain-core` | >=0.4, >=0.3 |
| `langchain-anthropic`, `langchain-openai` | >=0.3 |
| `fastapi`, `uvicorn[standard]` | >=0.115, >=0.34 |
| `httpx`, `pydantic`, `pydantic-settings` | >=0.28, >=2.0 |

### 报表专用（Demo 阶段）
| 方案 | 说明 |
|----|------|
| LLM Code Execution 沙盒 | matplotlib 图表 + reportlab/weasyprint PDF，Anthropic 托管，零运维 |
| 后续升级 | antvis/mcp-server-chart（图表）+ Jinja2 + Playwright（PDF），详见 `decisions.md#5` |

## Observability

- **LangSmith / Arize AI**：追踪 Thought-Action-Observation
- **Structured Logging**：Tool 调用记录输入/输出/耗时
- **Metrics**：Token usage, tool call count, latency P50/P95, SQL validation rejection rate

## References

- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Anthropic: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [INSART: AI-Assisted Report Generation with LLM](https://insart.com/ai-assisted-report-generation-langchain-fastapi-anthropic-claude/)
- [Anthropic Skills for Text-to-SQL](https://medium.com/@shakthiram7787/anthropic-skills-for-text-to-sql-what-i-learned-building-a-skills-anchored-chat-agent-7edf0c5bb188)
- [Anthropic Official Skills](https://github.com/anthropics/skills)
- [molefrog/react-pdf Skill](https://github.com/molefrog/skills)
