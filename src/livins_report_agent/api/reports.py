"""GET /reports/{file_id} — stream file, cached locally after first download."""

from __future__ import annotations

import io
import logging
import mimetypes

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory cache: file_id → (bytes, filename, media_type)
_file_cache: dict[str, tuple[bytes, str, str]] = {}

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".csv": "text/csv",
    ".svg": "image/svg+xml",
}


def _guess_media_type(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _MEDIA_TYPES.get(ext) or mimetypes.guess_type(filename)[0] or "application/octet-stream"


@router.get("/reports/{file_id}")
async def download_report(file_id: str):
    # Serve from cache if available
    if file_id in _file_cache:
        file_bytes, filename, media_type = _file_cache[file_id]
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
            },
        )

    # Download from Anthropic Files API and cache
    try:
        import anthropic
        from livins_report_agent.config import get_settings

        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        file_metadata = client.beta.files.retrieve_metadata(file_id)
        file_response = client.beta.files.download(file_id)
        file_bytes = file_response.read()
        filename = file_metadata.filename
        media_type = _guess_media_type(filename)

        # Cache it
        _file_cache[file_id] = (file_bytes, filename, media_type)
        logger.info("Cached file %s (%s, %d bytes)", file_id, filename, len(file_bytes))

        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "public, max-age=3600",
            },
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="anthropic SDK not installed")
    except Exception as exc:
        logger.exception("Failed to download report %s", file_id)
        raise HTTPException(status_code=404, detail=f"File not found: {exc}")
