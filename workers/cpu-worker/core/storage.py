"""
R2 Storage helpers — Download/Upload via S3-compatible API (boto3).
"""
from __future__ import annotations

import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
_R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
_R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
_R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")

_s3_client = None


def _get_client():  # type: ignore[return]
    """Lazy-init the boto3 S3 client for Cloudflare R2."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    _s3_client = boto3.client(
        "s3",
        endpoint_url=f"https://{_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=_R2_ACCESS_KEY_ID,
        aws_secret_access_key=_R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )
    return _s3_client


def download_from_r2(key: str, dest_path: str) -> None:
    """Download an object from R2 to a local file.

    Args:
        key: The R2 object key.
        dest_path: Local filesystem path to write the file to.
    """
    client = _get_client()
    logger.info("R2 download: %s -> %s", key, dest_path)
    client.download_file(_R2_BUCKET_NAME, key, dest_path)


def upload_to_r2(src_path: str, key: str) -> None:
    """Upload a local file to R2.

    Args:
        src_path: Local filesystem path of the file to upload.
        key: The R2 object key to store under.
    """
    client = _get_client()
    logger.info("R2 upload: %s -> %s", src_path, key)
    client.upload_file(src_path, _R2_BUCKET_NAME, key)
