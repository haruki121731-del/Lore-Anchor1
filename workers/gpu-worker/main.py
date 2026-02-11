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
import tempfile
import uuid
from pathlib import Path

import torch
from arq import create_pool
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


if __name__ == "__main__":
    import asyncio

    from arq import run_worker

    logger.info("Starting GPU Worker...")
    run_worker(WorkerSettings)  # type: ignore[arg-type]
