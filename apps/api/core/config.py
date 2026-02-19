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

    # --- JWT (Supabase project JWT secret for HS256 verification) ---
    JWT_SECRET: str = ""

    # --- Cloudflare R2 (optional in DEBUG mode) ---
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_ENDPOINT_URL: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_DOMAIN: str = ""

    # --- Redis (optional in DEBUG mode) ---
    REDIS_URL: str = ""

    # --- CORS ---
    CORS_ORIGINS: str = ""

    # --- Rate limiting ---
    RATE_LIMIT_UPLOAD: str = "10/minute"
    RATE_LIMIT_READ: str = "60/minute"

    # --- Debug ---
    DEBUG: bool = False

    def validate(self) -> None:
        """Validate that required env vars are set in non-DEBUG mode."""
        if self.DEBUG:
            return
        required = {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
            "JWT_SECRET": self.JWT_SECRET,
            "R2_ACCESS_KEY_ID": self.R2_ACCESS_KEY_ID,
            "R2_SECRET_ACCESS_KEY": self.R2_SECRET_ACCESS_KEY,
            "R2_ENDPOINT_URL": self.R2_ENDPOINT_URL,
            "R2_BUCKET_NAME": self.R2_BUCKET_NAME,
            "REDIS_URL": self.REDIS_URL,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variables (DEBUG=False): {', '.join(missing)}"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()  # type: ignore[call-arg]
