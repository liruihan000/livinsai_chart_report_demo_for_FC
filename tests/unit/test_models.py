"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from livins_report_agent.models import ChatRequest, ChatResponse, MessagePayload, FileInfo


def test_message_payload_valid():
    msg = MessagePayload(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_message_payload_invalid_role():
    with pytest.raises(ValidationError):
        MessagePayload(role="system", content="hello")


def test_message_payload_empty_content():
    with pytest.raises(ValidationError):
        MessagePayload(role="user", content="")


def test_chat_request_valid():
    req = ChatRequest(
        messages=[{"role": "user", "content": "test"}],
        session_id="abc-123",
    )
    assert len(req.messages) == 1
    assert req.session_id == "abc-123"


def test_chat_request_empty_messages():
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])


def test_chat_request_no_session_id():
    req = ChatRequest(messages=[{"role": "user", "content": "test"}])
    assert req.session_id is None


def test_chat_response():
    resp = ChatResponse(reply="hello", session_id="abc")
    assert resp.reply == "hello"
    assert resp.files is None


def test_chat_response_with_files():
    resp = ChatResponse(
        reply="done",
        session_id="abc",
        files=[FileInfo(file_id="f1", filename="report.pdf")],
    )
    assert len(resp.files) == 1
    assert resp.files[0].file_id == "f1"
