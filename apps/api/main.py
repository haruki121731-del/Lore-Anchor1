"""lore-anchor Backend API — FastAPI application entry-point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import images

# ------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler.

    Currently a no-op placeholder; use this to initialise / tear-down
    shared resources (e.g. Redis connection pool) in the future.
    """
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

# ------------------------------------------------------------------
# CORS — allow the Next.js frontend in dev & production
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # Next.js dev server
        "https://lore-anchor.com",   # production (placeholder)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(images.router, prefix="/api/v1")


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Minimal liveness probe."""
    return {"status": "ok"}
