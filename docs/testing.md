# Testing

> Aligned with rent_agent testing patterns. 不含 LLM benchmark — 只覆盖确定性逻辑。

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                     共享 fixtures: mock_client, settings
│
├── unit/                           单元测试 — 无网络、无LLM调用
│   ├── __init__.py
│   ├── test_models.py              Pydantic 模型校验
│   ├── test_config.py              Settings 加载
│   ├── test_client.py              MockDataClient 行为
│   ├── test_tools/
│   │   ├── __init__.py
│   │   ├── test_skill.py           load_skill: 加载存在/不存在的skill、frontmatter剥离
│   │   └── test_query.py           query_database: SQL执行、安全校验拒绝、结果格式
│   ├── test_skills/
│   │   ├── __init__.py
│   │   └── test_skills_prompt.py   SKILL.md加载、frontmatter剥离
│   └── test_agent/
│       ├── __init__.py
│       └── test_graph.py           Agent graph编译（不执行LLM）
│
└── e2e/                            端到端测试
    ├── __init__.py
    ├── test_chat_flow.py           POST /chat → 回复（mock LLM）
    ├── test_report_download.py     报告下载 + 跨endpoint链路（mock Files API）
    ├── test_frontend_contract.py   前端契约测试 — API响应匹配前端类型
    └── test_real_agent.py          真实E2E — 真LLM + Code Execution（需API Key）
```

## 两层测试

### Unit Tests — 快、隔离、零网络

**原则**：所有 unit test 使用 `MockDataClient`，不调网络、不调LLM。

```bash
pytest tests/unit/ -v                    # 跑全部 unit
pytest tests/unit/test_tools/ -v         # 只跑 tools
```

**每个 Tool 测什么**：

| Tool | Happy Path | Edge Cases |
|------|-----------|------------|
| `load_skill` | 有效skill名返回内容，frontmatter已剥离 | 无效skill名报错 |
| `query_database` | 有效SELECT返回数据 | 写操作被拒绝、非白名单表被拒绝、API超时 |

**Tool 测试模式**（和 rent_agent 一致）：
```python
# tests/unit/test_tools/test_query.py
@pytest.fixture
def query_tool(mock_client):
    return create_query_tool(mock_client)

async def test_select_query(query_tool):
    result = await query_tool.ainvoke({
        "sql": "SELECT borough, AVG(price) FROM listings JOIN buildings ON listings.building_id = buildings.id GROUP BY borough"
    })
    data = json.loads(result)
    assert "columns" in data
    assert "rows" in data

async def test_write_query_rejected(query_tool):
    result = await query_tool.ainvoke({"sql": "DROP TABLE listings"})
    assert "error" in result.lower()
```

### E2E Tests — Mock LLM，真实API流程

**原则**：mock `get_graph` 返回预设 AIMessage，验证整条 API 链路（HTTP 进 → HTTP 出）。不调真实LLM。

**边界**：路由可达、请求校验、正常链路、异常链路、并发控制。SQL 安全校验在 data_service 层测试，Tool 逻辑在 unit tests 覆盖，均不在 e2e 重复。

```bash
pytest tests/e2e/ -v
```

#### POST /chat（test_chat_flow.py）

| 测试 | 验证 |
|------|------|
| `test_health` | GET /health → 200, `{"status": "ok"}` |
| `test_chat_success` | POST /chat → 200, response 含 reply + session_id |
| `test_chat_generates_session_id` | 不传 session_id → 自动生成 UUID |
| `test_chat_empty_messages` | 空 messages → 422 |
| `test_chat_invalid_role` | role="system" → 422 |
| `test_chat_missing_messages_field` | 请求体缺 messages 字段 → 422 |
| `test_chat_multi_turn` | 多轮 messages（user/assistant 交替）→ Agent 收到完整上下文 |
| `test_chat_with_files` | mock Agent 返回含 file 附件 → response 中 files 字段正确 |
| `test_chat_agent_error` | mock `graph.ainvoke` 抛异常 → 500 + error 信息 |
| `test_chat_agent_empty_response` | mock 返回空 messages → 500 |
| `test_chat_concurrency_limit` | 并发 `max_concurrent_invocations + 1` 请求 → Semaphore 生效（排队/限流） |

#### GET /reports/{file_id}（test_report_download.py）

| 测试 | 验证 |
|------|------|
| `test_report_not_found` | 不存在的 file_id → 404（或 501 若 SDK 未装） |
| `test_report_download_success` | mock Anthropic Files API → 200, Content-Type=application/pdf, Content-Disposition 含文件名 |
| `test_report_streaming` | 验证返回 StreamingResponse，body 非空 |
| `test_report_sdk_not_installed` | mock anthropic import 失败 → 501 |

#### 跨 endpoint 流程

| 测试 | 验证 |
|------|------|
| `test_chat_then_download` | POST /chat 返回 file_id → GET /reports/{file_id} 下载成功（完整链路） |

**E2E 测试模式**（和 rent_agent test_chat.py 一致）：
```python
# tests/e2e/test_chat_flow.py
@pytest.fixture
async def app_client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

