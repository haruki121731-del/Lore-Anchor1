"""Application configuration loaded from environment variables via Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the lore-anchor Backend API.

    All values are loaded from a `.env` file (or OS environment variables).
    Variable names match those defined in the MDD Section 6.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Supabase (optional in DEBUG mode) ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # --- Cloudflare R2 (optional in DEBUG mode) ---
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_ENDPOINT_URL: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_DOMAIN: str = ""

    # --- Redis (optional in DEBUG mode) ---
    REDIS_URL: str = ""

    # --- Debug ---
    DEBUG: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()  # type: ignore[call-arg]
