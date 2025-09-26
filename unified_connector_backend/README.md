# Unified Connector Backend

FastAPI backend exposing normalized connector APIs for Jira and Confluence with Atlassian OAuth, MongoDB credential storage, and multi-tenant scoping.

## Run locally

1. Create `.env` from `.env.example` with your Atlassian OAuth app credentials and Mongo URL.
2. Install deps:

   pip install -r requirements.txt

3. Start dev server:

   ./run.sh

Open http://localhost:8000/api/docs

## Environment

- MONGODB_URL, MONGODB_DB
- ALLOWED_ORIGINS
- ENC_KEY
- JIRA_CLIENT_ID, JIRA_CLIENT_SECRET, JIRA_REDIRECTION_URI
- CONFLUENCE_CLIENT_ID, CONFLUENCE_CLIENT_SECRET, CONFLUENCE_REDIRECTION_URI

## Notes

- Encryption helper is for demo only. Replace with a proper KMS/HSM solution.
- State storage uses in-memory dict; replace with Redis or signed cookies in production.
