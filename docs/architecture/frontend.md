# Frontend Architecture

Chat 界面 + PDF 预览/下载，与 FastAPI 后端分离部署。

## Tech Stack

| 层 | 选择 | 原因 |
|---|---|---|
| Framework | **Next.js 15** (App Router, `output: 'export'`) | 静态导出，无 SSR 开销；App Router 是 React 最新范式 |
| UI | **React 19** + **TypeScript 5** | Concurrent 特性（useTransition）、类型安全 |
| Styling | **Tailwind CSS v4** | Utility-first + CSS variables 主题系统；v4 零配置 |
| PDF 预览 | **@react-pdf-viewer/core** + **pdfjs-dist** | 浏览器内渲染、支持缩放/翻页/搜索、社区活跃 |
| 动画 | **motion** (Framer Motion v12) | React 动画标准库、stagger/layout 动画 |
| HTTP | **原生 fetch** | 无需 axios —— 只有 3 个 endpoint |
| 包管理 | **pnpm** | 磁盘高效、lockfile 严格 |

**不用的**：Redux/Zustand（useState + custom hooks 足够）、axios（fetch 够用）、UI 库（Tailwind 手写）。

## Directory Structure

```
frontend/
├── src/
│   ├── app/                         # Next.js App Router
│   │   ├── layout.tsx               # Root layout（字体、主题、metadata）
│   │   ├── page.tsx                 # 唯一页面 — Chat + PDF split-panel
│   │   └── globals.css              # Tailwind directives + CSS variables
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx    # 编排层：组合 MessageList + InputBar
│   │   │   ├── MessageList.tsx      # 消息列表（虚拟滚动 if needed）
│   │   │   ├── MessageBubble.tsx    # 单条消息（支持 Markdown 渲染）
│   │   │   ├── InputBar.tsx         # 输入框 + 发送按钮
│   │   │   ├── ToolSteps.tsx        # 工具调用步骤（流式过程中展示，完成后消失）
│   │   │   └── StreamingDots.tsx    # Agent 思考中的加载动画
│   │   ├── pdf/
│   │   │   ├── PdfPanel.tsx         # PDF 预览面板（右侧滑入）
│   │   │   └── PdfToolbar.tsx       # 缩放、翻页、下载按钮
│   │   └── layout/
│   │       ├── AppShell.tsx         # 整体布局骨架
│   │       └── Header.tsx           # 顶栏：标题 + 清除历史按钮
│   ├── hooks/
│   │   ├── useChat.ts              # 核心：消息状态 + API 调用 + loading
│   │   ├── useLocalStorage.ts      # localStorage 读写 + SSR 安全
│   │   └── usePdf.ts              # PDF URL 管理 + blob 缓存
│   ├── lib/
│   │   ├── api.ts                  # fetch 封装（baseURL, error handling）
│   │   ├── storage.ts             # localStorage key 常量 + 序列化
│   │   └── types.ts               # ChatMessage, ChatResponse, SessionState
│   └── config/
│       └── fonts.ts               # next/font 配置（Google Fonts）
├── public/
│   └── favicon.svg
├── next.config.ts                  # output: 'export'（纯静态，无 rewrites）
├── postcss.config.js              # Tailwind v4 postcss plugin
├── tsconfig.json
├── .env.local.example             # NEXT_PUBLIC_API_URL=http://localhost:8000
└── package.json
```

## Page Layout

单页应用，split-panel 布局：

```
┌──────────────────────────────────────────────────────┐
│  Header:  🏠 Livins Report Agent    [清除对话]       │
├────────────────────────┬─────────────────────────────┤
│                        │                             │
│   Chat Messages        │   PDF Preview Panel         │
│   ┌──────────────┐     │   (report_url 存在时显示)    │
│   │ User message  │     │                             │
│   └──────────────┘     │   ┌───────────────────────┐ │
│   ┌──────────────┐     │   │                       │ │
│   │ Agent reply   │     │   │   PDF Viewer          │ │
│   │ [查看报告]    │     │   │   (react-pdf-viewer)  │ │
│   └──────────────┘     │   │                       │ │
│                        │   └───────────────────────┘ │
│                        │   [⬇ Download] [🔍 Zoom]    │
│   ┌──────────────────┐ │                             │
│   │ 输入框    [发送]  │ │                             │
│   └──────────────────┘ │                             │
├────────────────────────┴─────────────────────────────┤
```

- **默认**：Chat 占满全宽
- **有报告时**：左 60% Chat + 右 40% PDF Panel（motion 动画滑入）
- **移动端**：PDF 以 bottom sheet 方式弹出
- **响应式断点**：`md:` (768px) 切换 split/stack 布局

## State Management

```
useState + Custom Hooks，无外部状态库
```

### useChat Hook（核心）

