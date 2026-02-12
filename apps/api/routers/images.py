"""Image upload router — the primary entry-point for creators."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from apps.api.core.security import get_current_user_id
from apps.api.services.database import DatabaseService, get_database_service
from apps.api.services.queue import QueueService, get_queue_service
from apps.api.services.storage import StorageService, get_storage_service

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# ------------------------------------------------------------------
# Allowed MIME types for upload validation
# ------------------------------------------------------------------
_ALLOWED_CONTENT_TYPES: set[str] = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

_MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB


# ------------------------------------------------------------------
# Response schema
# ------------------------------------------------------------------
class UploadResponse(BaseModel):
    image_id: str
    status: str


# ------------------------------------------------------------------
# POST /images/upload
# ------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image for protection",
)
async def upload_image(
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
    storage: StorageService = Depends(get_storage_service),
    db: DatabaseService = Depends(get_database_service),
    queue: QueueService = Depends(get_queue_service),
) -> UploadResponse:
    """Accept an image upload and kick off the GPU protection pipeline.

    Flow:
        1. Validate the uploaded file (type & size).
        2. Upload the raw file to Cloudflare R2.
        3. Create an ``images`` row in Supabase (status = ``pending``).
        4. Push a task onto the Redis queue for the GPU worker.

    Returns:
        ``image_id`` and current ``status``.
    """
    # ── 1. Validate ──────────────────────────────────────────────────
    content_type: str = file.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: {_ALLOWED_CONTENT_TYPES}",
        )

    file_bytes: bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the {_MAX_FILE_SIZE // (1024 * 1024)} MB limit",
        )

    # Derive a unique storage key so filenames never collide.
    ext: str = _extension_from_content_type(content_type)
    storage_key: str = f"raw/{user_id}/{uuid.uuid4().hex}{ext}"

    # ── 2. Storage → 3. Database → 4. Queue ─────────────────────────
    image_id: str | None = None
    try:
        # 2. Upload to R2
        await storage.upload_file(file_bytes, storage_key, content_type)

        # 3. Persist metadata in Supabase
        row: dict[str, Any] = db.create_image(
            user_id=user_id,
            original_url=storage_key,
        )
        image_id = row["id"]

        # 4. Enqueue task for the GPU worker
        await queue.enqueue(image_id=image_id, storage_key=storage_key)

    except HTTPException:
        # Re-raise HTTP errors (validation etc.) as-is.
        raise
    except Exception as exc:
        logger.exception("Upload pipeline failed for user %s", user_id)
        # If we already created a DB row, mark it as failed.
        if image_id is not None:
            _mark_failed_safe(db, image_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload. Please try again later.",
        ) from exc

    return UploadResponse(image_id=image_id, status="pending")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _extension_from_content_type(content_type: str) -> str:
    """Map a MIME type to a file extension."""
    mapping: dict[str, str] = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }
    return mapping.get(content_type, ".bin")


def _mark_failed_safe(db: DatabaseService, image_id: str) -> None:
    """Best-effort status update — never raises."""
    try:
        db.set_failed(image_id)
    except Exception:
        logger.exception(
            "Failed to mark image %s as failed in DB", image_id
        )
