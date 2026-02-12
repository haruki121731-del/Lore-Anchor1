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
    )

    # --- Supabase ---
    NEXT_PUBLIC_SUPABASE_URL: str
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # --- Cloudflare R2 (S3-compatible) ---
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str

    # --- Redis ---
    REDIS_URL: str

    # --- Debug ---
    DEBUG: bool = False

    # --- Worker Config ---
    MIST_EPSILON: int = 8
    MIST_STEPS: int = 3

    @property
    def r2_endpoint_url(self) -> str:
        """Construct the S3-compatible endpoint URL for Cloudflare R2."""
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()  # type: ignore[call-arg]
