# Backend-local Makefile for convenience

PYTHON ?= python3
PIP ?= pip

.PHONY: setup
setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && $(PIP) install -r requirements.txt

.PHONY: start
start:
	. .venv/bin/activate && $(PYTHON) -m app.server

.PHONY: start-uvicorn
start-uvicorn:
	. .venv/bin/activate && uvicorn app.asgi:app --host 0.0.0.0 --port $${PORT:-3002}

