"""Supabase JWT verification for FastAPI dependency injection."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from apps.api.core.config import Settings, get_settings

logger: logging.Logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Supabase JWTs are signed with the ANON / service-role secret which is
# derived from the project's JWT secret.  The audience is always
# "authenticated" for logged-in users.
_ALGORITHM: str = "HS256"
_AUDIENCE: str = "authenticated"

_DEBUG_USER_ID: str = "00000000-0000-0000-0000-000000000000"


def _decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a Supabase-issued JWT.

    Args:
        token: The raw Bearer token string.
        settings: Application settings (carries the JWT secret).

    Returns:
        The full decoded payload as a dict.

    Raises:
        HTTPException 401: If the token is expired, malformed, or the
            signature is invalid.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SUPABASE_SERVICE_ROLE_KEY,
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
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    """FastAPI dependency that extracts the authenticated ``user_id``.

    When ``DEBUG=True`` in the environment and no Bearer token is provided,
    JWT verification is skipped and a deterministic dummy user-id is returned.
    This is intended **only** for local smoke-testing.

    Returns:
        The ``sub`` claim from the JWT, or a dummy UUID in debug mode.

    Raises:
        HTTPException 401: If the token is missing / invalid (non-debug).
    """
    # --- Debug bypass ------------------------------------------------
    if settings.DEBUG:
        if credentials is None:
            logger.warning(
                "DEBUG mode: skipping JWT verification, using dummy user_id=%s",
                _DEBUG_USER_ID,
            )
            return _DEBUG_USER_ID
        # If a token *was* supplied in debug mode, still validate it so
        # the developer can test real auth alongside the bypass.

    # --- Normal path -------------------------------------------------
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload: dict[str, Any] = _decode_token(credentials.credentials, settings)

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
