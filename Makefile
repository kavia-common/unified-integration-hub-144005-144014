# Convenience Makefile for CI and local development from repo root.

PYTHON ?= python3
PIP ?= pip

# Create venv if not exists and install backend deps using backend requirements
.PHONY: setup-backend
setup-backend:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && $(PIP) install -r unified_connector_backend/requirements.txt

# Start backend using module runner (loads .env, logs host/port)
.PHONY: start-backend
start-backend:
	cd unified_connector_backend && . ../.venv/bin/activate && $(PYTHON) -m app.server

# A default 'ci' target some pipelines call
.PHONY: ci
ci: setup-backend
	@echo "Backend dependencies installed."

