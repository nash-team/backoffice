# Backoffice Makefile
# Essential commands for local development workflow

.PHONY: help install run clean test test-unit test-e2e db-migrate db-status setup dev \
        lint format typecheck deps deadcode precommit \
        frontend-install frontend-build frontend-dev \
        docker-build docker-up docker-down docker-logs docker-shell docker-test docker-clean

.DEFAULT_GOAL := help

# -------- Variables --------
PY ?= python
PIP ?= pip
APP ?= backoffice.main:app
HOST ?= localhost
PORT ?= 8001
REQ ?= requirements.txt

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": ## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# -------- Setup --------
# -------- Install (pyproject + extras) --------
install: install-dev ## Install dev deps + Playwright (default)

install-dev: ## pip install -e '.[dev]' + playwright chromium
	@echo "Installing dev dependencies (editable + extras [dev])..."
	$(PY) -m pip install --upgrade pip
	$(PIP) install -e '.[dev]'
	@echo "Installing Playwright browsers..."
	$(PY) -m playwright install chromium
	@echo "Done."

install-prod: ## Only runtime deps (no dev tools), + playwright if needed
	@echo "Installing runtime dependencies (editable)..."
	$(PY) -m pip install --upgrade pip
	$(PIP) install -e .
	@echo "Done."
	@echo "If your prod uses Playwright, install browsers via:"
	@echo "  python -m playwright install --with-deps chromium"

setup: ## Full development setup (install + migrate)
	@$(MAKE) install
	@$(MAKE) db-migrate
	@echo "Environment ready."

# -------- App --------
ensure-docker: ## Ensure Docker containers are running
	@if ! docker compose ps --status running 2>/dev/null | grep -q backoffice_postgres; then \
		echo "Starting Docker containers..."; \
		$(MAKE) docker-up; \
		echo "Waiting for PostgreSQL to be ready..."; \
		until docker compose exec -T postgres pg_isready -U backoffice >/dev/null 2>&1; do sleep 1; done; \
		echo "PostgreSQL ready."; \
	else \
		echo "Docker containers already running."; \
	fi

run: ensure-docker ## Start FastAPI development server
	@echo "Starting dev server on http://$(HOST):$(PORT)"
	uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

dev: ensure-docker ## Migrate then run
	@$(MAKE) db-migrate
	@$(MAKE) run

# -------- Tests --------
test: ## Run all working tests (unit only, E2E and integration disabled)
	$(PY) -m pytest src/backoffice/features/ebook/*/tests/unit src/backoffice/features/ebook/shared/tests/unit tests/fixtures -v

test-unit: ## Run unit tests only (from all features)
	$(PY) -m pytest src/backoffice/features/ebook/*/tests/unit src/backoffice/features/ebook/shared/tests/unit -v

test-integration: ## Run integration tests only (REQUIRES DOCKER + testcontainers)
	@echo "⚠️  Integration tests require Docker running + testcontainers setup"
	@echo "   Currently disabled due to migration issues - use test-unit instead"
	@echo "   TODO: Fix test_client fixture import for feature tests"
	# $(PY) -m pytest src/backoffice/features/*/tests/integration -v

test-smoke: ## Run E2E smoke tests only (fast health checks)
	$(PY) -m pytest tests/e2e/test_smoke.py -v \
		--browser chromium \
		--screenshot only-on-failure \
		--video retain-on-failure

test-e2e: ## Run E2E tests with Playwright (chromium)
	$(PY) -m pytest tests/e2e -v \
		--browser chromium \
		--screenshot only-on-failure \
		--video retain-on-failure

# -------- DB --------
db-migrate: ## Run database migrations
	alembic upgrade head

db-status: ## Show current migration status & history
	alembic current && alembic history

# -------- Quality --------
lint: ## Ruff lint (includes tests via pyproject.toml per-file-ignores)
	ruff check .

format: ## Ruff format (in place)
	ruff format .

fix: ## Fix lint + format issues automatically
	ruff check --fix .
	ruff format

typecheck: ## Mypy type checking
	mypy src/

deps: ## Deptry (dependency analysis)
	deptry src

deadcode: ## Vulture (dead code)
	vulture . --min-confidence=80 --exclude=tests,**/__init__.py

precommit: ## Run all pre-commit hooks on all files
	pre-commit run --all-files

# -------- Frontend (React Pipeline SPA) --------
frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-build: ## Build frontend for production
	cd frontend && npm run build

frontend-dev: ## Start frontend dev server (Vite, port 3000)
	cd frontend && npm run dev

frontend-test: ## Run frontend unit tests (Vitest)
	cd frontend && npm test

# -------- Docker --------
# Auto-detect available postgres port (5433 default, increments if taken)
define find_free_port
$(shell port=5433; while lsof -iTCP:$$port -sTCP:LISTEN >/dev/null 2>&1; do port=$$((port + 1)); done; echo $$port)
endef

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services (detached, auto-detect free postgres port)
	@port=$$(port=5433; while lsof -iTCP:$$port -sTCP:LISTEN >/dev/null 2>&1; do port=$$((port + 1)); done; echo $$port); \
	echo "Using PostgreSQL port: $$port"; \
	POSTGRES_PORT=$$port docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Show logs from all services
	docker compose logs -f

docker-shell: ## Open shell in app container
	docker compose exec app bash

docker-test: ## Run tests inside Docker container
	docker compose exec app pytest src/backoffice/features/*/tests/unit -v

docker-clean: ## Stop services and remove volumes
	docker compose down -v

docker-dev: docker-up ## Alias for docker-up (start services)
