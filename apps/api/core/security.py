"""Supabase JWT verification for FastAPI dependency injection."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from apps.api.core.config import Settings, get_settings

_bearer_scheme = HTTPBearer()

# Supabase JWTs are signed with the ANON / service-role secret which is
# derived from the project's JWT secret.  The audience is always
# "authenticated" for logged-in users.
_ALGORITHM: str = "HS256"
_AUDIENCE: str = "authenticated"


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
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    """FastAPI dependency that extracts the authenticated ``user_id``.

    Usage::

        @router.post("/upload")
        async def upload(user_id: str = Depends(get_current_user_id)):
            ...

    Returns:
        The ``sub`` claim from the JWT — i.e. the Supabase Auth user UUID.

    Raises:
        HTTPException 401: If the token is missing, invalid, or does not
            contain a ``sub`` claim.
    """
    payload: dict[str, Any] = _decode_token(credentials.credentials, settings)

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
