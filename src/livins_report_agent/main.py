"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from livins_report_agent.api.chat import router as chat_router
from livins_report_agent.api.reports import router as reports_router


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

    return app


app = create_app()
