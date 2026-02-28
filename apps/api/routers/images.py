"""Image upload router — the primary entry-point for creators."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from apps.api.core.config import get_settings
from apps.api.core.security import get_current_user_id
from apps.api.models.schemas import (
    DeleteResponse,
    DownloadTrackedResponse,
    ImageRecord,
    PaginatedImageListResponse,
    RetryResponse,
    TaskStatusResponse,
    UploadResponse,
)
from apps.api.services.database import DatabaseService, get_database_service
from apps.api.services.queue import QueueService, get_queue_service
from apps.api.services.storage import StorageService, get_storage_service

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

limiter = Limiter(key_func=get_remote_address)

# ------------------------------------------------------------------
# Allowed MIME types for upload validation
# ------------------------------------------------------------------
_ALLOWED_CONTENT_TYPES: set[str] = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

_MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB

# Free tier limits
FREE_TIER_MONTHLY_LIMIT: int = 5

# ------------------------------------------------------------------
# Magic byte signatures for file type validation
# ------------------------------------------------------------------
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]


def _validate_magic_bytes(file_bytes: bytes, declared_type: str) -> None:
    """Validate file content matches declared MIME type via magic bytes."""
    if len(file_bytes) < 12:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File too small to be a valid image",
        )

    # Check standard signatures
    for sig, mime in _MAGIC_SIGNATURES:
        if file_bytes[:len(sig)] == sig:
            if declared_type != mime:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"File content ({mime}) does not match declared type ({declared_type})",
                )
            return

    # WebP: starts with RIFF....WEBP
    if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        if declared_type != "image/webp":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File content (image/webp) does not match declared type ({declared_type})",
            )
        return

    # No known signature matched
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="File content does not match any supported image format (PNG, JPEG, WebP)",
    )


# ------------------------------------------------------------------
# GET /images/
# ------------------------------------------------------------------
@router.get(
    "/",
    response_model=PaginatedImageListResponse,
    summary="List images for the authenticated user",
)
@limiter.limit(get_settings().RATE_LIMIT_READ)
async def list_images(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> PaginatedImageListResponse:
    """Return images belonging to the authenticated user, newest first."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    rows, total = db.list_images_by_user(user_id, page=page, page_size=page_size)
    return PaginatedImageListResponse(
        images=rows,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


# ------------------------------------------------------------------
# GET /images/{image_id}
# ------------------------------------------------------------------
@router.get(
    "/{image_id}",
    response_model=ImageRecord,
    summary="Get a single image by ID",
)
@limiter.limit(get_settings().RATE_LIMIT_READ)
async def get_image(
    request: Request,
    image_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
    storage: StorageService = Depends(get_storage_service),
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
    # Generate pre-signed URL for protected image
    if row.get("protected_url"):
        try:
            row["protected_url"] = await storage.generate_presigned_url(
                row["protected_url"], expires_in=3600,
            )
        except Exception:
            logger.warning("Failed to generate presigned URL for %s", image_id)
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
@limiter.limit(get_settings().RATE_LIMIT_UPLOAD)
async def upload_image(
    request: Request,
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
    storage: StorageService = Depends(get_storage_service),
    db: DatabaseService = Depends(get_database_service),
    queue: QueueService = Depends(get_queue_service),
) -> UploadResponse:
    """Accept an image upload and kick off the GPU protection pipeline.

    Flow:
        1. Validate the uploaded file (type, size, magic bytes).
        2. Upload the raw file to Cloudflare R2.
        3. Create an ``images`` row in Supabase (status = ``pending``).
        4. Push a task onto the Redis queue for the GPU worker.

    Returns:
        ``image_id`` and current ``status``.
    """
    # ── 0. Check usage limit ─────────────────────────────────────────
    can_upload, used, limit = check_user_usage_limit(user_id, db)
    if not can_upload:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly limit reached ({used}/{limit} images). Upgrade to Pro for unlimited processing.",
        )

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

    # Validate magic bytes match declared content type
    _validate_magic_bytes(file_bytes, content_type)

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
        assert image_id is not None
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

    return UploadResponse(image_id=image_id, status="pending")  # type: ignore[arg-type]


# ------------------------------------------------------------------
# DELETE /images/{image_id}
# ------------------------------------------------------------------
@router.delete(
    "/{image_id}",
    response_model=DeleteResponse,
    summary="Delete an image",
)
@limiter.limit(get_settings().RATE_LIMIT_UPLOAD)
async def delete_image(
    request: Request,
    image_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
    storage: StorageService = Depends(get_storage_service),
) -> DeleteResponse:
    """Delete an image and its associated files from R2."""
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

    # Delete files from R2
    try:
        if row.get("original_url"):
            await storage.delete_file(row["original_url"])
        if row.get("protected_url"):
            await storage.delete_file(row["protected_url"])
    except Exception:
        logger.warning("Failed to delete R2 files for image %s", image_id)

    # Soft-delete in DB
    db.delete_image(image_id)

    return DeleteResponse(image_id=image_id, deleted=True)


# ------------------------------------------------------------------
# POST /images/{image_id}/downloaded
# ------------------------------------------------------------------
@router.post(
    "/{image_id}/downloaded",
    response_model=DownloadTrackedResponse,
    summary="Track a completed image download event",
)
@limiter.limit(get_settings().RATE_LIMIT_READ)
async def track_download(
    request: Request,
    image_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> DownloadTrackedResponse:
    """Increment download count for a completed image."""
    image = db.get_image(image_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    if image["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    if image["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Download can only be tracked for completed images",
        )
    download_count = db.increment_download_count(image_id)
    return DownloadTrackedResponse(
        image_id=image_id,
        download_count=download_count,
    )


# ------------------------------------------------------------------
# GET /tasks/{image_id}/status
# ------------------------------------------------------------------

# Separate router so the URL is /api/v1/tasks/{image_id}/status
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])


@tasks_router.get(
    "/{image_id}/status",
    response_model=TaskStatusResponse,
    summary="Get task status for an image",
)
async def get_task_status(
    image_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> TaskStatusResponse:
    """Return current processing status for the given image.

    The frontend polls this endpoint until ``status`` is
    ``completed`` or ``failed``.
    """
    # Verify the image exists and belongs to the requesting user.
    image = db.get_image(image_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    if image["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Fetch the latest task row for this image.
    task = db.get_task_by_image_id(image_id)

    return TaskStatusResponse(
        image_id=image_id,
        status=image["status"],
        error_log=task.get("error_log") if task else None,
        started_at=task.get("started_at") if task else None,
        completed_at=task.get("completed_at") if task else None,
    )


@tasks_router.post(
    "/{image_id}/retry",
    response_model=RetryResponse,
    summary="Retry a failed task",
)
@limiter.limit(get_settings().RATE_LIMIT_UPLOAD)
async def retry_task(
    request: Request,
    image_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
    queue: QueueService = Depends(get_queue_service),
) -> RetryResponse:
    """Reset failed task to ``pending`` and enqueue for retry."""
    image = db.get_image(image_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )
    if image["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    if image["status"] != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed images can be retried",
        )

    storage_key: str | None = image.get("original_url")
    if not storage_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Original image key is missing; retry unavailable",
        )

    try:
        db.set_pending(image_id)
        await queue.enqueue(image_id=image_id, storage_key=storage_key)
    except Exception as exc:
        logger.exception("Retry enqueue failed for image %s", image_id)
        _mark_failed_safe(db, image_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue retry task",
        ) from exc

    return RetryResponse(image_id=image_id, status="pending", queued=True)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def check_user_usage_limit(user_id: str, db: DatabaseService) -> tuple[bool, int, int]:
    """
    Check if user has exceeded their monthly usage limit.
    
    Returns:
        (can_upload: bool, used: int, limit: int)
    """
    from datetime import datetime
    
    # Get user's subscription tier
    profile = db.get_profile(user_id)
    tier = profile.get("subscription_tier", "free") if profile else "free"
    
    # Pro users have no limit (or high limit)
    if tier == "pro":
        return True, 0, 100  # Pro limit is handled separately
    
    # Free tier: check monthly count
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    count = db.count_images_this_month(user_id, start_of_month.isoformat())
    
    return count < FREE_TIER_MONTHLY_LIMIT, count, FREE_TIER_MONTHLY_LIMIT


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
