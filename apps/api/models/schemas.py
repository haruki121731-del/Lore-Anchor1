"""Pydantic response/request schemas for the lore-anchor API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Image schemas
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
# Task schemas
# ------------------------------------------------------------------

class TaskStatusResponse(BaseModel):
    image_id: str
    status: str
    error_log: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
