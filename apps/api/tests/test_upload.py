"""Tests for POST /api/v1/images/upload validation."""


def test_upload_no_file_returns_422(client):
    """Sending no file should return 422 Unprocessable Entity."""
    response = client.post("/api/v1/images/upload")
    assert response.status_code == 422


def test_upload_unsupported_type_returns_415(client):
    """Uploading a non-image file should return 415."""
    response = client.post(
        "/api/v1/images/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_oversized_file_returns_413(client):
    """Uploading a file exceeding 20 MB should return 413."""
    # 20 MB + 1 byte
    oversized = b"\x00" * (20 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/images/upload",
        files={"file": ("big.png", oversized, "image/png")},
    )
    assert response.status_code == 413
