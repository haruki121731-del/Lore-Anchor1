"""
lore-anchor GPU Worker Entrypoint

Pulls tasks from Redis queue (via arq), executes the defense pipeline:
  Step 1: PixelSeal (invisible watermark)
  Step 2: Mist v2 (adversarial perturbation)
  Step 3: C2PA signing
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import tempfile
import uuid
from pathlib import Path

import torch
from arq.connections import RedisSettings
from dotenv import load_dotenv
from PIL import Image

from core.mist.mist_v2 import apply_mist_v2
from core.seal.pixelseal import embed_watermark
from core.storage import download_from_r2, upload_to_r2
from core.c2pa_sign import sign_c2pa

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
R2_BUCKET: str = os.getenv("R2_BUCKET_NAME", "")


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
            mem_gb = mem / (1024 ** 3)
            logger.info("  GPU %d: %s (%.1f GB VRAM)", i, name, mem_gb)
        logger.info("Current device: %s", torch.cuda.current_device())
    else:
        logger.warning("No CUDA GPU detected — will use CPU (slow)")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
async def process_image(
    ctx: dict,
    image_id: str,
    original_r2_key: str,
) -> dict[str, str]:
    """Execute the full defense pipeline for a single image.

    Args:
        ctx: arq worker context (contains redis pool, etc.)
        image_id: UUID of the image record in Supabase.
        original_r2_key: R2 object key for the original uploaded image.

    Returns:
        dict with ``protected_r2_key`` and ``watermark_id``.
    """
    logger.info("Starting pipeline for image_id=%s", image_id)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using device: %s", device)

    watermark_id = uuid.uuid4().hex[:32]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        original_path = tmp / "original.png"
        watermarked_path = tmp / "watermarked.png"
        protected_path = tmp / "protected.png"
        signed_path = tmp / "signed.png"

        # --- Download original from R2 ---
        logger.info("Downloading original image from R2: %s", original_r2_key)
        download_from_r2(original_r2_key, str(original_path))

        image = Image.open(original_path).convert("RGB")

        # --- Step 1: PixelSeal watermark ---
        logger.info("Step 1: Embedding PixelSeal watermark (id=%s)", watermark_id)
        try:
            watermarked = embed_watermark(image, watermark_id, device=device)
            watermarked.save(watermarked_path)
        except Exception:
            logger.exception("PixelSeal watermark failed for image_id=%s", image_id)
            raise

        # --- Step 2: Mist v2 adversarial perturbation ---
        logger.info(
            "Step 2: Applying Mist v2 (epsilon=%d, steps=%d)",
            MIST_EPSILON,
            MIST_STEPS,
        )
        try:
            protected = apply_mist_v2(
                watermarked,
                epsilon=MIST_EPSILON,
                steps=MIST_STEPS,
                device=device,
            )
            protected.save(protected_path)
        except Exception:
            logger.exception("Mist v2 failed for image_id=%s", image_id)
            raise

        # --- Step 3: C2PA signing ---
        logger.info("Step 3: Signing with C2PA")
        try:
            sign_c2pa(str(protected_path), str(signed_path))
        except Exception:
            logger.exception("C2PA signing failed for image_id=%s", image_id)
            raise

        # --- Upload result to R2 ---
        protected_r2_key = f"protected/{image_id}.png"
        logger.info("Uploading protected image to R2: %s", protected_r2_key)
        upload_to_r2(str(signed_path), protected_r2_key)

    logger.info("Pipeline completed for image_id=%s", image_id)
    return {
        "protected_r2_key": protected_r2_key,
        "watermark_id": watermark_id,
    }


# ---------------------------------------------------------------------------
# arq Worker class
# ---------------------------------------------------------------------------
class WorkerSettings:
    """arq worker settings."""

    functions = [process_image]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 1  # GPU bound — one job at a time
    job_timeout = 600  # 10 minutes per image


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from arq import run_worker

    # --- Startup diagnostics ---
    logger.info("=" * 60)
    logger.info("lore-anchor GPU Worker starting")
    logger.info("=" * 60)
    _log_gpu_info()
    logger.info("Redis URL: %s", REDIS_URL.split("@")[-1])  # hide password
    logger.info("Mist config: epsilon=%d, steps=%d", MIST_EPSILON, MIST_STEPS)
    logger.info("=" * 60)

    # --- Graceful shutdown on SIGTERM (SaladCloud sends this on stop) ---
    def _handle_sigterm(signum: int, frame) -> None:  # type: ignore[no-untyped-def]
        logger.info("Received SIGTERM — shutting down gracefully")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    # --- Start arq worker (blocks indefinitely, polling Redis for jobs) ---
    logger.info("Worker entering arq run loop (waiting for jobs)...")
    run_worker(WorkerSettings)  # type: ignore[arg-type]
