"""Integration tests for the API upload → read flow.

These tests run with DEBUG=true (set in conftest.py) so all external
services (R2, Supabase, Redis) are replaced by in-memory stubs.
No Docker or network access required.

Because ``get_database_service`` creates a new DebugDatabaseService on
every call (no cache), we override the dependency so that all requests
within a test share the same in-memory store.
"""

import io

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.database import DebugDatabaseService, get_database_service


# ---------------------------------------------------------------------------
# Helper: create a minimal valid 1×1 PNG in memory
# ---------------------------------------------------------------------------
def _make_1x1_png() -> bytes:
    """Return the bytes of a valid 1×1 white PNG image."""
    import struct
    import zlib

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1×1 RGB
    raw_row = b"\x00" + b"\xff\xff\xff"  # filter=None + white pixel
    idat_data = zlib.compress(raw_row)
    return signature + _chunk(b"IHDR", ihdr_data) + _chunk(b"IDAT", idat_data) + _chunk(b"IEND", b"")


_PNG_BYTES = _make_1x1_png()


@pytest.fixture()
def integration_client():
    """TestClient with a shared DebugDatabaseService across all requests."""
    shared_db = DebugDatabaseService()
    app.dependency_overrides[get_database_service] = lambda: shared_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_database_service, None)


# ---------------------------------------------------------------------------
# a. POST /upload → 201 with image_id
# ---------------------------------------------------------------------------
def test_upload_image_returns_201_with_image_id(integration_client):
    """Uploading a valid PNG should return 201 with an image_id."""
    response = integration_client.post(
        "/api/v1/images/upload",
        files={"file": ("test.png", io.BytesIO(_PNG_BYTES), "image/png")},
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert "image_id" in data, f"Response missing 'image_id': {data}"
    assert data["status"] == "pending"


# ---------------------------------------------------------------------------
# b. GET /images/{image_id} → status is pending
# ---------------------------------------------------------------------------
def test_get_image_after_upload_returns_pending(integration_client):
    """After upload, fetching the image by ID should show status=pending."""
    # Upload first
    upload_resp = integration_client.post(
        "/api/v1/images/upload",
        files={"file": ("test.png", io.BytesIO(_PNG_BYTES), "image/png")},
    )
    assert upload_resp.status_code == 201
    image_id = upload_resp.json()["image_id"]

    # Fetch by ID
    get_resp = integration_client.get(f"/api/v1/images/{image_id}")
    assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
    data = get_resp.json()
    assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"
    assert data["id"] == image_id


# ---------------------------------------------------------------------------
# c. GET /images/ → list contains the uploaded image_id
# ---------------------------------------------------------------------------
def test_list_images_contains_uploaded_image(integration_client):
    """After upload, the image list should contain the uploaded image."""
    # Upload first
    upload_resp = integration_client.post(
        "/api/v1/images/upload",
        files={"file": ("test.png", io.BytesIO(_PNG_BYTES), "image/png")},
    )
    assert upload_resp.status_code == 201
    image_id = upload_resp.json()["image_id"]

    # List all images
    list_resp = integration_client.get("/api/v1/images/")
    assert list_resp.status_code == 200, f"Expected 200, got {list_resp.status_code}: {list_resp.text}"
    data = list_resp.json()
    image_ids = [img["id"] for img in data["images"]]
    assert image_id in image_ids, f"image_id {image_id} not found in image list: {image_ids}"
