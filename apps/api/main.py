"""lore-anchor Backend API — FastAPI application entry-point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from apps.api.core.config import get_settings
from apps.api.routers import images
from apps.api.routers.images import tasks_router

logger: logging.Logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Rate limiter
# ------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    settings = get_settings()
    settings.check_required()
    if settings.DEBUG:
        logger.warning(
            "=== DEBUG MODE ACTIVE === "
            "Storage -> local tmp/uploads/, DB -> in-memory, Queue -> log-only"
        )
    yield


# ------------------------------------------------------------------
# FastAPI application
# ------------------------------------------------------------------

app = FastAPI(
    title="lore-anchor API",
    description="Copyright-protection pipeline for creators — Shield, Trust, Speed.",
    version="0.1.0",
    lifespan=_lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ------------------------------------------------------------------
# CORS — allow the Next.js frontend in dev & production
# ------------------------------------------------------------------

_default_origins = [
    "http://localhost:3000",              # Next.js dev server
    "https://lore-anchor1-who4.vercel.app", # Vercel production (current)
    "https://lore-anchor-web.vercel.app", # Vercel production (legacy)
    "https://lore-anchor.com",            # custom domain (future)
]
_extra = get_settings().CORS_ORIGINS
_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()] if _extra else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(images.router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Minimal liveness probe."""
    return {"status": "ok"}