async def test_chat_success(app_client):
    mock_response = {"messages": [AIMessage(content="曼哈顿一居室均价$3,500...")]}
    with patch("livins_report_agent.dependencies.get_graph", new_callable=AsyncMock) as mock_get_graph:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = mock_response
        mock_get_graph.return_value = mock_graph
        resp = await app_client.post("/chat", json={
            "messages": [{"role": "user", "content": "分析曼哈顿租金"}]
        })
        assert resp.status_code == 200
        assert "reply" in resp.json()
```

### Frontend Contract Tests — API 响应匹配前端类型

**文件**：`tests/e2e/test_frontend_contract.py`

**原则**：验证后端 API 响应 shape 与前端 `types.ts`（ChatResponse, FileRef）完全一致。前端静态部署、后端独立迭代，契约测试防止两端 drift。

| 测试 | 验证 |
|------|------|
| `test_response_has_all_frontend_fields` | 响应包含 reply(str), session_id(str), files(null\|list)，字段名匹配前端 ChatResponse |
| `test_response_files_shape_when_present` | files 数组元素包含 file_id + filename，匹配前端 FileRef |
| `test_session_id_round_trip` | 前端发 session_id，服务端原样回传 |
| `test_session_id_auto_generated_when_missing` | 首次请求无 session_id，服务端生成 UUID 返回 |
| `test_multi_turn_messages` | 前端发完整 messages[] 历史（localStorage 模式），服务端正确处理 |
| `test_report_endpoint_returns_404_for_unknown_file` | GET /reports/{file_id} 未知 ID → 404 |
| `test_empty_content_rejected` | 空 content → 422 |
| `test_missing_messages_rejected` | 缺 messages 字段 → 422 |

```bash
pytest tests/e2e/test_frontend_contract.py -v
```

### Data Service Tests — `/query/execute` SQL 安全校验

`/query/execute` 是 data_service 层新增的通用 SQL 执行 endpoint，供 Report Agent 的 Text-to-SQL 使用。测试文件在 data_service 仓库内：

```
white_forest/backend/data_service/test/
└── test_query_execute.py
    ├── TestValidateSqlAllowed     (9 tests) — 合法 SELECT 通过校验
    ├── TestValidateSqlBlocked     (10 tests) — 写操作/非白名单表/多语句 被拒绝
    └── TestQueryExecuteAPI        (9 tests) — 集成测试（需 data_service 运行）