```typescript
interface UseChatReturn {
  messages: ChatMessage[]        // 当前对话消息（已完成的）
  isLoading: boolean             // Agent 是否在响应
  activeToolSteps: ToolStep[]    // 流式过程中的工具步骤（处理完成后清空）
  streamingContent: string       // 流式过程中的部分文本（处理完成后清空）
  sendMessage: (content: string) => Promise<void>
  clearHistory: () => void       // 清空 localStorage + 重置 state
  files: FileRef[] | null        // 最新生成的文件列表 [{file_id, filename}]
}
```

**流程**（SSE 流式）：
1. 组件 mount → `useLocalStorage` 读取历史消息 + session_id
2. 用户发送消息 → 追加到 messages → POST `/chat/stream` SSE 连接
3. 收到 `tool_start`/`tool_end` → 更新 `activeToolSteps`（实时显示工具调用进度）
4. 收到 `token` → 追加到 `streamingContent`（逐字显示 LLM 回复）
5. 收到 `done` → 将完整文本存入 messages + 写回 localStorage，清空 activeToolSteps/streamingContent
6. 如果 `done` 含 `files` → 存文件引用 → 触发 PDF 面板展开

**工具步骤生命周期**：`activeToolSteps` 和 `streamingContent` 仅在流式过程中有值，完成后归零。已完成的消息（`messages[]`）中不保留工具步骤 — 历史消息只存最终文本。

### useLocalStorage Hook

```typescript
// SSR-safe：Next.js 静态导出无 SSR 问题，但仍做 typeof window 检查
function useLocalStorage<T>(key: string, initialValue: T): [T, (v: T) => void]
```

**localStorage Keys**：
| Key | 内容 |
|---|---|
| `livins_messages` | `ChatMessage[]` — 完整对话历史 |
| `livins_session_id` | `string` — `crypto.randomUUID()` |
| `livins_theme` | `'light' \| 'dark'` — 主题偏好 |

### usePdf Hook

```typescript
interface UsePdfReturn {
  pdfUrl: string | null          // 当前预览的 PDF blob URL
  isOpen: boolean                // 面板是否展开
  openPdf: (fileId: string, filename?: string) => Promise<void>  // fetch → blob → URL
  closePdf: () => void
  downloadPdf: () => void        // 触发浏览器下载
}
```

**PDF 缓存**：fetch 报告 → `URL.createObjectURL(blob)` → 存 ref，避免重复下载。组件卸载时 `revokeObjectURL`。

## API Integration

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function chatStream(messages, sessionId, callbacks): Promise<void>
// POST /chat/stream → SSE 流，通过 callbacks 实时回调 tool_start/tool_end/token/done

async function chatRequest(messages, sessionId): Promise<ChatResponse>
// POST /chat → { messages, session_id } → { reply, session_id, files? }（保留，向后兼容）

async function fetchReport(fileId: string): Promise<Blob>
// GET /reports/{file_id} → PDF blob（服务端从 Anthropic Files API 流式转发）

