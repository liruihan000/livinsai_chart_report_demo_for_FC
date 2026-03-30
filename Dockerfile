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

# Install Python dependencies (leverage Docker cache)
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .

# Copy application source + frontend static output
COPY src/ /app/src/
COPY --from=frontend /app/frontend/out /app/frontend/out

# Re-install so the package is importable
RUN pip install --no-cache-dir --no-deps .

# Cloud Run sets $PORT; default 8080
ENV PORT=8080

CMD ["sh", "-c", "uvicorn livins_report_agent.main:app --host 0.0.0.0 --port ${PORT}"]
