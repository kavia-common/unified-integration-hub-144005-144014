from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class SecuritySettings(BaseModel):
    """Security-related settings for token encryption and signing."""

    ENCRYPTION_KEY: str = Field(..., description="Symmetric key used for encrypting connector tokens. Request from operator.")


class MongoSettings(BaseModel):
    """MongoDB connection settings."""

    MONGODB_URL: str = Field(..., description="Mongo connection string (e.g., mongodb+srv://user:pass@cluster/url)")
    MONGODB_DB: str = Field(default="unified_connector", description="Database name to use")


class OAuthSettings(BaseModel):
    """OAuth client ids and secrets for supported connectors.

    For local development these can be dummy values until real OAuth is set up.
    """

    # JIRA (Atlassian)
    JIRA_CLIENT_ID: Optional[str] = Field(default=None, description="OAuth client ID for Jira Cloud (Atlassian)")
    JIRA_CLIENT_SECRET: Optional[str] = Field(default=None, description="OAuth client secret for Jira Cloud (Atlassian)")
    JIRA_REDIRECT_URI: Optional[str] = Field(default=None, description="OAuth redirect URL for Jira auth callback")

    # Confluence (Atlassian)
    CONFLUENCE_CLIENT_ID: Optional[str] = Field(default=None, description="OAuth client ID for Confluence Cloud (Atlassian)")
    CONFLUENCE_CLIENT_SECRET: Optional[str] = Field(default=None, description="OAuth client secret for Confluence Cloud (Atlassian)")
    CONFLUENCE_REDIRECT_URI: Optional[str] = Field(default=None, description="OAuth redirect URL for Confluence auth callback")


class APISettings(BaseModel):
    """FastAPI application settings."""

    API_TITLE: str = Field(default="Unified Connector Backend", description="API title for OpenAPI")
    API_DESCRIPTION: str = Field(
        default="Unified connector platform API for managing integrations (Jira, Confluence, ...).",
        description="API description",
    )
    API_VERSION: str = Field(default="0.1.0", description="API version")
    CORS_ALLOW_ORIGINS: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed origins")
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed methods")
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed headers")


class TenantSettings(BaseModel):
    """Tenant and environment settings."""

    DEFAULT_TENANT_ID: str = Field(default="public", description="Default tenant id if header missing")
    TENANT_HEADER_NAME: str = Field(default="X-Tenant-ID", description="Header used to pass tenant id")
    ENV: str = Field(default=os.getenv("ENV", "development"), description="Environment name")


class Settings(BaseModel):
    """Application configuration bundle."""

    security: SecuritySettings
    mongo: MongoSettings
    oauth: OAuthSettings
    api: APISettings
    tenant: TenantSettings

    @staticmethod
    def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(name, default)

    # PUBLIC_INTERFACE
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        security = SecuritySettings(ENCRYPTION_KEY=cls._get_env("ENCRYPTION_KEY", "") or "")
        mongo = MongoSettings(
            MONGODB_URL=cls._get_env("MONGODB_URL", "") or "",
            MONGODB_DB=cls._get_env("MONGODB_DB", "unified_connector"),
        )
        oauth = OAuthSettings(
            JIRA_CLIENT_ID=cls._get_env("JIRA_CLIENT_ID"),
            JIRA_CLIENT_SECRET=cls._get_env("JIRA_CLIENT_SECRET"),
            JIRA_REDIRECT_URI=cls._get_env("JIRA_REDIRECT_URI"),
            CONFLUENCE_CLIENT_ID=cls._get_env("CONFLUENCE_CLIENT_ID"),
            CONFLUENCE_CLIENT_SECRET=cls._get_env("CONFLUENCE_CLIENT_SECRET"),
            CONFLUENCE_REDIRECT_URI=cls._get_env("CONFLUENCE_REDIRECT_URI"),
        )
        api = APISettings(
            API_TITLE=cls._get_env("API_TITLE", "Unified Connector Backend"),
            API_DESCRIPTION=cls._get_env(
                "API_DESCRIPTION",
                "Unified connector platform API for managing integrations (Jira, Confluence, ...).",
            ),
            API_VERSION=cls._get_env("API_VERSION", "0.1.0"),
            CORS_ALLOW_ORIGINS=(cls._get_env("CORS_ALLOW_ORIGINS", "*") or "*").split(","),
            CORS_ALLOW_METHODS=(cls._get_env("CORS_ALLOW_METHODS", "*") or "*").split(","),
            CORS_ALLOW_HEADERS=(cls._get_env("CORS_ALLOW_HEADERS", "*") or "*").split(","),
        )
        tenant = TenantSettings(
            DEFAULT_TENANT_ID=cls._get_env("DEFAULT_TENANT_ID", "public"),
            TENANT_HEADER_NAME=cls._get_env("TENANT_HEADER_NAME", "X-Tenant-ID"),
            ENV=cls._get_env("ENV", "development"),
        )
        return cls(security=security, mongo=mongo, oauth=oauth, api=api, tenant=tenant)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton access to application settings loaded from environment."""
    return Settings.from_env()
