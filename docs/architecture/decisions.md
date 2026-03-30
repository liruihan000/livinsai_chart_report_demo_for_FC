# Design Decisions

每个决策记录：选了什么、为什么、否决了什么替代方案。

## 1. 单 ReAct Agent，不用 Pipeline/Multi-Agent

**选择**：一个 ReAct Agent + Tools

**原因**：
- Pipeline多Agent串行会丢失上下文（用户说"重点关注流失率"在传递中丢失）
- 报表生成是顺序+工具密集型任务，Google Research数据：工具密集型多Agent慢2-6倍
- 所有步骤共享同一个上下文（Agent需要知道之前查了什么才能决定下一步）

**参考**：Anthropic "Building Effective Agents" — 从最简方案开始，只在必要时增加复杂度

## 2. Schema 写入 Skill，通过 load_skill 按需加载

**选择**：Schema 全量写入 `data_query/SKILL.md`，Agent 通过 `load_skill("data_query")` 按需加载

**否决方案**：
- Embedding检索：语义匹配会漏掉"语义距离远但业务相关"的表
- 全量塞 System Prompt：每次对话都占 token，浪费
- `explore_schema` Tool 调 API：4张表要调5次（表列表+每张表），太多轮次

**原因**：
- 4张表全量写入一个 SKILL.md 也就几百 token，一次 load_skill 调用全部获取
- Skill 索引通过 `load_skill` 的 docstring 自动暴露给 LLM，System Prompt 无需包含任何 Skill 内容
- 如果未来表增长到几十张，再考虑拆分或改为 API 探索

## 3. Agent决定报告结构，不用固定模板

**选择**：Agent 在 Code Execution 沙盒中自行编写报告生成代码，决定结构和布局

**否决**：FastAPI模板方案（INSART案例的做法）

**原因**：
- 固定模板限制灵活性——趋势分析是"时间线"结构，对比分析是"并列"结构
- Agent = 设计师，Code Execution = 排版工具

## 4. Text-to-SQL：Agent 写 SQL，API 层校验执行

**选择**：`query_database(sql)` Tool — Agent 生成 SELECT SQL，通过 data_service `/query/execute` 执行

**否决方案**：预定义 analytics endpoints（`/analytics/price-trend` 等）

**原因**：
- **业界标准**：Databricks AI/BI、Snowflake Cortex Analyst、AWS QuickSight Q 都用 text-to-SQL
- **灵活性**：报表分析需求千变万化，预定义 endpoint 永远补不完（每种聚合/分组/过滤组合都需要新 endpoint）
- **安全可控**：校验逻辑集中在 API 层（sqlglot AST 解析 + 白名单表 + 只读连接 + 超时 + 行数限制），Agent 不感知
- **减少 API 维护**：只需两个通用 endpoint（`/query/execute` + `/query/schema`），不需要为每种分析需求建 endpoint
- **LLM SQL 质量**：现代 LLM 对 SQL 生成的准确率已由 Spider/Bird benchmark 验证，4张表的简单 schema 出错率很低

## 5. 图表+PDF：Demo 用 Claude Code Execution，后续升级 antvis + Playwright

**选择（Demo）**：Claude Code Execution 沙盒 — Agent 通过 `code_execution_20250825` 在 Anthropic 托管容器中执行 matplotlib 生成图表 + reportlab/weasyprint 生成 PDF，通过 Files API 取回文件。

**原因**：
- 零运维，不需要自建渲染环境
- `create_chart` 和 `build_report` 两个 Tool 合并为一个 Code Execution 调用
- Haiku 4.5 也支持，成本可控
- 限制：仅 Claude API（不支持 Bedrock/Vertex），有额外费用，沙盒启动+执行 ~5-15秒

**后续升级方案（更快更便宜）**：
- 图表：[antvis/mcp-server-chart](https://github.com/antvis/mcp-server-chart) — MCP Server，26+ 图表类型（基于 AntV），渲染 ~1-2秒，免费，LLM 无关
- PDF：Jinja2 模板 → HTML → [Playwright](https://playwright.dev/) → PDF — warm 模式下 13ms 生成 PDF
- 优势：速度快 10x+，无 Anthropic 沙盒费用，可切换任意 LLM
- 配置示例：
  ```json
  {
    "mcpServers": {
      "mcp-server-chart": {
        "command": "npx",
        "args": ["-y", "@antv/mcp-server-chart"]
      }
    }
  }
  ```

## 6. 对话历史：Demo 阶段浏览器缓存，服务端无状态

**选择**：对话历史存浏览器 `localStorage`，每轮请求携带完整 `messages` 数组发送给服务端，服务端转为 LangChain 消息后喂给 Agent。服务端不持久化对话历史。

**否决方案**：
- 服务端 Checkpointer（LangGraph MemorySaver / Redis）：Demo 阶段不需要跨设备同步，增加运维复杂度
- 数据库持久化（PostgreSQL / SQLite）：同上，Demo 阶段过重
- Session cookie：不够透明，不便于调试

**原因**：
- **与 rent_agent 一致**：rent_agent 已验证此模式（`localStorage` key: `rent_agent_history`），服务端完全无状态
- **简单可靠**：无分布式锁、无 session 过期、无数据库迁移，Demo 阶段够用
- **调试友好**：浏览器 DevTools → Application → LocalStorage 直接查看/编辑对话历史

**实现要点**（aligned with rent_agent）：
- 浏览器端：`localStorage` 存储 `[{role, content}, ...]`，每次 POST `/chat` 时携带完整 `messages`
- 服务端：`ChatRequest.messages` → 转为 `HumanMessage` / `AIMessage` → 喂给 Agent，不存储
- Session ID：浏览器生成 `crypto.randomUUID()`，存 `localStorage`，随请求发送，服务端回传
- 清除对话：前端"清除对话"按钮清空 `localStorage` 中的 history 和 session_id

**后续升级**：
- 需要跨设备同步时，加 LangGraph Checkpointer（Redis / PostgreSQL）
- 需要对话摘要时，加 summarize_conversation 中间件压缩历史

## 7. 前端：Next.js 15 静态导出 + React 19 + Tailwind v4

**选择**：Next.js 15 App Router（`output: 'export'`）+ React 19 + Tailwind CSS v4 + @react-pdf-viewer/core

**否决方案**：
- Vite + React SPA：可行，但 Next.js 的 `next/font`、静态优化、约定式路由更省心
- Vue/Svelte：团队 React 栈，与生态保持一致
- Ant Design / shadcn-ui：Chat + PDF 预览场景简单，组件库引入过重
- SWR / React Query：仅 3 个 endpoint，原生 fetch + custom hooks 足够

**原因**：
- **静态导出**：`output: 'export'` 生成纯静态 HTML/JS，Nginx/CDN 直接托管，无 Node.js 运行时
- **状态管理**：useState + custom hooks（useChat / useLocalStorage / usePdf），无需 Redux/Zustand
- **PDF 预览**：@react-pdf-viewer/core 基于 pdfjs-dist，浏览器内渲染，支持缩放/翻页/搜索
- **动画**：motion (Framer Motion v12)，仅用于消息出现 + PDF 面板滑入
- **与后端解耦**：前端通过 `NEXT_PUBLIC_API_URL` 环境变量直连 FastAPI，纯静态无 rewrites

详见 `docs/architecture/frontend.md`。

## 8. Protocol-based Client，不用继承

**选择**：`DataClientProtocol(Protocol)` 结构化类型

**原因**：
- 和rent_agent一致的模式
- Mock/Http实现不需要继承关系，只需满足接口签名
- 测试时传MockClient，零网络调用
