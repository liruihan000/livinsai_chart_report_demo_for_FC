"""FastAPI application entry point."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from livins_report_agent.api.chat import router as chat_router
from livins_report_agent.api.reports import router as reports_router

# Configure logging for agent tool calls
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet noisy libs, keep our tools visible
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)
logging.getLogger("langgraph").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    app = FastAPI(title="Livins Report Agent", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(reports_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Serve frontend static files (production: Docker copies to frontend/out)
    # In Docker: /app/frontend/out; local dev: ./frontend/out (doesn't exist, skipped)
    frontend_dir = Path("/app/frontend/out")
    if not frontend_dir.exists():
        frontend_dir = Path.cwd() / "frontend" / "out"
    if frontend_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(frontend_dir / "_next")), name="next-static")

        @app.get("/")
        async def serve_index():
            return FileResponse(frontend_dir / "index.html")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            file = frontend_dir / path
            if file.exists() and file.is_file():
                return FileResponse(file)
            return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()
