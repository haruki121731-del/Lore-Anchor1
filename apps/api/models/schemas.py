"""Pydantic response/request schemas for the lore-anchor API."""

from __future__ import annotations

from pydantic import BaseModel


# ------------------------------------------------------------------
# Image schemas
# ------------------------------------------------------------------

class ImageRecord(BaseModel):
    id: str
    user_id: str
    original_url: str
    protected_url: str | None = None
    watermark_id: str | None = None
    status: str
    created_at: str
    updated_at: str


class ImageListResponse(BaseModel):
    images: list[ImageRecord]


class UploadResponse(BaseModel):
    image_id: str
    status: str


# ------------------------------------------------------------------
# Task schemas
# ------------------------------------------------------------------

class TaskStatusResponse(BaseModel):
    image_id: str
    status: str
    error_log: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
