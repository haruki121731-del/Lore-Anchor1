"""Cloudflare R2 storage operations via the S3-compatible boto3 API."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import boto3

from apps.api.core.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger: logging.Logger = logging.getLogger(__name__)


class StorageService:
    """Async wrapper around boto3 S3 client for Cloudflare R2.

    All heavy I/O is offloaded to a thread-pool via ``asyncio.to_thread``
    because boto3 is synchronous.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client: S3Client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        self._bucket: str = settings.R2_RAW_BUCKET

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def upload_file(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str = "image/png",
    ) -> str:
        """Upload *file_bytes* to the raw bucket under *key*.

        Returns:
            The object key that was written (same as *key*).
        """
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return key

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a pre-signed GET URL for the given object *key*."""
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete_file(self, key: str) -> None:
        """Delete the object identified by *key* from the raw bucket."""
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )


class DebugStorageService(StorageService):
    """Local filesystem stub used when ``DEBUG=true``.

    Files are written to ``tmp/uploads/`` instead of Cloudflare R2.
    """

    def __init__(self) -> None:
        self._base_dir: Path = Path("tmp/uploads")
        self._base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("[DEBUG] StorageService using local dir: %s", self._base_dir.resolve())

    async def upload_file(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str = "image/png",
    ) -> str:
        dest: Path = self._base_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_bytes)
        logger.info("[DEBUG] Saved %d bytes -> %s", len(file_bytes), dest)
        return key

    async def generate_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        path: Path = self._base_dir / key
        url = f"file://{path.resolve()}"
        logger.info("[DEBUG] Presigned URL (local): %s", url)
        return url

    async def delete_file(self, key: str) -> None:
        path: Path = self._base_dir / key
        if path.exists():
            path.unlink()
            logger.info("[DEBUG] Deleted local file: %s", path)


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Return a cached singleton of :class:`StorageService`.

    In DEBUG mode, returns a :class:`DebugStorageService` that writes to
    the local filesystem instead of Cloudflare R2.
    """
    if get_settings().DEBUG:
        return DebugStorageService()
    return StorageService()
