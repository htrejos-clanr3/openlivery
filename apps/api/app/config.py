from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


APP_DIR = Path(__file__).resolve().parents[1]   # apps/api
REPO_ROOT = Path(__file__).resolve().parents[3]  # monorepo root (used for a shared local .env)


class Settings(BaseSettings):
    app_name: str = "OpenLivery API"
    database_url: str = "postgresql+psycopg://openlivery:openlivery@localhost:5432/openlivery"
    secret_key: str = "dev-local-change-this-key-please"
    encryption_key: str = "dev-local-change-this-key-too"
    frontend_url: str = "http://localhost:3000"
    access_token_minutes: int = 60 * 24 * 7
    # Session cookie flags. Defaults suit local HTTP; set cookie_secure=true (and
    # cookie_samesite=none when the frontend and API are on different sites)
    # behind HTTPS in production.
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    # Rate limiting on public/unauthenticated endpoints (per client IP). Disable
    # only for tests or when a proxy in front already enforces limits.
    rate_limit_enabled: bool = True
    # SSRF guard for agent HTTP tools: URLs resolving to private/loopback
    # addresses are rejected. Enable only on self-hosted deployments that need
    # tools to reach internal services.
    tools_allow_private_urls: bool = False
    storage_dir: Path = APP_DIR / "storage"
    backend_url: str = "http://localhost:8000"
    whatsapp_bridge_url: str = "http://localhost:3101"
    whatsapp_bridge_token: str = "dev-local-change-this-bridge-token"
    # Meta Graph API root used by the WhatsApp Cloud API channel; override to
    # point at a mock server in tests. Version is the last path segment (v23.0).
    meta_graph_base_url: str = "https://graph.facebook.com/v23.0"
    # Platform Meta App for managed Embedded Signup (not per-client BYO).
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_whatsapp_config_id: str = ""
    # When true, signup/complete can finish without real Meta credentials.
    meta_mock_mode: bool = False
    meta_oauth_redirect_path: str = "/api/whatsapp-cloud/oauth/callback"
    # Instagram Content Publishing (reuse META_APP_* for Facebook Login OAuth).
    instagram_publishing_mock_mode: bool = False
    instagram_oauth_redirect_path: str = "/api/instagram/oauth/callback"
    instagram_container_poll_max_attempts: int = 30
    instagram_container_poll_delay_seconds: float = 2.0
    instagram_scheduler_interval_seconds: float = 20.0
    instagram_scheduler_enabled: bool = True
    instagram_max_image_bytes: int = 8 * 1024 * 1024
    instagram_max_video_bytes: int = 100 * 1024 * 1024
    instagram_media_url_ttl_seconds: int = 60 * 60
    # Meta Developer Tools / Social Technologies MCP (diagnostics only — not on message path).
    meta_devtools_mcp_enabled: bool = False
    meta_devtools_mcp_url: str = "https://mcp.facebook.com/devtools"
    meta_devtools_mcp_timeout_seconds: float = 25.0
    meta_devtools_mcp_access_token: str = ""
    meta_devtools_mcp_mock_mode: bool = False
    meta_devtools_mcp_manage_enabled: bool = False
    meta_api_warning_threshold: int = 70
    meta_api_critical_threshold: int = 90
    meta_mcp_cache_ttl_seconds: int = 180
    meta_mcp_slow_cache_ttl_seconds: int = 1800
    # Google Identity (password OR Google). Leave empty to disable Google buttons.
    google_oauth_client_id: str = ""
    # When true, forgot-password responses include the raw token (local/tests only).
    auth_expose_reset_token: bool = False

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", APP_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
