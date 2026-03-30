# API Documentation

## Endpoints

### Health Check

```
GET /health
Response: {"status": "ok"}
```

### Chat

对话入口。发送完整消息历史，返回 Agent 回复和可能的报告下载链接。

**服务端无状态** — 不持久化对话历史。每次请求携带完整 `messages` 数组，服务端转为 LangChain 消息后喂给 Agent（详见 `decisions.md` 第7条）。

```
POST /chat
```

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "分析曼哈顿一居室的租金趋势"},
    {"role": "assistant", "content": "根据分析..."},
    {"role": "user", "content": "再对比布鲁克林的数据"}
  ],
  "session_id": "uuid-from-browser"
}
```

> **对话历史由浏览器管理**：前端从 `localStorage` 读取历史 → 追加新消息 → 完整发送。服务端不存储任何对话状态。

**Response:**
```json
{
  "reply": "根据分析，曼哈顿一居室近3个月均价...",
  "session_id": "uuid",
  "files": [
    {"file_id": "file_xxx", "filename": "report.pdf"}
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| reply | string | Agent 的文字回复 |
| session_id | string | 会话ID（浏览器生成，服务端回传） |
| files | array \| null | 生成的文件列表（file_id + filename），未生成时为 null 或空数组 |

### Chat Stream

SSE 流式端点，实时推送 Agent 工具调用步骤和文本生成。前端用此端点替代 `/chat` 实现流式体验。

```
POST /chat/stream
Content-Type: application/json → text/event-stream (SSE)
```

**Request**：与 `/chat` 相同。

**SSE Events**：

| event | data | 说明 |
|-------|------|------|
| `session` | `{"session_id": "uuid"}` | 连接建立，返回 session_id |
| `thinking` | `{"content": "让我查询各区域数据..."}` | Agent 工具调用前的推理文本（灰色斜体显示） |
| `tool_start` | `{"name": "query_database", "label": "查询数据库", "input": "SELECT ..."}` | 工具调用开始 |
| `tool_end` | `{"name": "query_database", "label": "查询数据库"}` | 工具调用完成 |
| `token` | `{"content": "根据查询结果..."}` | 最终回复文本（所有工具完成后） |
| `done` | `{"files": [...]}` | Agent 执行完毕，附带生成的文件列表 |
| `error` | `{"detail": "..."}` | 执行异常 |

> **thinking vs token**：后端缓冲 LLM 文本，遇到 `tool_start` 时将缓冲区作为 `thinking` 事件发出（中间推理），流结束时将剩余缓冲区作为 `token` 事件发出（最终回复）。

**SSE 格式**：
```
event: thinking
data: {"content":"让我查询各区域的租房数据："}

event: tool_start
data: {"name":"query_database","label":"查询数据库","input":"SELECT borough, AVG(price)..."}

event: tool_end
data: {"name":"query_database","label":"查询数据库"}

event: token
data: {"content":"根据查询结果，曼哈顿的平均租金为..."}

event: done
data: {"files":[{"file_id":"file_xxx","filename":"report.pdf"}]}
```

**实现**：后端使用 LangGraph `astream_events(version="v2")` 捕获 `on_chat_model_stream` 文本并缓冲，遇到 `on_tool_start` 时将缓冲区作为 `thinking` 事件发出，流结束时将剩余缓冲区作为 `token`（最终回复）发出。通过 FastAPI `StreamingResponse` 以 `text/event-stream` 格式推送。

### Report Download

从 Anthropic Files API 流式转发文件（Demo 阶段，服务端不缓存）。

```
GET /reports/{file_id}
Response: 文件流式下载
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"
```

---

## Agent Tools (内部)

Agent 在 ReAct 循环中调用的 Tools，不直接暴露为 API：

| Tool | 签名 | 说明 |
|------|------|------|
| `load_skill` | `(name: string) → string` | 按需加载 Skill 内容（Schema/图表/报告规范） |
| `query_database` | `(sql: string) → json` | 执行只读 SQL，API 层 AST 校验 |
| Code Execution（沙盒） | LLM 自动生成 Python 代码 | 图表（matplotlib）+ PDF（reportlab/weasyprint），通过 Files API 取回 |

---

## Error Responses

```json
{
  "detail": "错误描述"
}
```

| HTTP Code | 说明 |
|-----------|------|
| 400 | 请求格式错误 |
| 422 | 参数校验失败 |
| 500 | Agent 执行错误 |
| 504 | Agent 超时（超过 max_agent_steps） |
