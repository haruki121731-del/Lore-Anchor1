"""
lore-anchor GPU Worker Entrypoint

Pulls tasks from Redis queue (BLPOP on ``lore_anchor_tasks``), executes
the defense pipeline:
  Step 1: PixelSeal (invisible watermark)
  Step 2: Mist v2 (adversarial perturbation)
  Step 3: C2PA signing

After processing, updates Supabase ``images`` status and records
progress in the ``tasks`` table.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import signal
import sys
import tempfile
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import redis
import torch
from dotenv import load_dotenv
from PIL import Image
from supabase import Client, create_client

from core.c2pa_sign import sign_c2pa
from core.mist.mist_v2 import apply_mist_v2
from core.seal.pixelseal import embed_watermark
from core.storage import download_from_r2, upload_to_r2

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gpu-worker")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
MIST_EPSILON: int = int(os.getenv("MIST_EPSILON", "8"))
MIST_STEPS: int = int(os.getenv("MIST_STEPS", "3"))
R2_PUBLIC_DOMAIN: str = os.getenv("R2_PUBLIC_DOMAIN", "")
WORKER_ID: str = platform.node()

# Must match apps/api/services/queue.py QUEUE_KEY
QUEUE_KEY: str = "lore_anchor_tasks"

_shutdown_requested: bool = False
_processing: bool = False


class PipelineStepError(Exception):
    """Raised when a specific pipeline step fails."""

    def __init__(self, step: str, original: Exception) -> None:
        self.step = step
        self.original = original
        super().__init__(f"Step: {step} | Error: {original}")


# ---------------------------------------------------------------------------
# Supabase client (service-role for server-side writes)
# ---------------------------------------------------------------------------
def _init_supabase() -> Client:
    """Initialise and return a Supabase client using service-role key."""
    url: str = os.getenv("SUPABASE_URL", "")
    key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — DB updates disabled")
    return create_client(url, key)


def _get_image_status(sb: Client, image_id: str) -> str | None:
    """Fetch the current status of an image from Supabase.

    Returns the status string, or ``None`` if the row is not found.
    """
    try:
        result = sb.table("images").select("status").eq("id", image_id).execute()
        if result.data:
            return result.data[0]["status"]
        return None
    except Exception:
        logger.exception("Failed to fetch image status for image_id=%s", image_id)
        return None


def _update_image_status(
    sb: Client,
    image_id: str,
    status: str,
    *,
    protected_url: str | None = None,
    watermark_id: str | None = None,
    error_log: str | None = None,
) -> None:
    """Update the ``images`` row for *image_id* in Supabase."""
    data: dict[str, Any] = {"status": status}
    if protected_url is not None:
        data["protected_url"] = protected_url
    if watermark_id is not None:
        data["watermark_id"] = watermark_id
    if error_log is not None:
        data["error_log"] = error_log[:4000]
    try:
        sb.table("images").update(data).eq("id", image_id).execute()
        logger.info("images.status -> '%s' for image_id=%s", status, image_id)
    except Exception:
        logger.exception("Failed to update images status for image_id=%s", image_id)


def _insert_task(sb: Client, image_id: str) -> str | None:
    """Insert a new row into ``tasks`` and return its id."""
    try:
        result = (
            sb.table("tasks")
            .insert({
                "image_id": image_id,
                "worker_id": WORKER_ID,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )
        task_id: str = result.data[0]["id"]
        logger.info("tasks row created: task_id=%s for image_id=%s", task_id, image_id)
        return task_id
    except Exception:
        logger.exception("Failed to insert tasks row for image_id=%s", image_id)
        return None


def _complete_task(sb: Client, task_id: str) -> None:
    """Mark a task as completed."""
    try:
        sb.table("tasks").update({
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", task_id).execute()
    except Exception:
        logger.exception("Failed to update task completed_at for task_id=%s", task_id)


def _fail_task(sb: Client, task_id: str, error_msg: str) -> None:
    """Record an error on the task."""
    try:
        sb.table("tasks").update({
            "error_log": error_msg[:4000],
        }).eq("id", task_id).execute()
    except Exception:
        logger.exception("Failed to update task error_log for task_id=%s", task_id)


# ---------------------------------------------------------------------------
# GPU diagnostics (logged at startup for SaladCloud verification)
# ---------------------------------------------------------------------------
def _log_gpu_info() -> None:
    """Log CUDA availability and GPU details."""
    cuda_available = torch.cuda.is_available()
    logger.info("CUDA available: %s", cuda_available)
    logger.info("PyTorch version: %s", torch.__version__)
    logger.info("CUDA build version: %s", torch.version.cuda or "N/A")

    if cuda_available:
        device_count = torch.cuda.device_count()
        logger.info("GPU count: %d", device_count)
        for i in range(device_count):
            name = torch.cuda.get_device_name(i)
            mem = torch.cuda.get_device_properties(i).total_mem
            mem_gb = mem / (1024**3)
            logger.info("  GPU %d: %s (%.1f GB VRAM)", i, name, mem_gb)
        logger.info("Current device: %s", torch.cuda.current_device())
    else:
        logger.warning("No CUDA GPU detected — will use CPU (slow)")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def process_image(image_id: str, original_r2_key: str) -> dict[str, str]:
    """Execute the full defense pipeline for a single image.

    Each step is wrapped individually so that failures report the exact
    step name.  On failure a ``PipelineStepError`` is raised.

    Args:
        image_id: UUID of the image record in Supabase.
        original_r2_key: R2 object key for the original uploaded image.

    Returns:
        dict with ``protected_r2_key`` and ``watermark_id``.
    """
    logger.info("Starting pipeline for image_id=%s", image_id)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using device: %s", device)

    watermark_id: str = uuid.uuid4().hex[:32]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        original_path = tmp / "original.png"
        watermarked_path = tmp / "watermarked.png"
        protected_path = tmp / "protected.png"
        signed_path = tmp / "signed.png"

        # --- Step: download ---
        try:
            logger.info("Step: download — fetching from R2: %s", original_r2_key)
            download_from_r2(original_r2_key, str(original_path))
            image = Image.open(original_path).convert("RGB")
            logger.info("Step completed: download for image_id=%s", image_id)
        except Exception as exc:
            raise PipelineStepError("download", exc) from exc

        # --- Step: pixelseal ---
        try:
            logger.info("Step: pixelseal — embedding watermark (id=%s)", watermark_id)
            watermarked = embed_watermark(image, watermark_id, device=device)
            watermarked.save(watermarked_path)
            logger.info("Step completed: pixelseal for image_id=%s", image_id)
        except Exception as exc:
            raise PipelineStepError("pixelseal", exc) from exc

        # --- Step: mist_v2 ---
        try:
            logger.info(
                "Step: mist_v2 — applying perturbation (epsilon=%d, steps=%d)",
                MIST_EPSILON,
                MIST_STEPS,
            )
            protected = apply_mist_v2(
                watermarked,
                epsilon=MIST_EPSILON,
                steps=MIST_STEPS,
                device=device,
            )
            protected.save(protected_path)
            logger.info("Step completed: mist_v2 for image_id=%s", image_id)
        except Exception as exc:
            raise PipelineStepError("mist_v2", exc) from exc

        # --- Step: c2pa_sign ---
        try:
            logger.info("Step: c2pa_sign — signing image")
            sign_c2pa(str(protected_path), str(signed_path))
            logger.info("Step completed: c2pa_sign for image_id=%s", image_id)
        except Exception as exc:
            raise PipelineStepError("c2pa_sign", exc) from exc

        # --- Step: upload ---
        try:
            protected_r2_key = f"protected/{image_id}.png"
            logger.info("Step: upload — uploading to R2: %s", protected_r2_key)
            upload_to_r2(str(signed_path), protected_r2_key)
            logger.info("Step completed: upload for image_id=%s", image_id)
        except Exception as exc:
            raise PipelineStepError("upload", exc) from exc

    return {
        "protected_r2_key": protected_r2_key,
        "watermark_id": watermark_id,
    }


# ---------------------------------------------------------------------------
# Redis BLPOP consumer loop
# ---------------------------------------------------------------------------
def _run_consumer() -> None:
    """Block on Redis ``BLPOP`` and process tasks one at a time."""
    global _processing

    r = redis.from_url(REDIS_URL, decode_responses=True)
    sb = _init_supabase()
    logger.info("Worker started, listening on queue: %s", QUEUE_KEY)

    while not _shutdown_requested:
        # BLPOP blocks for up to 5 seconds, then re-checks shutdown flag.
        result: tuple[str, str] | None = r.blpop(QUEUE_KEY, timeout=5)  # type: ignore[assignment]
        if result is None:
            continue

        _key, raw_payload = result
        logger.info("Received raw task payload: %s", raw_payload)

        try:
            payload: dict[str, Any] = json.loads(raw_payload)
            image_id: str = payload["image_id"]
            storage_key: str = payload["storage_key"]
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Invalid task payload: %s — %s", raw_payload, exc)
            continue

        logger.info("Received task: image_id=%s", image_id)

        # --- Dedup check: skip if already processing or completed ---
        current_status = _get_image_status(sb, image_id)
        if current_status in ("processing", "completed"):
            logger.warning(
                "Skipping duplicate task: image_id=%s already has status='%s'",
                image_id,
                current_status,
            )
            continue
        if current_status is None:
            logger.warning(
                "Image row not found for image_id=%s, processing anyway",
                image_id,
            )

        # --- Mark as processing ---
        _processing = True
        t_start = time.monotonic()
        _update_image_status(sb, image_id, "processing")
        task_id = _insert_task(sb, image_id)

        try:
            result_data = process_image(image_id, storage_key)

            # --- Build public URL for the protected image ---
            protected_r2_key: str = result_data["protected_r2_key"]
            protected_url: str = (
                f"{R2_PUBLIC_DOMAIN}/{protected_r2_key}"
                if R2_PUBLIC_DOMAIN
                else protected_r2_key
            )

            # --- Mark success in Supabase ---
            _update_image_status(
                sb,
                image_id,
                "completed",
                protected_url=protected_url,
                watermark_id=result_data["watermark_id"],
            )
            if task_id:
                _complete_task(sb, task_id)

            elapsed = time.monotonic() - t_start
            logger.info("Pipeline completed: image_id=%s in %.1fs", image_id, elapsed)

        except PipelineStepError as exc:
            elapsed = time.monotonic() - t_start
            error_detail = f"Step: {exc.step} | Error: {exc.original}"
            logger.error(
                "Pipeline failed at step %s: image_id=%s | %s (%.1fs elapsed)",
                exc.step,
                image_id,
                exc.original,
                elapsed,
            )

            # --- Mark failure in Supabase ---
            _update_image_status(
                sb, image_id, "failed", error_log=error_detail,
            )
            if task_id:
                _fail_task(sb, task_id, error_detail)

        except Exception:
            elapsed = time.monotonic() - t_start
            error_detail = traceback.format_exc()
            logger.exception(
                "Pipeline failed (unexpected): image_id=%s (%.1fs elapsed)",
                image_id,
                elapsed,
            )

            # --- Mark failure in Supabase ---
            _update_image_status(
                sb, image_id, "failed", error_log=error_detail,
            )
            if task_id:
                _fail_task(sb, task_id, error_detail)

        finally:
            _processing = False

    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # --- Startup diagnostics ---
    logger.info("=" * 60)
    logger.info("lore-anchor GPU Worker starting")
    logger.info("=" * 60)
    _log_gpu_info()
    logger.info("Redis URL: %s", REDIS_URL.split("@")[-1])  # hide password
    logger.info("Mist config: epsilon=%d, steps=%d", MIST_EPSILON, MIST_STEPS)
    logger.info("Queue key: %s", QUEUE_KEY)
    logger.info("Worker ID: %s", WORKER_ID)
    logger.info("=" * 60)

    # --- Graceful shutdown on SIGTERM (SaladCloud sends this on stop) ---
    def _handle_sigterm(signum: int, frame: Any) -> None:
        global _shutdown_requested
        logger.info("Shutdown signal received, finishing current task...")
        _shutdown_requested = True

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    # --- Start BLPOP consumer loop ---
    logger.info("Worker started, listening on queue: %s", QUEUE_KEY)
    try:
        _run_consumer()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt — exiting")
    finally:
        if _processing:
            logger.info("Waiting for current task to finish before exit...")
        logger.info("Worker stopped.")
        sys.exit(0)
