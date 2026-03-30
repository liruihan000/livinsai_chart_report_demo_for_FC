#!/bin/bash
# Start backend (FastAPI) and frontend (Next.js) concurrently
set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    echo -e "\n${GREEN}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Backend
echo -e "${CYAN}[Backend]${NC} Starting FastAPI on :8000 ..."
USE_MOCK_CLIENT=true python -m uvicorn livins_report_agent.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Frontend
echo -e "${CYAN}[Frontend]${NC} Starting Next.js on :3000 ..."
cd frontend && pnpm dev --port 3000 &
FRONTEND_PID=$!

echo -e "${GREEN}Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}Press Ctrl+C to stop both.${NC}"

wait
