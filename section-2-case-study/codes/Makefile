PYTHON_BOOTSTRAP ?= $(shell command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || command -v python3.10 2>/dev/null || command -v python3)
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
BACKEND_HOST ?= 0.0.0.0
BACKEND_PORT ?= 8000
FRONTEND_HOST ?= 0.0.0.0
FRONTEND_PORT ?= 5173

PYTHON_DEPS_STAMP := $(VENV)/.deps-installed

export PYTHONPATH := $(CURDIR)

.PHONY: help install backend frontend dev prod test docker-build docker-up docker-down clean

help:
	@printf "Targets:\n"
	@printf "  make install      Install Python and frontend dependencies\n"
	@printf "  make backend      Run FastAPI on port $(BACKEND_PORT)\n"
	@printf "  make frontend     Run Vite on port $(FRONTEND_PORT)\n"
	@printf "  make dev          Run backend and frontend together\n"
	@printf "  make prod         Run backend and frontend with backend caching enabled\n"
	@printf "  make test         Run pytest\n"
	@printf "  make docker-up    Build and run both services with Docker Compose\n"
	@printf "  make docker-down  Stop Docker Compose services\n"

$(PYTHON):
	$(PYTHON_BOOTSTRAP) -m venv $(VENV)

$(PYTHON_DEPS_STAMP): requirements.txt | $(PYTHON)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@touch $(PYTHON_DEPS_STAMP)

install: $(PYTHON_DEPS_STAMP)
	npm --prefix frontend install

backend: $(PYTHON_DEPS_STAMP)
	$(PYTHON) main.py --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

frontend:
	npm --prefix frontend run dev -- --host $(FRONTEND_HOST) --port $(FRONTEND_PORT)

dev: $(PYTHON_DEPS_STAMP)
	@set -e; \
	ANALYSIS_CACHE_ENABLED=false $(PYTHON) main.py --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload & \
	backend_pid=$$!; \
	npm --prefix frontend run dev -- --host $(FRONTEND_HOST) --port $(FRONTEND_PORT) & \
	frontend_pid=$$!; \
	trap 'kill $$backend_pid $$frontend_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$backend_pid $$frontend_pid

prod: $(PYTHON_DEPS_STAMP)
	@set -e; \
	npm --prefix frontend run build; \
	ANALYSIS_CACHE_ENABLED=true $(PYTHON) main.py --host $(BACKEND_HOST) --port $(BACKEND_PORT) & \
	backend_pid=$$!; \
	npm --prefix frontend run preview -- --host $(FRONTEND_HOST) --port $(FRONTEND_PORT) & \
	frontend_pid=$$!; \
	trap 'kill $$backend_pid $$frontend_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$backend_pid $$frontend_pid

test: $(PYTHON_DEPS_STAMP)
	$(PYTHON) -m pytest

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf frontend/dist .pytest_cache data/processed/cache $(VENV)
