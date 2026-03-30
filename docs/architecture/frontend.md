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
  messages: ChatMessage[]        // 当前对话消息
  isLoading: boolean             // Agent 是否在响应
  sendMessage: (content: string) => Promise<void>
  clearHistory: () => void       // 清空 localStorage + 重置 state
  files: FileRef[] | null        // 最新生成的文件列表 [{file_id, filename}]
}
```

**流程**：
1. 组件 mount → `useLocalStorage` 读取历史消息 + session_id
2. 用户发送消息 → 追加到 messages → POST `/chat` 发送完整 messages[]
3. 收到响应 → 追加 AI 消息 → 写回 localStorage
4. 如果响应含 `files` → 存文件引用（file_id + filename）→ 触发 PDF 面板展开

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

async function chatRequest(messages: ChatMessage[], sessionId: string): Promise<ChatResponse>
// POST /chat → { messages, session_id } → { reply, session_id, files? }

async function fetchReport(fileId: string): Promise<Blob>
// GET /reports/{file_id} → PDF blob（服务端从 Anthropic Files API 流式转发）

async function healthCheck(): Promise<boolean>
// GET /health → { status: 'ok' }
```

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

### Aesthetic：Editorial Luxury — 数据杂志风

适合房源数据分析场景：专业、精致、有质感。

### Typography（Google Fonts via next/font）

| 用途 | 字体 | 风格 |
|---|---|---|
| Headings / Logo | **Playfair Display** | Serif，高对比、editorial 气质 |
| Body / Messages | **Outfit** | Geometric sans，现代干净、可读性强 |
| Code / Data | **JetBrains Mono** | Monospace，SQL/数据展示 |

### Color Palette（CSS Variables）

```css
:root {
  /* Base — 深色背景 */
  --bg-primary: #0f0f14;          /* 近黑，微冷 */
  --bg-secondary: #1a1a24;        /* 卡片/面板背景 */
  --bg-tertiary: #24243a;         /* 输入框/hover 态 */

  /* Text */
  --text-primary: #f0ebe3;        /* 暖白/奶油色 */
  --text-secondary: #9a9aad;      /* 次要文字 */
  --text-muted: #5a5a6e;          /* 占位符/时间戳 */

  /* Accent — 琥珀金 */
  --accent: #c8956c;              /* 主强调色 */
  --accent-hover: #d4a574;        /* Hover 态 */
  --accent-subtle: rgba(200, 149, 108, 0.12); /* 背景高亮 */

  /* Semantic */
  --success: #5cb389;
  --error: #c75f5f;
  --border: rgba(255, 255, 255, 0.06);
}
```

**Light theme**：反转 bg/text，accent 保持琥珀金。CSS variables 切换即可。

### Motion Design

| 交互 | 动画 |
|---|---|
| 消息出现 | `fadeInUp` — opacity 0→1, y 12→0, stagger 50ms |
| PDF 面板展开 | 右侧 `slideInRight` — x 100%→0, width 0→40% |
| 发送按钮 | hover scale 1.05, active scale 0.95 |
| 加载指示器 | 3 个圆点 bounce，stagger 100ms |
| 清除对话 | messages `fadeOut`，然后 empty state `fadeIn` |

### 背景氛围

- 主背景：细微 noise texture overlay（`opacity: 0.03`），增加质感
- Chat 区域：左侧极细竖线装饰（editorial 风格的栏线）
- PDF 面板：微弱 inner shadow，制造深度感

## Component Detail

### MessageBubble

- **User 消息**：右对齐，accent 背景，圆角
- **Agent 消息**：左对齐，secondary 背景，支持 Markdown（react-markdown + remark-gfm）
- **Report 链接**：Agent 消息内嵌 "📄 查看报告" 按钮，点击触发 PDF 面板
- **SQL 展示**：折叠的 `<details>` 块，JetBrains Mono 渲染

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
