"""SaladCloud GPU container group management — scale-to-zero.

Starts the GPU container group when Pro user tasks arrive, and workers
self-stop after 15 minutes of idle time. The API only handles the
start-up trigger; shutdown is handled by the worker itself.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from apps.api.core.config import get_settings

logger: logging.Logger = logging.getLogger(__name__)

_SALAD_API_BASE = "https://api.salad.com/api/public"


class SaladService:
    """Thin async client for the SaladCloud Container Groups API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: str = settings.SALAD_API_KEY
        self._org_name: str = settings.SALAD_ORG_NAME
        self._project_name: str = settings.SALAD_PROJECT_NAME
        self._group_name: str = settings.SALAD_CONTAINER_GROUP_NAME
        self._enabled: bool = bool(self._api_key and self._org_name)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _url(self, action: str = "") -> str:
        base = (
            f"{_SALAD_API_BASE}/organizations/{self._org_name}"
            f"/projects/{self._project_name}"
            f"/containers/{self._group_name}"
        )
        if action:
            return f"{base}/{action}"
        return base

    def _headers(self) -> dict[str, str]:
        return {
            "Salad-Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    async def get_status(self) -> str:
        """Return the container group status (e.g. 'running', 'stopped')."""
        if not self._enabled:
            return "disabled"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self._url(), headers=self._headers())
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data.get("current_state", {}).get("status", "unknown")

    async def start(self) -> bool:
        """Start the container group. Returns True if started successfully."""
        if not self._enabled:
            logger.info("SaladCloud not configured, skipping start")
            return False

        try:
            current = await self.get_status()
            if current == "running":
                logger.info("SaladCloud container group already running")
                return True

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._url("start"),
                    headers=self._headers(),
                )
                resp.raise_for_status()
                logger.info("SaladCloud container group start requested")
                return True
        except Exception:
            logger.exception("Failed to start SaladCloud container group")
            return False

    async def stop(self) -> bool:
        """Stop the container group. Returns True if stopped successfully."""
        if not self._enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._url("stop"),
                    headers=self._headers(),
                )
                resp.raise_for_status()
                logger.info("SaladCloud container group stop requested")
                return True
        except Exception:
            logger.exception("Failed to stop SaladCloud container group")
            return False
