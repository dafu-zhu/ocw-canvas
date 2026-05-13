from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "sqlite:///./ocw_canvas.db"

    # Auth
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_ttl_days: int = 30
    cookie_name: str = "ocw_session"
    cookie_secure: bool = False  # True in production (HTTPS); False for local http
    cookie_samesite: str = "lax"  # "none" in production for cross-site frontend

    # CORS — comma-separated list of allowed frontend origins
    frontend_origins: str = "http://localhost:5173"

    # Owner bootstrap (used by `python -m app.manage create-owner` when env-driven)
    owner_email: str = "owner@example.com"

    # Supabase Storage (used from P2 onward)
    supabase_url: str = ""
    supabase_service_key: str = ""

    # AI (used from P3 onward)
    claude_code_oauth_token: str = ""
    anthropic_api_key: str = ""
    ai_solution_generation_enabled: bool = True

    # Email (used from P4 onward)
    resend_api_key: str = ""

    # Cron (used from P4 onward)
    cron_secret: str = "dev-cron-secret"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
