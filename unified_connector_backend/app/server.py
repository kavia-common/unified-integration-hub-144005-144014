import os
from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env if present (no hardcoding of secrets)
load_dotenv()

if __name__ == "__main__":
    # Respect PORT env if provided by runtime, default to 8000
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    # Start uvicorn pointing to FastAPI app
    uvicorn.run("app.main:app", host=host, port=port, reload=os.getenv("RELOAD", "false").lower() == "true")
```

Explanation: Add a README with instructions for installing dependencies and running the server. This helps CI/preview systems and developers.
````write file="unified-integration-hub-144005-144014/unified_connector_backend/README.md"
# Unified Connector Backend

FastAPI backend for Unified Connector Platform.

## Setup

1. Create and populate a `.env` (if needed). Do not commit secrets.
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
python -m app.server
```

- The server starts at http://localhost:8000
- API docs: http://localhost:8000/docs

## Health

- `GET /health` -> `{ "status": "ok" }`
