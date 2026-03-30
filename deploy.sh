#!/usr/bin/env bash
set -euo pipefail

# === Configuration ===
PROJECT_ROOT=/home/lee/livins_report_agent
REGISTRY="us-east5-docker.pkg.dev/powerful-surf-415220/whiteforest"
IMAGE="$REGISTRY/livins-report:latest"
REGION="us-east1"
SERVICE="livins-report"

# === Environment Variables for Cloud Run ===
DATA_SERVICE_URL="https://wf-data-593342552993.us-east1.run.app"
LLM_MODEL="anthropic:claude-haiku-4-5-20251001"
USE_MOCK_CLIENT="false"
API_HOST="0.0.0.0"
MAX_AGENT_STEPS="15"
MAX_CONCURRENT_INVOCATIONS="5"
ALLOWED_ORIGINS="https://livins.ai,https://www.livins.ai"

# === Update Secret Manager from .env (only extract API key, don't pollute env) ===
if [ -f "$PROJECT_ROOT/.env" ]; then
  _API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' "$PROJECT_ROOT/.env" | cut -d'=' -f2-)
  if [ -n "${_API_KEY:-}" ]; then
    echo "=== Updating ANTHROPIC_API_KEY in Secret Manager ==="
    echo -n "$_API_KEY" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-
  fi
fi

# === Build & Push ===
echo "=== Building livins-report image ==="
cd "$PROJECT_ROOT"
docker build --no-cache -t "$IMAGE" .

echo "=== Pushing to Artifact Registry ==="
docker push "$IMAGE"

# === Deploy ===
echo "=== Deploying $SERVICE ==="

# Use ^;;^ separator so commas in ALLOWED_ORIGINS aren't misinterpreted
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
