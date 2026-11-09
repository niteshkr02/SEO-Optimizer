"""Runtime application settings using Pydantic Settings."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # API & Runtime
    PROJECT_NAME: str = "SEO Optimizer API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(
        default="development", description="development | test | production"
    )
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ]
    )

    # Security & SSRF Guard
    ENFORCE_SSRF_PROTECTION: bool = True
    ALLOWED_EGRESS_PORTS: list[int] = Field(default_factory=lambda: [80, 443])
    ALLOWED_SCHEMES: list[str] = Field(default_factory=lambda: ["http", "https"])
    DNS_RESOLVER_TIMEOUT_SECONDS: float = 3.0
    CONNECT_TIMEOUT_SECONDS: float = 3.0
    READ_TIMEOUT_SECONDS: float = 5.0
    SCAN_TIMEOUT_SECONDS: float = 10.0
    MAX_REDIRECTS: int = 5
    MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    MAX_DOM_NODES: int = 25000

    # User Agent
    CRAWLER_USER_AGENT: str = (
        "Mozilla/5.0 (compatible; SEOOptimizerBot/1.0; +https://seo-optimizer.com/bot)"
    )

    # Scoring & Rules Versioning
    RULESET_VERSION: str = "1.0.0"
    SCORING_MODEL_VERSION: str = "1.0.0"

    # Category Weights for Overall Health Score (E3)
    WEIGHT_INDEXABILITY: float = 0.35
    WEIGHT_TECHNICAL: float = 0.30
    WEIGHT_PERFORMANCE: float = 0.20
    WEIGHT_ON_PAGE: float = 0.15

    # Lead Capture & Consultation Management
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Administrative login username",
    )
    ADMIN_PASSWORD: str = Field(
        default="dev-admin-password-change-in-production",
        description="Administrative login password",
    )
    ADMIN_API_KEY: str = Field(
        default="dev-admin-secret-key-change-in-production",
        description="API key required for server-to-server admin lead management endpoints",
    )
    ADMIN_SESSION_SECRET: str = Field(
        default="dev-session-secret-change-in-production-min-32-chars",
        description="Secret key used for HMAC session cookie signing",
    )
    ADMIN_SESSION_TTL_SECONDS: int = Field(
        default=86400,
        description="Admin session lifetime in seconds (default 24 hours)",
    )
    CSRF_SECRET: str = Field(
        default="dev-csrf-secret-change-in-production-key",
        description="Secret key used for CSRF token generation and validation",
    )
    COOKIE_SECURE: bool = Field(
        default=False,
        description="Whether cookies must be sent over HTTPS (enable in production)",
    )
    PERSISTENCE_BACKEND: str = Field(
        default="sqlite",
        description="Persistence backend: in_memory | sqlite | supabase",
    )
    SQLITE_DB_PATH: str = Field(
        default="seo_optimizer.db",
        description="File path for SQLite persistent storage",
    )
    SUPABASE_URL: str | None = Field(
        default=None,
        description="Supabase PostgREST endpoint (server-only)",
    )
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(
        default=None,
        description="Supabase service role secret key (server-only, never expose to clients)",
    )
    SUPABASE_SECRET_KEY: str | None = Field(
        default=None,
        description="Supabase secret key (new sb_secret_... format, server-only)",
    )
    SUPABASE_PUBLISHABLE_KEY: str | None = Field(
        default=None,
        description="Supabase publishable key (sb_publishable_...)",
    )
    SUPABASE_JWKS_URL: str | None = Field(
        default=None,
        description="Supabase JWKS URL for JWT validation",
    )
    DATABASE_URL: str | None = Field(
        default=None,
        description="PostgreSQL database connection URL",
    )
    DIRECT_URL: str | None = Field(
        default=None,
        description="Direct PostgreSQL connection URL",
    )
    LEAD_RATE_LIMIT_MAX_SUBMISSIONS: int = 5
    LEAD_RATE_LIMIT_WINDOW_SECONDS: int = 600
    LEAD_DUPLICATE_WINDOW_SECONDS: int = 60

    @model_validator(mode="after")
    def enforce_production_cookie_security(self) -> "Settings":
        """Enforces HTTPS Secure flag on session cookies in production and resolves Supabase keys."""
        if self.ENVIRONMENT == "production" and not self.COOKIE_SECURE:
            object.__setattr__(self, "COOKIE_SECURE", True)
        if not self.SUPABASE_SERVICE_ROLE_KEY and self.SUPABASE_SECRET_KEY:
            object.__setattr__(self, "SUPABASE_SERVICE_ROLE_KEY", self.SUPABASE_SECRET_KEY)
        return self


settings = Settings()
