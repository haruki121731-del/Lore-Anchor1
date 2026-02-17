"""Supabase database operations for the ``images`` table."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from apps.api.core.config import get_settings

# MDD Section 4.2 – valid status transitions
_VALID_STATUSES: set[str] = {"pending", "processing", "completed", "failed"}

_TABLE_IMAGES: str = "images"
_TABLE_TASKS: str = "tasks"

logger: logging.Logger = logging.getLogger(__name__)


class DatabaseService:
    """Async-friendly wrapper around the Supabase Python SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )

    # ------------------------------------------------------------------
    # images table – CREATE
    # ------------------------------------------------------------------

    def create_image(
        self,
        user_id: str,
        original_url: str,
        watermark_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new row into ``images`` with status ``'pending'``."""
        row: dict[str, Any] = {
            "user_id": user_id,
            "original_url": original_url,
            "status": "pending",
        }
        if watermark_id is not None:
            row["watermark_id"] = watermark_id

        response = (
            self._client.table(_TABLE_IMAGES).insert(row).execute()
        )
        return dict(response.data[0])  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # images table – READ
    # ------------------------------------------------------------------

    def get_image(self, image_id: str) -> dict[str, Any] | None:
        """Fetch a single image row by its primary key."""
        response = (
            self._client.table(_TABLE_IMAGES)
            .select("*")
            .eq("id", image_id)
            .execute()
        )
        if response.data:
            return dict(response.data[0])  # type: ignore[arg-type]
        return None

    def list_images_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return all image rows belonging to *user_id*, newest first."""
        response = (
            self._client.table(_TABLE_IMAGES)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [dict(row) for row in response.data]  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # images table – UPDATE
    # ------------------------------------------------------------------

    def update_status(self, image_id: str, status: str) -> dict[str, Any]:
        """Set the ``status`` column of an image row."""
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of {_VALID_STATUSES}"
            )
        response = (
            self._client.table(_TABLE_IMAGES)
            .update({"status": status})
            .eq("id", image_id)
            .execute()
        )
        return dict(response.data[0])  # type: ignore[arg-type]

    def set_protected_url(
        self,
        image_id: str,
        protected_url: str,
        watermark_id: str | None = None,
        c2pa_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Populate ``protected_url`` and mark the image as ``completed``."""
        update_data: dict[str, Any] = {
            "protected_url": protected_url,
            "status": "completed",
        }
        if watermark_id is not None:
            update_data["watermark_id"] = watermark_id
        if c2pa_manifest is not None:
            update_data["c2pa_manifest"] = c2pa_manifest
        response = (
            self._client.table(_TABLE_IMAGES)
            .update(update_data)
            .eq("id", image_id)
            .execute()
        )
        return dict(response.data[0])  # type: ignore[arg-type]

    def set_failed(self, image_id: str) -> dict[str, Any]:
        """Mark the image as ``failed``."""
        return self.update_status(image_id, "failed")

    # ------------------------------------------------------------------
    # tasks table – READ
    # ------------------------------------------------------------------

    def get_task_by_image_id(self, image_id: str) -> dict[str, Any] | None:
        """Return the most recent task row for *image_id*, or ``None``."""
        response = (
            self._client.table(_TABLE_TASKS)
            .select("*")
            .eq("image_id", image_id)
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return dict(response.data[0])  # type: ignore[arg-type]
        return None


class DebugDatabaseService(DatabaseService):
    """In-memory stub used when ``DEBUG=true``.

    Stores image records in a plain dict instead of Supabase.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        logger.info("[DEBUG] DatabaseService using in-memory store")

    def create_image(
        self,
        user_id: str,
        original_url: str,
        watermark_id: str | None = None,
    ) -> dict[str, Any]:
        image_id: str = str(uuid.uuid4())
        now: str = datetime.now(timezone.utc).isoformat()
        row: dict[str, Any] = {
            "id": image_id,
            "user_id": user_id,
            "original_url": original_url,
            "protected_url": None,
            "watermark_id": watermark_id,
            "c2pa_manifest": None,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        self._store[image_id] = row
        logger.info("[DEBUG] DB insert: image_id=%s", image_id)
        return dict(row)

    def get_image(self, image_id: str) -> dict[str, Any] | None:
        row = self._store.get(image_id)
        return dict(row) if row else None

    def list_images_by_user(self, user_id: str) -> list[dict[str, Any]]:
        return [
            dict(r) for r in self._store.values()
            if r["user_id"] == user_id
        ]

    def update_status(self, image_id: str, status: str) -> dict[str, Any]:
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of {_VALID_STATUSES}"
            )
        row = self._store.get(image_id)
        if row is None:
            raise KeyError(f"Image {image_id} not found in debug store")
        row["status"] = status
        row["updated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("[DEBUG] DB update: image_id=%s -> status=%s", image_id, status)
        return dict(row)

    def set_protected_url(
        self,
        image_id: str,
        protected_url: str,
        watermark_id: str | None = None,
        c2pa_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = self._store.get(image_id)
        if row is None:
            raise KeyError(f"Image {image_id} not found in debug store")
        row["protected_url"] = protected_url
        row["status"] = "completed"
        row["updated_at"] = datetime.now(timezone.utc).isoformat()
        if watermark_id is not None:
            row["watermark_id"] = watermark_id
        if c2pa_manifest is not None:
            row["c2pa_manifest"] = c2pa_manifest
        logger.info("[DEBUG] DB update: image_id=%s -> completed", image_id)
        return dict(row)


    def get_task_by_image_id(self, image_id: str) -> dict[str, Any] | None:
        """Debug stub — always returns ``None`` (no tasks table)."""
        return None


def get_database_service() -> DatabaseService:
    """Return a :class:`DatabaseService` instance.

    In DEBUG mode, returns a :class:`DebugDatabaseService` backed by an
    in-memory dict instead of Supabase.
    """
    if get_settings().DEBUG:
        return DebugDatabaseService()
    return DatabaseService()
