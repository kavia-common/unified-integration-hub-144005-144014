.PHONY: install run run-dev openapi

install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && uvicorn unified_connector_backend/app.server:app --host 0.0.0.0 --port $${PORT:-3001}

run-dev:
	. .venv/bin/activate && python -m unified_connector_backend.run

openapi:
	@echo "To export OpenAPI, ensure the server is running then:"
	@echo "curl http://localhost:$${PORT:-3001}/openapi.json > unified_connector_backend/interfaces/openapi.json"
