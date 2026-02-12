"""Redis-backed task queue for dispatching GPU worker jobs."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from apps.api.core.config import get_settings

_QUEUE_KEY: str = "lore_anchor_tasks"


class QueueService:
    """Thin async wrapper that pushes task payloads onto a Redis list.

    Workers consume tasks from the same list via ``BLPOP`` / ``LPOP``.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._redis: aioredis.Redis = aioredis.from_url(  # type: ignore[assignment]
            settings.REDIS_URL,
            decode_responses=True,
        )

    async def enqueue(self, image_id: str, storage_key: str) -> int:
        """Push a task onto the ``lore_anchor_tasks`` list.

        Args:
            image_id: UUID of the ``images`` row.
            storage_key: R2 object key where the original file lives.

        Returns:
            The new length of the list after the push.
        """
        payload: dict[str, Any] = {
            "image_id": image_id,
            "storage_key": storage_key,
        }
        length: int = await self._redis.rpush(_QUEUE_KEY, json.dumps(payload))
        return length

    async def queue_length(self) -> int:
        """Return the current number of pending tasks."""
        length: int = await self._redis.llen(_QUEUE_KEY)
        return length

    async def close(self) -> None:
        """Gracefully close the underlying Redis connection."""
        await self._redis.aclose()


def get_queue_service() -> QueueService:
    """Return a new :class:`QueueService` instance."""
    return QueueService()
