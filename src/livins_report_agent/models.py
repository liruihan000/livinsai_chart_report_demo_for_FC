"""Pydantic models for request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessagePayload(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[MessagePayload] = Field(..., min_length=1)
    session_id: str | None = None


class FileInfo(BaseModel):
    file_id: str
    filename: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    files: list[FileInfo] | None = None
