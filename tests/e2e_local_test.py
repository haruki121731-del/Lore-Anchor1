# Usage: docker-compose up -d && python tests/e2e_local_test.py
#
# End-to-end smoke test that hits the running API via HTTP.
# Requires: pip install requests pillow
"""E2E local test — validates the API running inside docker-compose."""

from __future__ import annotations

import io
import sys

import requests
from PIL import Image

BASE_URL = "http://localhost:8000"


def _create_test_png() -> bytes:
    """Generate a minimal 1×1 PNG image using Pillow."""
    buf = io.BytesIO()
    img = Image.new("RGB", (1, 1), color=(255, 255, 255))
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def main() -> None:
    passed = 0
    total = 4

    # --- Step a: GET /health → 200 ---
    print("[1/4] GET /health ...", end=" ")
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.json() == {"status": "ok"}, f"Unexpected body: {resp.json()}"
    print("OK")
    passed += 1

    # --- Step b: POST /upload with test image ---
    print("[2/4] POST /upload ...", end=" ")
    png_bytes = _create_test_png()
    resp = requests.post(
        f"{BASE_URL}/api/v1/images/upload",
        files={"file": ("test.png", png_bytes, "image/png")},
        timeout=10,
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "image_id" in data, f"Response missing 'image_id': {data}"
    image_id = data["image_id"]
    print(f"OK  image_id={image_id}")
    passed += 1

    # --- Step c: GET /images/{image_id} → status pending ---
    print(f"[3/4] GET /images/{image_id} ...", end=" ")
    resp = requests.get(f"{BASE_URL}/api/v1/images/{image_id}", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"
    print("OK  status=pending")
    passed += 1

    # --- Step d: GET /images/ → list contains image_id ---
    print("[4/4] GET /images/ ...", end=" ")
    resp = requests.get(f"{BASE_URL}/api/v1/images/", timeout=5)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    image_ids = [img["image_id"] for img in data["images"]]
    assert image_id in image_ids, f"image_id {image_id} not found in list: {image_ids}"
    print("OK")
    passed += 1

    print(f"\nAll {passed}/{total} checks passed!")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.ConnectionError:
        print(
            "FAIL: Could not connect to the API. "
            "Make sure docker-compose is running: docker-compose up -d",
            file=sys.stderr,
        )
        sys.exit(1)
