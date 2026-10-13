import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file from working directory, backend directory, or repository root
for candidate_env in [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]:
    if candidate_env.exists():
        load_dotenv(candidate_env, override=False)
        break


class Settings(BaseModel):
    """Core application settings with environment variable fallbacks."""

    PROJECT_NAME: str = "Facility Layout Optimization & Decision Support System"
    VERSION: str = "1.0.0-rc.1"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1"))
    
    # Static Directory for Single-Origin Deployment
    STATIC_DIR: str | None = Field(default_factory=lambda: os.getenv("STATIC_DIR", None))

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: (
            [o.strip() for o in os.getenv("CORS_ORIGINS").split(",") if o.strip()]
            if os.getenv("CORS_ORIGINS")
            else [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        )
    )

    # Confidentiality-First Gemini AI Configuration
    # AI integration is disabled by default to protect proprietary facility data
    AI_ENABLED: bool = Field(default_factory=lambda: os.getenv("AI_ENABLED", "false").lower() in ("true", "1"))
    GEMINI_API_KEY: str | None = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", None))
    GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    GEMINI_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0")))
    AI_CONSENT_SECRET: str = Field(default_factory=lambda: os.getenv("AI_CONSENT_SECRET", "flodss-confidential-consent-secret-v1"))

    # Controlled Research Access & Security Configuration
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "flodss-controlled-research-access-secret-v1-2026"))
    DATABASE_PATH: str = Field(default_factory=lambda: os.getenv("DATABASE_PATH", "data/flodss_research.db"))
    SESSION_EXPIRE_HOURS: int = Field(default_factory=lambda: int(os.getenv("SESSION_EXPIRE_HOURS", "24")))
    INVITATION_EXPIRE_HOURS: int = Field(default_factory=lambda: int(os.getenv("INVITATION_EXPIRE_HOURS", "48")))
    MAX_CONCURRENT_JOBS_PER_USER: int = Field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_JOBS_PER_USER", "2")))
    MAX_TOTAL_CONCURRENT_JOBS: int = Field(default_factory=lambda: int(os.getenv("MAX_TOTAL_CONCURRENT_JOBS", "4")))
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = Field(default_factory=lambda: int(os.getenv("RATE_LIMIT_LOGIN_MAX_ATTEMPTS", "5")))
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = Field(default_factory=lambda: int(os.getenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", "300")))
    AUTH_ENFORCED: bool = Field(default_factory=lambda: os.getenv("AUTH_ENFORCED", "true").lower() in ("true", "1"))
    SESSION_COOKIE_SECURE: bool = Field(default_factory=lambda: os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1"))

    # Network Binding & Trusted Proxy Governance
    HOST: str = Field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    TRUSTED_PROXIES: List[str] = Field(
        default_factory=lambda: (
            [p.strip() for p in os.getenv("TRUSTED_PROXIES").split(",") if p.strip()]
            if os.getenv("TRUSTED_PROXIES")
            else ["127.0.0.1", "::1", "testclient"]
        )
    )

    # Cloudflare Perimeter Architecture: DISABLED | MANAGED_ACCESS | PROTECTED_QUICK_TUNNEL
    CLOUDFLARE_PERIMETER_MODE: str = Field(
        default_factory=lambda: os.getenv("CLOUDFLARE_PERIMETER_MODE", "DISABLED").upper()
    )
    CLOUDFLARE_ACCESS_ENFORCED: bool = Field(default_factory=lambda: os.getenv("CLOUDFLARE_ACCESS_ENFORCED", "false").lower() in ("true", "1"))
    CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS: List[str] = Field(
        default_factory=lambda: (
            [e.strip().lower() for e in os.getenv("CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS", "").split(",") if e.strip()]
            if os.getenv("CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS")
            else []
        )
    )

    # Cloudflare Access Cryptographic Perimeter Configuration (Managed Access Mode)
    CLOUDFLARE_ACCESS_TEAM_NAME: str | None = Field(default_factory=lambda: os.getenv("CLOUDFLARE_ACCESS_TEAM_NAME", None))
    CLOUDFLARE_ACCESS_TEAM_DOMAIN: str | None = Field(default_factory=lambda: os.getenv("CLOUDFLARE_ACCESS_TEAM_DOMAIN", None))
    CLOUDFLARE_ACCESS_EXPECTED_AUD: str | None = Field(default_factory=lambda: os.getenv("CLOUDFLARE_ACCESS_EXPECTED_AUD", None))
    CLOUDFLARE_ACCESS_CERTS_URL: str | None = Field(default_factory=lambda: os.getenv("CLOUDFLARE_ACCESS_CERTS_URL", None))
    CLOUDFLARE_ACCESS_JWKS_CACHE_TTL_SECONDS: int = Field(default_factory=lambda: int(os.getenv("CLOUDFLARE_ACCESS_JWKS_CACHE_TTL_SECONDS", "3600")))

    @property
    def effective_perimeter_mode(self) -> str:
        """Resolve effective perimeter mode, maintaining backward compatibility with CLOUDFLARE_ACCESS_ENFORCED."""
        mode = self.CLOUDFLARE_PERIMETER_MODE.upper()
        if mode in ("MANAGED_ACCESS", "PROTECTED_QUICK_TUNNEL"):
            return mode
        if self.CLOUDFLARE_ACCESS_ENFORCED:
            return "MANAGED_ACCESS"
        return "DISABLED"

    @property
    def is_perimeter_enforced(self) -> bool:
        """Check whether any Cloudflare perimeter (MANAGED_ACCESS or PROTECTED_QUICK_TUNNEL) is active."""
        return self.effective_perimeter_mode != "DISABLED"

    @property
    def cloudflare_team_domain(self) -> str | None:
        """Resolve team domain or name for Cloudflare Access."""
        return self.CLOUDFLARE_ACCESS_TEAM_DOMAIN or self.CLOUDFLARE_ACCESS_TEAM_NAME

    @property
    def cloudflare_expected_issuer(self) -> str | None:
        """Expected JWT issuer URL for Cloudflare Access."""
        domain = self.cloudflare_team_domain
        if not domain:
            return None
        if domain.startswith("http://") or domain.startswith("https://"):
            return domain.rstrip("/")
        return f"https://{domain}.cloudflareaccess.com"

    @property
    def cloudflare_certs_url(self) -> str | None:
        """Public JWKS certificates URL for Cloudflare Access."""
        if self.CLOUDFLARE_ACCESS_CERTS_URL:
            return self.CLOUDFLARE_ACCESS_CERTS_URL
        issuer = self.cloudflare_expected_issuer
        if not issuer:
            return None
        return f"{issuer}/cdn-cgi/access/certs"

    # Initial Admin Seed
    DEFAULT_ADMIN_EMAIL: str = Field(default_factory=lambda: os.getenv("DEFAULT_ADMIN_EMAIL", "admin@flodss.local"))
    DEFAULT_ADMIN_PASSWORD: str = Field(default_factory=lambda: os.getenv("DEFAULT_ADMIN_PASSWORD", "FlodssAdmin2026!"))
    DEFAULT_ADMIN_NAME: str = Field(default_factory=lambda: os.getenv("DEFAULT_ADMIN_NAME", "Lead Research Administrator"))

    @property
    def is_default_admin_password_used(self) -> bool:
        """Check whether a well-known default initial password is still configured."""
        known_defaults = {"FlodssAdmin2026!", "admin123", "password", "admin", "12345678"}
        return self.DEFAULT_ADMIN_PASSWORD in known_defaults


settings = Settings()
