def get_openapi_config():
    return {
        "title": "Unified Connector Backend",
        "description": "FastAPI backend for Jira/Confluence connectors with OAuth, normalized APIs, and multi-tenant storage.",
        "version": "0.1.0",
        "openapi_tags": [
            {"name": "Connectors", "description": "Connector discovery, OAuth, and operations"},
            {"name": "System", "description": "System endpoints"},
        ],
        "docs_url": "/api/docs",
        "redoc_url": "/api/redoc",
        "openapi_url": "/api/openapi.json",
    }
