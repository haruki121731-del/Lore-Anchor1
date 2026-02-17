#!/usr/bin/env python3
"""
Smoke test for the GPU Worker core modules.

Runs entirely on CPU with no model downloads — validates that the full
pipeline (PixelSeal DWT + Mist v2 freq) produces valid output and that
the watermark survives the perturbation.

Usage:
    cd workers/gpu-worker
    python -m tests.smoke_test
"""
from __future__ import annotations

import logging
import sys
import uuid

import numpy as np
from PIL import Image

# Adjust path so we can import core.* when running from workers/gpu-worker/
sys.path.insert(0, ".")

from core.seal.pixelseal import embed_watermark, verify_watermark
from core.mist.mist_v2 import apply_mist_v2

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("smoke_test")


def _make_test_image(width: int = 256, height: int = 256) -> Image.Image:
    """Create a synthetic RGB test image with gradients and shapes."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    # Red gradient
    arr[:, :, 0] = np.linspace(0, 255, width, dtype=np.uint8)
    # Green gradient
    arr[:, :, 1] = np.linspace(0, 255, height, dtype=np.uint8)[:, None]
    # Blue circle
    cy, cx = height // 2, width // 2
    y, x = np.ogrid[:height, :width]
    mask = (x - cx) ** 2 + (y - cy) ** 2 < (min(width, height) // 4) ** 2
    arr[mask, 2] = 200
    return Image.fromarray(arr)


def test_pixelseal_dwt_roundtrip() -> None:
    """Embed then extract — IDs must match exactly on clean image."""
    logger.info("=== Test: PixelSeal DWT round-trip ===")
    img = _make_test_image()
    wm_id = uuid.uuid4().hex

    watermarked = embed_watermark(img, wm_id, backend="dwt")
    assert watermarked.size == img.size, "Size changed after watermarking"

    # Pixel diff should be small (invisible)
    diff = np.abs(
        np.array(watermarked, dtype=np.float32) - np.array(img, dtype=np.float32)
    )
    max_diff = diff.max()
    mean_diff = diff.mean()
    logger.info("  Pixel diff — max=%.1f  mean=%.2f", max_diff, mean_diff)
    assert max_diff < 30, f"Watermark too visible (max diff {max_diff})"

    # Extract and verify
    match, accuracy = verify_watermark(watermarked, wm_id, backend="dwt")
    logger.info("  Bit accuracy: %.1f%%  match=%s", accuracy * 100, match)
    assert match, f"Watermark lost on clean image (accuracy={accuracy:.1%})"
    assert accuracy > 0.95, f"Accuracy too low: {accuracy:.1%}"
    logger.info("  PASSED")


def test_pixelseal_survives_mist() -> None:
    """Watermark should survive Mist v2 freq perturbation (ε=8)."""
    logger.info("=== Test: PixelSeal survives Mist v2 (freq mode) ===")
    img = _make_test_image(512, 512)  # larger image = more spreading gain
    wm_id = uuid.uuid4().hex

    # Step 1: watermark
    watermarked = embed_watermark(img, wm_id, backend="dwt")

    # Step 2: adversarial perturbation
    protected = apply_mist_v2(watermarked, epsilon=8, steps=1, mode="freq")
    assert protected.size == watermarked.size

    # Verify watermark survives
    match, accuracy = verify_watermark(protected, wm_id, backend="dwt")
    logger.info("  Bit accuracy after Mist: %.1f%%  match=%s", accuracy * 100, match)
    assert match, f"Watermark destroyed by Mist (accuracy={accuracy:.1%})"
    logger.info("  PASSED")


def test_mist_freq_output() -> None:
    """Mist v2 freq mode should produce a visibly different image."""
    logger.info("=== Test: Mist v2 freq mode output ===")
    img = _make_test_image()

    protected = apply_mist_v2(img, epsilon=16, steps=1, mode="freq")
    assert protected.size == img.size

    diff = np.abs(
        np.array(protected, dtype=np.float32) - np.array(img, dtype=np.float32)
    )
    max_diff = diff.max()
    mean_diff = diff.mean()
    logger.info("  Perturbation — max=%.1f  mean=%.2f", max_diff, mean_diff)
    assert max_diff > 0, "No perturbation applied"
    assert max_diff <= 16 + 1, f"Perturbation exceeds epsilon (max={max_diff})"
    logger.info("  PASSED")


def main() -> None:
    logger.info("Starting smoke tests...\n")
    tests = [
        test_pixelseal_dwt_roundtrip,
        test_mist_freq_output,
        test_pixelseal_survives_mist,
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            logger.error("  FAILED: %s", e)
            failed += 1
        logger.info("")

    logger.info("Results: %d passed, %d failed", passed, failed)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
