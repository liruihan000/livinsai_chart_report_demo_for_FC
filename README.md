# Livins Report Agent — FC 面试题目一 Demo

这是针对 **FC 面试题目一** 做的 Demo 演示，花了约一天时间完成。

## 功能

- 自然语言提问，Agent 自动查询房源数据库（Text-to-SQL）
- 根据查询结果自动生成数据图表（matplotlib）
- 自动生成 PDF 报告，支持在线预览和下载
- SSE 流式推送，实时显示 Agent 工具调用步骤（SQL、代码执行等）
- 多轮对话，支持上下文追问

## 关于图表/PDF 生成

当前 Demo 使用 **Claude Code Execution 沙盒**（`code_execution_20250825`）生成图表和 PDF：Agent 在 Anthropic 托管的容器中执行 matplotlib 绘图 + reportlab 组装 PDF，通过 Files API 取回文件。这种方式零运维、开发快，但沙盒启动+执行约 5-15 秒，且有额外的 API 费用。

**生产环境升级方案**（速度提升 10x+，成本大幅降低）：

| 组件 | Demo（当前） | Production（计划） |
|------|-------------|-------------------|
| 图表 | Claude 沙盒 + matplotlib（5-15s） | [antvis/mcp-server-chart](https://github.com/antvis/mcp-server-chart) MCP Server，26+ 图表类型，~1-2s，免费 |
| PDF | Claude 沙盒 + reportlab（同上） | Jinja2 模板 → HTML → Playwright，warm 模式 13ms，无沙盒费用 |

升级后无需 Anthropic 沙盒，可切换任意 LLM，详见 `docs/architecture/decisions.md` 第 5 条。

## 已知限制

- **未做手机端适配**，仅适合桌面浏览器使用
- **对话历史仅存浏览器 localStorage**，未入库持久化。清除对话或清除浏览器数据后**无法找回**
- Demo 级别项目，未做生产级错误处理和鉴权

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Next.js 15 + React 19 + Tailwind CSS v4 + @react-pdf-viewer/core |
| 后端 | FastAPI + LangGraph ReAct Agent + LangChain |
| LLM | Claude（Anthropic）|
| 图表/PDF | Demo: Claude Code Execution 沙盒（matplotlib + reportlab）→ Prod: antvis MCP + Playwright |
| 数据库 | PostgreSQL + PostGIS（通过 Livins Data Service API）|

## 快速开始

### 1. 安装依赖

```bash
# 后端
pip install -e ".[dev]"

# 前端
cd frontend && pnpm install
```

### 2. 配置环境变量

```bash
# 后端：复制 .env.example 并填入你的配置
cp .env.example .env

# 前端：复制 .env.local.example 并填入 API 地址
cp frontend/.env.local.example frontend/.env.local
```

### 3. 启动

```bash
./dev.sh
```

启动后访问：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000

### 4. 使用

1. 打开浏览器访问 http://localhost:3000
2. 在聊天框输入自然语言问题，例如："帮我分析各区域房源价格分布"
3. Agent 会自动查询数据库、生成图表和 PDF 报告
4. 右侧面板可预览和下载生成的 PDF

## 项目结构

```
├── src/livins_report_agent/    # 后端
│   ├── agent/                  # ReAct Agent
│   ├── api/                    # FastAPI 端点（/chat, /chat/stream, /reports）
│   ├── tools/                  # 工具（query_database, load_skill, code_execution）
│   ├── skills/                 # Skill 文件（Schema、图表规范、报告规范）
│   └── apartment_client/       # 数据服务客户端
├── frontend/                   # Next.js 前端
│   └── src/
│       ├── components/         # Chat、PDF 预览组件
│       ├── hooks/              # useChat, usePdf, useLocalStorage
│       └── lib/                # API 调用、类型定义
├── tests/                      # 单元测试 + E2E 测试
├── docs/                       # 架构文档
└── dev.sh                      # 一键启动前后端
```
