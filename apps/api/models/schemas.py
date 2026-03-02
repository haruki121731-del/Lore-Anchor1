"""Pydantic response/request schemas for the lore-anchor API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Image schemas
# ------------------------------------------------------------------

class ImageRecord(BaseModel):
    model_config = {"populate_by_name": True}

    image_id: str = Field(validation_alias="id")
    user_id: str
    original_url: str
    protected_url: str | None = None
    watermark_id: str | None = None
    c2pa_manifest: dict[str, Any] | None = None
    download_count: int = 0
    status: str
    created_at: str
    updated_at: str


class ImageListResponse(BaseModel):
    images: list[ImageRecord]


class PaginatedImageListResponse(BaseModel):
    images: list[ImageRecord]
    total: int
    page: int
    page_size: int
    has_more: bool


class UploadResponse(BaseModel):
    image_id: str
    status: str


class DeleteResponse(BaseModel):
    image_id: str
    deleted: bool


class DownloadTrackedResponse(BaseModel):
    image_id: str
    download_count: int


# ------------------------------------------------------------------
# Task schemas
# ------------------------------------------------------------------

class TaskStatusResponse(BaseModel):
    image_id: str
    status: str
    error_log: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class RetryResponse(BaseModel):
    image_id: str
    status: str
    queued: bool
