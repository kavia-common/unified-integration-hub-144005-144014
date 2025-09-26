# PUBLIC_INTERFACE
"""
Application settings and configuration management.

Loads environment variables and exposes a typed Settings object.
No secrets are logged and defaults are safe for local development.
"""
from __future__ import annotations

import os
from pydantic import BaseModel, Field
from typing import List


class Settings(BaseModel):
    """Service-level configuration loaded from environment variables."""
    app_name: str = Field(default="Unified Connector Backend", description="Human-readable app name")
    environment: str = Field(default=os.getenv("ENVIRONMENT", "development"), description="Environment name")
    host: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("PORT", "3001")))
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "info"))
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
    )
    encryption_key: str | None = Field(default=os.getenv("ENCRYPTION_KEY"), description="Optional base64 or hex key for AES-GCM encryption")
    request_id_header: str = Field(default="X-Request-Id", description="Header name for request id propagation")
    tenant_header: str = Field(default="X-Tenant-Id", description="Header name for tenant id")
    # OAuth related (optional for demo; OAuth flows are mocked)
    jira_client_id: str | None = Field(default=os.getenv("JIRA_CLIENT_ID"))
    jira_client_secret: str | None = Field(default=os.getenv("JIRA_CLIENT_SECRET"))
    jira_redirect_uri: str | None = Field(default=os.getenv("JIRA_REDIRECTION_URI"))
    confluence_client_id: str | None = Field(default=os.getenv("CONFLUENCE_CLIENT_ID"))
    confluence_client_secret: str | None = Field(default=os.getenv("CONFLUENCE_CLIENT_SECRET"))
    confluence_redirect_uri: str | None = Field(default=os.getenv("CONFLUENCE_REDIRECTION_URI"))

    class Config:
        arbitrary_types_allowed = True


_settings: Settings | None = None


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
