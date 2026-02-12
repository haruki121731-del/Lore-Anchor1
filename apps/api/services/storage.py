"""Cloudflare R2 storage operations via the S3-compatible boto3 API."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

import boto3

from apps.api.core.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


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
        """Generate a pre-signed GET URL for the given object *key*.

        Args:
            key: S3 object key.
            expires_in: URL lifetime in seconds (default 1 hour).

        Returns:
            A pre-signed URL string.
        """
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


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Return a cached singleton of :class:`StorageService`."""
    return StorageService()
