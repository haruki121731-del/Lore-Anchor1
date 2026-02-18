"""Supabase JWT verification for FastAPI dependency injection."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from apps.api.core.config import Settings, get_settings

logger: logging.Logger = logging.getLogger(__name__)

# Supabase JWTs are signed with the ANON / service-role secret which is
# derived from the project's JWT secret.  The audience is always
# "authenticated" for logged-in users.
_ALGORITHM: str = "HS256"
_AUDIENCE: str = "authenticated"

_DEBUG_USER_ID: str = "21888f74-e977-4293-8968-52c7afaf54c9"


def _extract_bearer_token(request: Request) -> str | None:
    """Extract the Bearer token from the Authorization header.

    Returns:
        The raw token string, or ``None`` if the header is absent or
        does not use the Bearer scheme.
    """
    auth: str | None = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def _decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a Supabase-issued JWT.

    Raises:
        HTTPException 401: If the token is expired, malformed, or the
            signature is invalid.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload


async def get_current_user_id(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> str:
    """FastAPI dependency that extracts the authenticated ``user_id``.

    When ``DEBUG=True`` and no Bearer token is provided, JWT verification
    is skipped and a deterministic dummy user-id is returned.  This is
    intended **only** for local smoke-testing.

    Returns:
        The ``sub`` claim from the JWT, or a dummy UUID in debug mode.

    Raises:
        HTTPException 401: If the token is missing / invalid (non-debug).
    """
    token: str | None = _extract_bearer_token(request)

    # --- Debug bypass ------------------------------------------------
    if settings.DEBUG and token is None:
        logger.warning(
            "DEBUG mode: skipping JWT verification, using dummy user_id=%s",
            _DEBUG_USER_ID,
        )
        return _DEBUG_USER_ID

    # --- Normal path -------------------------------------------------
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload: dict[str, Any] = _decode_token(token, settings)

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
