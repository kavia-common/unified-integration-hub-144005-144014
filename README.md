# Unified Integration Hub

This workspace contains:
- unified_connector_backend (FastAPI + MongoDB)
- unified_connector_frontend (Next.js + Tailwind)

Quickstart:
1) Backend
   - cd unified_connector_backend
   - cp .env.example .env and fill values
   - pip install -r requirements.txt
   - uvicorn unified_connector_backend.app.main:app --reload

2) Frontend
   - cd ../unified_connector_frontend
   - cp .env.example .env
   - npm i
   - npm run dev

Docs:
- See PDFs in attachments/ for architecture, flow, and development steps.