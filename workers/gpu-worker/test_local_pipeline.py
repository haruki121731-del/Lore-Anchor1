#!/usr/bin/env python3
"""
Local integration test for the GPU Worker pipeline.

Runs the full defense pipeline (PixelSeal -> Mist v2 -> C2PA) on a test
image **without** Docker or Redis.  Validates that the core logic works
end-to-end on the current machine (CPU fallback mode).

Usage:
    python workers/gpu-worker/test_local_pipeline.py [IMAGE_PATH]

If IMAGE_PATH is omitted a synthetic 512x512 test image is generated.
"""
from __future__ import annotations

import logging
import sys
import tempfile
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

# Allow running from repo root
_WORKER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_WORKER_DIR))

from core.c2pa_sign import sign_c2pa  # noqa: E402
from core.mist.mist_v2 import apply_mist_v2  # noqa: E402
from core.seal.pixelseal import embed_watermark, extract_watermark  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test-local-pipeline")


def _create_test_image(size: int = 512) -> Image.Image:
    """Generate a colourful synthetic image for testing."""
    arr = np.random.randint(0, 255, (size, size, 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def main(image_path: str | None = None) -> None:
    logger.info("=" * 60)
    logger.info("lore-anchor Local Pipeline Test")
    logger.info("=" * 60)

    # --- Load or generate image ---
    if image_path:
        image = Image.open(image_path).convert("RGB")
        logger.info("Loaded image: %s (%dx%d)", image_path, *image.size)
    else:
        image = _create_test_image()
        logger.info("Generated synthetic test image (512x512)")

    watermark_id: str = uuid.uuid4().hex[:32]

    try:
        import torch
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    except ImportError:
        device = "cpu"  # type: ignore[assignment]
    logger.info("Device: %s", device)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # --- Step 1: PixelSeal ---
        logger.info("Step 1: PixelSeal watermark (id=%s)", watermark_id)
        watermarked = embed_watermark(image, watermark_id, device=device)
        watermarked.save(tmp / "watermarked.png")
        logger.info("  OK — Watermark embedded")

        # Verify extraction
        extracted = extract_watermark(watermarked)
        match = extracted == watermark_id
        logger.info("  OK — Round-trip: extracted=%s match=%s", extracted, match)

        # --- Step 2: Mist v2 ---
        logger.info("Step 2: Mist v2 (epsilon=8, steps=3)")
        protected = apply_mist_v2(watermarked, epsilon=8, steps=3, device=device)
        protected.save(tmp / "protected.png")
        logger.info("  OK — Adversarial perturbation applied")

        # --- Step 3: C2PA ---
        logger.info("Step 3: C2PA signing")
        protected_path = str(tmp / "protected.png")
        signed_path = str(tmp / "signed.png")
        sign_c2pa(protected_path, signed_path)
        logger.info("  OK — C2PA signed")

        # --- Copy result to output ---
        output_dir = Path("tmp/test_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"protected_{watermark_id[:8]}.png"

        final = Image.open(signed_path)
        final.save(output_path)
        logger.info("Result saved: %s", output_path.resolve())

    logger.info("=" * 60)
    logger.info("ALL STEPS PASSED")
    logger.info("=" * 60)


if __name__ == "__main__":
    img_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(img_arg)
