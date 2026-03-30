# Deployment

## 架构概览

单容器部署到 GCP Cloud Run：多阶段 Docker 构建，前端 Next.js 静态导出 → FastAPI `StaticFiles` 托管。与 rent_agent 部署模式一致。

```
┌─────────────────────────────────────────────┐
│        Google Cloud Run (livins-report)      │
│        Port: 8080                            │
├─────────────────────────────────────────────┤
│  FastAPI + uvicorn                           │
│  ├── /chat, /chat/stream, /reports/*  (API) │
│  ├── /  → frontend/out/index.html    (SPA)  │
│  └── /static/*  → frontend/out/     (静态)  │
├─────────────────────────────────────────────┤
│  Secrets: ANTHROPIC_API_KEY (Secret Manager) │
│  Env: LLM_MODEL, DATA_SERVICE_URL, etc.     │
│  Scaling: min-instances=1, auto-scaling      │
└─────────────────────────────────────────────┘
         │
         ▼
  https://wf-data-ootdxiumvq-ue.a.run.app
  (Livins AI Data Service)
```

## Prerequisites

- Python 3.12+
- Node.js 20+ / pnpm（Docker 构建阶段使用）
- Docker
- gcloud CLI（已登录且已配置项目 `powerful-surf-415220`）
- Anthropic API Key
- 访问 Livins AI data_service（生产环境）

## Environment Variables

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `anthropic:claude-haiku-4-5-20251001` | LLM 模型 |
| `ANTHROPIC_API_KEY` | - | Anthropic API Key（生产环境用 Secret Manager） |
| `USE_MOCK_CLIENT` | `true` | 是否使用 Mock 数据 |
| `DATA_SERVICE_URL` | `http://localhost:8002` | data_service API 地址 |
| `MAX_AGENT_STEPS` | `15` | Agent 最大推理步数 |
| `MAX_CONCURRENT_INVOCATIONS` | `5` | 最大并发调用数 |
| `API_HOST` | `0.0.0.0` | 服务监听地址 |
| `API_PORT` | `8000` | 服务监听端口（本地开发用，Cloud Run 使用 `$PORT`=8080） |
| `ALLOWED_ORIGINS` | `*` | CORS 允许的域名（生产环境设为 `https://livins.ai,https://www.livins.ai`） |
| `REPORT_OUTPUT_DIR` | `./reports` | 报告文件输出目录（Demo 阶段文件通过 Files API 流式转发） |

## Local Development

```bash
# 安装
pip install -e ".[dev]"
cd frontend && pnpm install && cd ..

# 配置
cp .env.example .env
# 编辑 .env 设置 ANTHROPIC_API_KEY

# 启动（前后端同时）
bash dev.sh
# → Backend: http://localhost:8000
# → Frontend: http://localhost:3000
```

## Docker 构建

多阶段构建：Stage 1 构建前端静态文件，Stage 2 打包 Python 后端 + 静态文件。

```bash
# 本地构建测试
docker build -t livins-report .
docker run -p 8080:8080 -e ANTHROPIC_API_KEY=sk-... -e USE_MOCK_CLIENT=true livins-report
# → http://localhost:8080
```

### Dockerfile（多阶段）

```dockerfile
# Stage 1: Build Next.js static export
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=""
RUN pnpm build
# → /app/frontend/out/

# Stage 2: Python backend + static files
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .
COPY src/ /app/src/
COPY --from=frontend /app/frontend/out /app/frontend/out
RUN pip install --no-cache-dir --no-deps .
ENV PORT=8080
CMD ["sh", "-c", "uvicorn livins_report_agent.main:app --host 0.0.0.0 --port ${PORT}"]
```

### .dockerignore

```
.git
.gitignore
.env
.env.*
.venv
venv
__pycache__
*.pyc
.ruff_cache
.pytest_cache
.mypy_cache
tests/
docs/
*.md
.claude
node_modules
frontend/.next
frontend/out
```

## Cloud Run 部署

### 一键部署脚本 `deploy.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=/home/lee/livins_report_agent
REGISTRY="us-east5-docker.pkg.dev/powerful-surf-415220/whiteforest"
IMAGE="$REGISTRY/livins-report:latest"
REGION="us-east1"
SERVICE="livins-report"

# --- Environment Variables ---
DATA_SERVICE_URL="https://wf-data-ootdxiumvq-ue.a.run.app"
LLM_MODEL="anthropic:claude-haiku-4-5-20251001"
USE_MOCK_CLIENT="false"
API_HOST="0.0.0.0"
MAX_AGENT_STEPS="15"
MAX_CONCURRENT_INVOCATIONS="5"
ALLOWED_ORIGINS="https://livins.ai,https://www.livins.ai"

# --- Update Secret Manager ---
if [ -f "$PROJECT_ROOT/.env" ]; then
  source "$PROJECT_ROOT/.env"
  if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "=== Updating ANTHROPIC_API_KEY in Secret Manager ==="
    echo -n "$ANTHROPIC_API_KEY" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-
  fi
fi

# --- Build & Push ---
echo "=== Building image ==="
cd "$PROJECT_ROOT"
docker build -t "$IMAGE" .

echo "=== Pushing to Artifact Registry ==="
docker push "$IMAGE"

# --- Deploy ---
echo "=== Deploying $SERVICE ==="
ENV_VARS="LLM_MODEL=$LLM_MODEL"
ENV_VARS+=";;USE_MOCK_CLIENT=$USE_MOCK_CLIENT"
ENV_VARS+=";;DATA_SERVICE_URL=$DATA_SERVICE_URL"
ENV_VARS+=";;API_HOST=$API_HOST"
ENV_VARS+=";;MAX_AGENT_STEPS=$MAX_AGENT_STEPS"
ENV_VARS+=";;MAX_CONCURRENT_INVOCATIONS=$MAX_CONCURRENT_INVOCATIONS"
ENV_VARS+=";;ALLOWED_ORIGINS=$ALLOWED_ORIGINS"

gcloud run deploy "$SERVICE" \
  --region="$REGION" \
  --image="$IMAGE" \
  --update-env-vars="^;;^$ENV_VARS" \
  --set-secrets="ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest" \
  --min-instances=1 \
  --allow-unauthenticated

echo "=== livins-report deployed! ==="
```

### 手动步骤（首次）

```bash
# 1. 创建 Secret（仅首次）
echo -n "sk-ant-xxx" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-

# 2. 配置 Docker 认证（仅首次）
gcloud auth configure-docker us-east5-docker.pkg.dev

# 3. 部署
bash deploy.sh
```

## 前端 API 地址配置

- **本地开发**：`frontend/.env.local` 中 `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **生产构建**：Dockerfile 中 `NEXT_PUBLIC_API_URL=""`（空字符串 = 同源，API 请求走相对路径 `/chat/stream`）

## 后端代码变更（部署前需要）

`main.py` 需挂载静态文件以服务前端（生产环境）：

```python
# main.py — 在 create_app() 末尾、return app 之前添加
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file = frontend_dir / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(frontend_dir / "index.html")
```

## Testing

```bash
pytest                                     # 全量测试（零失败）
pytest tests/unit/ -v                      # 单元测试
pytest tests/e2e/ -v                       # E2E 测试
```

## Verification

```bash
# Health check
curl https://livins-report-ootdxiumvq-ue.a.run.app/health

# Chat test（SSE 流式）
curl -N -X POST https://livins-report-ootdxiumvq-ue.a.run.app/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "分析曼哈顿一居室的平均租金"}]}'
```
