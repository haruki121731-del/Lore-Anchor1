"""Image upload router — the primary entry-point for creators."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from apps.api.core.config import get_settings
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
class ImageRecord(BaseModel):
    model_config = {"populate_by_name": True}

    image_id: str = Field(alias="id")
    user_id: str
    original_url: str
    protected_url: str | None = None
    watermark_id: str | None = None
    c2pa_manifest: dict[str, Any] | None = None
    status: str
    created_at: str
    updated_at: str


class ImageListResponse(BaseModel):
    images: list[ImageRecord]


class UploadResponse(BaseModel):
    image_id: str
    status: str


# ------------------------------------------------------------------
# GET /images/
# ------------------------------------------------------------------
@router.get(
    "/",
    response_model=ImageListResponse,
    summary="List images for the authenticated user",
)
async def list_images(
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> ImageListResponse:
    """Return all images belonging to the authenticated user, newest first."""
    rows = db.list_images_by_user(user_id)
    return ImageListResponse(images=rows)


# ------------------------------------------------------------------
# GET /images/{image_id}
# ------------------------------------------------------------------
@router.get(
    "/{image_id}",
    response_model=ImageRecord,
    summary="Get a single image by ID",
)
async def get_image(
    image_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> ImageRecord:
    """Return a single image record. Returns 403 if it belongs to another user."""
    row = db.get_image(image_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    if row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return ImageRecord(**row)


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
        logger.info("[step 2/4] Uploading to R2: %s", storage_key)
        await storage.upload_file(file_bytes, storage_key, content_type)
        logger.info("[step 2/4] R2 upload succeeded")

        # 3. Persist metadata in Supabase
        logger.info("[step 3/4] Inserting row into Supabase for user %s", user_id)
        row: dict[str, Any] = db.create_image(
            user_id=user_id,
            original_url=storage_key,
        )
        image_id = row["id"]
        logger.info("[step 3/4] Supabase insert succeeded, image_id=%s", image_id)

        # 4. Enqueue task for the GPU worker
        logger.info("[step 4/4] Enqueuing task for image_id=%s", image_id)
        await queue.enqueue(image_id=image_id, storage_key=storage_key)
        logger.info("[step 4/4] Redis enqueue succeeded")

    except HTTPException:
        # Re-raise HTTP errors (validation etc.) as-is.
        raise
    except Exception as exc:
        logger.exception("Upload pipeline failed for user %s", user_id)
        # If we already created a DB row, mark it as failed.
        if image_id is not None:
            _mark_failed_safe(db, image_id)
        # In DEBUG mode, expose the real error for easier diagnosis.
        detail = (
            f"Upload failed: {type(exc).__name__}: {exc}"
            if get_settings().DEBUG
            else "Failed to process upload. Please try again later."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
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