```

**单元测试**（纯 `_validate_sql` 函数，无需服务器/数据库）：
```bash
cd ~/white_forest/backend
pytest data_service/test/test_query_execute.py::TestValidateSqlAllowed -v
pytest data_service/test/test_query_execute.py::TestValidateSqlBlocked -v
```

**集成测试**（需 data_service 运行在 localhost:8002）：
```bash
pytest data_service/test/test_query_execute.py::TestQueryExecuteAPI -v
```

| 测试类 | 覆盖内容 |
|--------|----------|
| `TestValidateSqlAllowed` | SELECT、JOIN、子查询、DATE_TRUNC、4表联查 |
| `TestValidateSqlBlocked` | DROP/INSERT/UPDATE/DELETE/CREATE/ALTER 拒绝、非白名单表拒绝、多语句拒绝 |
| `TestQueryExecuteAPI` | 区域聚合、趋势查询、ML特征查询、自动LIMIT、错误拒绝 |

### Real E2E Tests — 真实 LLM + Code Execution（test_real_agent.py）

**文件**：`tests/e2e/test_real_agent.py`

**前提**：需要 `ANTHROPIC_API_KEY` 设置在 `.env` 中。无 API Key 时自动 skip。使用 MockDataClient（不需要 data_service 运行）。

```bash
pytest tests/e2e/test_real_agent.py -v -s    # 需要 API Key，耗时 ~3 分钟
```

| 测试类 | 测试 | 验证 |
|--------|------|------|
| `TestRealAgentDataQuery` | `test_simple_analysis` | 真实 LLM 加载 skill → 写 SQL → 查询数据 → 返回包含 borough 的分析 |
| `TestRealAgentDataQuery` | `test_multi_turn_conversation` | 多轮对话历史正确传递给 Agent |
| `TestRealAgentChartGeneration` | `test_generate_chart` | Agent 调 `execute_code` → Code Execution 沙盒生成图表 → 返回 file_id |
| `TestRealAgentPdfReport` | `test_generate_pdf_report` | Agent 生成 PDF → file_id → GET `/reports/{file_id}` 下载成功 |
| `TestRealAgentFullFlow` | `test_full_analysis_report` | 完整流程：skill → SQL → chart → PDF → 文字总结 |

**架构**：Agent (LangGraph ReAct) 处理推理 + 工具调用，`execute_code` tool 内部用 Anthropic SDK 调 Code Execution 沙盒（`code_execution_20250522`），文件保存到 `OUTPUT_DIR` 后通过 Files API 取回 `file_id`。

## Commands

```bash
# 全部测试（不含 real agent）
pytest --ignore=tests/e2e/test_real_agent.py

# 只跑 unit（快，CI用）
pytest tests/unit/ -v

# 只跑 e2e（mock）
pytest tests/e2e/ -v --ignore=tests/e2e/test_real_agent.py

# 真实 E2E（需 API Key，慢）
pytest tests/e2e/test_real_agent.py -v -s

# 带覆盖率
pytest --cov=livins_report_agent --cov-report=term-missing

# 单个文件
pytest tests/unit/test_tools/test_query.py -v
```

## Frontend Tests — Vitest + React Testing Library

前端只做组件/hook 级别的单元测试，不做浏览器 E2E（Demo 阶段 Playwright 维护成本过高）。

```
frontend/__tests__/
├── setup.ts                     Vitest setup（jest-dom matchers）
├── hooks/
│   ├── useChat.test.ts          消息发送、loading 状态、清除历史、files 处理
│   ├── useLocalStorage.test.ts  读写 localStorage、JSON 异常处理
│   └── usePdf.test.ts           blob URL 生命周期、下载触发
└── components/
    ├── ChatContainer.test.tsx   空态渲染、消息列表、loading dots
    ├── MessageBubble.test.tsx   user/assistant 对齐、Markdown 渲染
    └── PdfPanel.test.tsx        PDF viewer 渲染、关闭/下载按钮
```

```bash
cd frontend
pnpm test                        # 跑全部（vitest run）
pnpm test:watch                  # watch 模式
```

**测试模式**：
- mock `fetch`（`vi.stubGlobal`）模拟 API 响应
- mock `localStorage`（jsdom 自带）
- mock `URL.createObjectURL` / `revokeObjectURL`

## 规则

1. **零失败**：后端 `pytest`、前端 `pnpm test`，必须全绿
2. **镜像结构**：`src/.../tools/query.py` → `tests/unit/test_tools/test_query.py`；`src/hooks/useChat.ts` → `__tests__/hooks/useChat.test.ts`
3. **MockDataClient**：后端 unit tests 永远不碰网络
4. **成功静默**：只输出失败信息（harness engineering原则：不撑爆context window）
5. **先写测试再写实现**：新 Tool/Skill/Hook/Component 先写 test，再写代码
