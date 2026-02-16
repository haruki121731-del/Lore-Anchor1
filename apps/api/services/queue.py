"""Redis-backed task queue for dispatching GPU worker jobs."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from apps.api.core.config import get_settings

QUEUE_KEY: str = "lore_anchor_tasks"

logger: logging.Logger = logging.getLogger(__name__)


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
        """Push a task onto the ``lore_anchor_tasks`` list."""
        payload: dict[str, Any] = {
            "image_id": image_id,
            "storage_key": storage_key,
        }
        length: int = await self._redis.rpush(QUEUE_KEY, json.dumps(payload))
        return length

    async def queue_length(self) -> int:
        """Return the current number of pending tasks."""
        length: int = await self._redis.llen(QUEUE_KEY)
        return length

    async def close(self) -> None:
        """Gracefully close the underlying Redis connection."""
        await self._redis.aclose()


class DebugQueueService(QueueService):
    """No-op stub used when ``DEBUG=true``.

    Logs enqueue calls without connecting to Redis.
    """

    def __init__(self) -> None:
        self._length: int = 0
        logger.info("[DEBUG] QueueService using log-only stub (no Redis)")

    async def enqueue(self, image_id: str, storage_key: str) -> int:
        self._length += 1
        logger.info(
            "[DEBUG] Queue enqueue (skipped): image_id=%s, storage_key=%s, queue_len=%d",
            image_id,
            storage_key,
            self._length,
        )
        return self._length

    async def queue_length(self) -> int:
        return self._length

    async def close(self) -> None:
        pass


def get_queue_service() -> QueueService:
    """Return a :class:`QueueService` instance.

    In DEBUG mode, returns a :class:`DebugQueueService` that only logs
    enqueue calls without connecting to Redis.
    """
    if get_settings().DEBUG:
        return DebugQueueService()
    return QueueService()
