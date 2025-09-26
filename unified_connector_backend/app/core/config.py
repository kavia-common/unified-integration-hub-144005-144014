from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List, Optional

class Settings(BaseSettings):
    # Server
    API_PREFIX: str = "/"
    CORS_ALLOW_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Mongo
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "unified_connector"

    # Security/crypto
    SECRET_KEY: str = "CHANGE_ME"
    ENCRYPTION_KEY: str = "CHANGE_ME_32BYTES_MIN"

    # Atlassian (Jira/Confluence) OAuth
    JIRA_CLIENT_ID: Optional[str] = None
    JIRA_CLIENT_SECRET: Optional[str] = None
    JIRA_REDIRECT_URI: Optional[AnyHttpUrl] = None

    CONFLUENCE_CLIENT_ID: Optional[str] = None
    CONFLUENCE_CLIENT_SECRET: Optional[str] = None
    CONFLUENCE_REDIRECT_URI: Optional[AnyHttpUrl] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
