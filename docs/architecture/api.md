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
| Code Execution（沙盒） | Claude 自动生成 Python 代码 | 图表（matplotlib）+ PDF（reportlab/weasyprint），通过 Files API 取回 |

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
