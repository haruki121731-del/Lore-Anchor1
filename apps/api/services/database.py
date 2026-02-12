"""Supabase database operations for the ``images`` table."""

from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from apps.api.core.config import get_settings

# MDD Section 4.2 – valid status transitions
_VALID_STATUSES: set[str] = {"pending", "processing", "completed", "failed"}

_TABLE_IMAGES: str = "images"


class DatabaseService:
    """Async-friendly wrapper around the Supabase Python SDK.

    Note: The official ``supabase-py`` SDK is synchronous under the hood, so
    callers in an async context should use ``asyncio.to_thread`` for
    CPU-bound / long-running queries when needed.  For typical small
    queries the overhead is negligible and direct calls are acceptable.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client: Client = create_client(
            settings.NEXT_PUBLIC_SUPABASE_URL,
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
        """Insert a new row into ``images`` with status ``'pending'``.

        Args:
            user_id: UUID of the authenticated user (from Supabase Auth).
            original_url: R2 private URL / object key of the uploaded image.
            watermark_id: Optional PixelSeal 128-bit ID (set later by worker).

        Returns:
            The inserted row as a dict.
        """
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
        return dict(response.data[0])

    # ------------------------------------------------------------------
    # images table – READ
    # ------------------------------------------------------------------

    def get_image(self, image_id: str) -> dict[str, Any] | None:
        """Fetch a single image row by its primary key.

        Returns:
            The row as a dict, or ``None`` if not found.
        """
        response = (
            self._client.table(_TABLE_IMAGES)
            .select("*")
            .eq("id", image_id)
            .execute()
        )
        if response.data:
            return dict(response.data[0])
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
        return [dict(row) for row in response.data]

    # ------------------------------------------------------------------
    # images table – UPDATE
    # ------------------------------------------------------------------

    def update_status(self, image_id: str, status: str) -> dict[str, Any]:
        """Set the ``status`` column of an image row.

        Args:
            image_id: UUID of the target row.
            status: One of ``pending``, ``processing``, ``completed``,
                    ``failed``.

        Raises:
            ValueError: If *status* is not a valid value.

        Returns:
            The updated row as a dict.
        """
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
        return dict(response.data[0])

    def set_protected_url(
        self,
        image_id: str,
        protected_url: str,
    ) -> dict[str, Any]:
        """Populate ``protected_url`` and mark the image as ``completed``.

        Called by the webhook handler once the GPU worker finishes.
        """
        response = (
            self._client.table(_TABLE_IMAGES)
            .update({"protected_url": protected_url, "status": "completed"})
            .eq("id", image_id)
            .execute()
        )
        return dict(response.data[0])

    def set_failed(
        self,
        image_id: str,
    ) -> dict[str, Any]:
        """Mark the image as ``failed``.

        Called when the GPU worker reports an unrecoverable error.
        """
        return self.update_status(image_id, "failed")


def get_database_service() -> DatabaseService:
    """Return a new :class:`DatabaseService` instance."""
    return DatabaseService()
