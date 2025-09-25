# Unified Connector Backend

FastAPI backend providing a unified interface to manage integrations (Jira, Confluence, ...). This initial scaffold includes:
- Multi-tenant Mongo-backed storage utilities
- Connector base class and registry
- Jira and Confluence connector stubs with OAuth endpoints
- OpenAPI documentation and CORS configuration

## Running locally

- Ensure Python dependencies are installed: `pip install -r requirements.txt`
- Set required environment variables (see `.env.example`)
- Start the API: `uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001`

## Environment Variables

- MONGODB_URL: Mongo connection string (provided by database container)
- MONGODB_DB: Mongo database name (default: unified_connector)
- ENCRYPTION_KEY: Symmetric key to encrypt tokens (request from operator)
- API_TITLE, API_DESCRIPTION, API_VERSION: Optional API metadata
- CORS_ALLOW_ORIGINS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS: Comma-separated lists

OAuth (stubs)
- JIRA_CLIENT_ID, JIRA_CLIENT_SECRET, JIRA_REDIRECT_URI
- CONFLUENCE_CLIENT_ID, CONFLUENCE_CLIENT_SECRET, CONFLUENCE_REDIRECT_URI

## Tenancy

Use header `X-Tenant-ID: <tenantId>` to scope storage. Defaults to `public` if omitted.

## Endpoints (initial)

- GET /connectors — List connectors
- GET /connectors/{id}/oauth/login — Returns authorization URL (stub)
- GET /connectors/{id}/oauth/callback — Completes OAuth (stub)
- GET /connectors/{id}/search?q=... — Search (stub)
- POST /connectors/{id}/connect — Connect (stub)
- POST /connectors/{id}/disconnect — Disconnect (stub)

Pass `X-Tenant-ID` with each request.

## Notes

- Token storage is stubbed and uses placeholder encrypted values. Replace with real crypto (e.g., Fernet/AES) using ENCRYPTION_KEY.
- Add connector-specific endpoints within their sub-routers (e.g., `/connectors/jira/...`).
