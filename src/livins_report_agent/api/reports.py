"""GET /reports/{file_id} — stream file from Anthropic Files API."""

from __future__ import annotations

import logging

import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/reports/{file_id}")
async def download_report(file_id: str):
    try:
        import anthropic

        client = anthropic.Anthropic()
        file_metadata = client.beta.files.retrieve_metadata(file_id)
        file_response = client.beta.files.download(file_id)
        file_bytes = file_response.read()
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{file_metadata.filename}"'
            },
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="anthropic SDK not installed")
    except Exception as exc:
        logger.exception("Failed to download report %s", file_id)
        raise HTTPException(status_code=404, detail=f"File not found: {exc}")
