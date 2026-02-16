#!/usr/bin/env python3
"""
Queue integration test — validates that the API's RPUSH and the
Worker's BLPOP use the same Redis key and payload format.

Requires a running Redis instance (set REDIS_URL env var).

Usage:
    # Terminal 1: Start the worker
    cd workers/gpu-worker && python main.py

    # Terminal 2: Enqueue a test task
    python workers/gpu-worker/test_queue_integration.py
"""
from __future__ import annotations

import json
import logging
import os

import redis
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test-queue")

# Must match both apps/api/services/queue.py and workers/gpu-worker/main.py
QUEUE_KEY: str = "lore_anchor_tasks"


def main() -> None:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    logger.info("Connecting to Redis: %s", redis_url.split("@")[-1])

    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    logger.info("Redis connection OK")

    # Enqueue a test task with the same format as apps/api/services/queue.py
    payload: dict[str, str] = {
        "image_id": "test-image-00000000",
        "storage_key": "raw/test-user/test-image.jpg",
    }
    length: int = r.rpush(QUEUE_KEY, json.dumps(payload))
    logger.info("Enqueued test task (queue length=%d): %s", length, payload)
    logger.info(
        "If the worker is running, it should pick up this task within ~5 seconds."
    )
    logger.info(
        "Check worker logs for: 'Starting pipeline for image_id=test-image-00000000'"
    )


if __name__ == "__main__":
    main()