async function healthCheck(): Promise<boolean>
// GET /health → { status: 'ok' }
```

**SSE 流读取**：`chatStream` 使用 `fetch` + `ReadableStream` 解析 SSE 事件，通过 `StreamCallbacks` 接口回调（`onToolStart`/`onToolEnd`/`onToken`/`onDone`/`onError`）。

**错误处理**：
- 网络错误 → Toast 提示 "连接失败，请检查服务端"
- 504 → Toast "分析超时，请简化查询"
- 500 → Toast "服务异常" + 消息标记为失败（可重试）

## Caching Strategy

| 数据 | 存储位置 | 生命周期 |
|---|---|---|
| 对话历史 | localStorage | 用户清除或浏览器清理 |
| Session ID | localStorage | 随对话历史一同清除 |
| PDF Blob | `URL.createObjectURL` (内存) | 组件卸载时释放 |
| 主题偏好 | localStorage | 持久 |
| 静态资源 | Next.js static export + CDN | 长期缓存 |

**无 SWR/React Query**：只有 3 个 endpoint，无需请求缓存/重新验证。

## Visual Design Direction

### Aesthetic：Warm Minimal — 与 rent_agent 一致

暖色极简风格，与 rent_agent 前端保持视觉一致性。浅色背景、暖灰色调、DM Sans 字体。

### Typography（Google Fonts via next/font）

| 用途 | 字体 | 风格 |
|---|---|---|
| Display / Logo | **Space Grotesk** | Geometric sans，现代标题 |
| Body / Messages | **DM Sans** | Humanist sans，温暖可读（与 rent_agent 一致） |
| Code / Data | **JetBrains Mono** | Monospace，SQL/数据展示 |

### Color Palette（CSS Variables，与 rent_agent 对齐）

```css
:root {
  --bg-primary: #f8f7f5;          /* 暖白背景 */
  --bg-secondary: #ffffff;        /* 卡片/面板/输入框 */
  --bg-tertiary: #faf9f7;         /* 次级背景 */

  --text-primary: #2d2b28;        /* 深炭文字 */
  --text-secondary: #7a7672;      /* 次要文字 */
  --text-muted: #a8a49f;          /* 占位符/标签 */

  --accent: #4a4743;              /* 按钮/强调 */
  --accent-subtle: #f0ece4;       /* 用户消息气泡背景 */

  --border: #e8e4de;              /* 分割线 */
  --border-light: #ede9e2;        /* 代码块/表格背景 */

  --shadow-sm: 0 2px 14px rgba(0,0,0,0.06);
  --shadow-md: 0 4px 18px rgba(0,0,0,0.08);
}
```

### Motion Design

| 交互 | 动画 |
|---|---|
| 消息出现 | `fade-up` 0.22s — translateY 8→0, opacity 0→1（与 rent_agent 一致） |
| 加载指示器 | 3 点 bounce，stagger 150ms，1.3s 周期（无工具步骤时显示） |
| 工具步骤 spinner | `spin` 0.8s linear infinite，当前执行步骤旋转指示 |
| 输入框 | textarea 高度自适应，最大 110px |

### 关键视觉元素

- 860px max-width 居中容器（与 rent_agent 一致）
- 圆角气泡（22px radius，用户消息右下角 5px 方角）
- 圆形发送按钮（36px，#9b9690，白色箭头图标）
- Assistant 头像（33px 圆形，#e8e3db 背景，人形 SVG 图标）
- Markdown 渲染：react-markdown + remark-gfm，样式与 rent_agent 的 marked.js 输出一致
- 3px 细滚动条，rgba(0,0,0,0.08)

## Component Detail

### MessageBubble / StreamingMessage

- **User 消息**：右对齐，accent 背景，圆角
- **Agent 消息（已完成）**：左对齐，Markdown 渲染，不含工具步骤
- **Agent 消息（流式中，StreamingMessage）**：左对齐，实时显示 ToolSteps + 逐字文本
- **Report 链接**：Agent 消息内嵌 "📄 查看报告" 按钮，点击触发 PDF 面板
- **SQL 展示**：折叠的 `<details>` 块，JetBrains Mono 渲染

### ToolSteps（流式过程中显示，完成后消失）

- 可折叠步骤列表，点击展开/收起
- 每个步骤：工具图标（数据库/代码/书本）+ 中文标签 + 输入摘要
- **进行中**：旋转 spinner + "查询数据库 (1/3)"
- **全部完成**：绿色勾 + "完成 3 个步骤"
- 展开后显示每步详情（SQL 语句、代码片段等，monospace 字体）
- 仅在 `isLoading` 期间渲染，完成后不保留在历史消息中

### InputBar

- 自适应高度 textarea（max 4 行）
- Enter 发送，Shift+Enter 换行
- 发送中 disabled + loading 状态
- 右侧发送按钮：accent 色图标

### PdfPanel

- 上方 Toolbar：文件名、页码 (1/N)、缩放 +/-、下载按钮
- 中间：react-pdf-viewer 渲染区
- 右上角关闭按钮 (×)
- 支持鼠标滚轮缩放

### Header

- 左侧：Playfair Display logo "Livins Report"
- 右侧：清除对话按钮（二次确认 dialog）、主题切换

## Build & Dev

```bash
# 安装
cd frontend && pnpm install

# 开发（代理 API 到 FastAPI）
pnpm dev                        # http://localhost:3000

# 构建静态产物
pnpm build                      # → frontend/out/

# 类型检查
pnpm typecheck                  # tsc --noEmit

# Lint
pnpm lint                       # next lint + eslint
```

### API 连接

静态导出不支持 `rewrites`，前端直接通过 `NEXT_PUBLIC_API_URL` 环境变量连接 FastAPI（默认 `http://localhost:8000`）。生产部署时由 Nginx/CDN 托管静态文件，`NEXT_PUBLIC_API_URL` 指向后端地址。

## Testing Strategy

Demo 阶段只做组件/hook 单元测试（Vitest + RTL），不做浏览器 E2E。详见 `docs/testing.md`。

| 层 | 工具 | 覆盖 |
|---|---|---|
| 组件/Hook 单元 | **Vitest** + **React Testing Library** | hooks 逻辑、组件渲染、用户交互 |

```
frontend/__tests__/
├── setup.ts
├── hooks/
│   ├── useChat.test.ts
│   ├── useLocalStorage.test.ts
│   └── usePdf.test.ts
└── components/
    ├── ChatContainer.test.tsx
    ├── MessageBubble.test.tsx
    └── PdfPanel.test.tsx
```
