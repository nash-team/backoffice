# Backoffice Makefile
# Essential commands for local development workflow

.PHONY: help install run clean test test-unit test-e2e db-migrate db-status setup dev \
        lint format typecheck deps deadcode precommit

.DEFAULT_GOAL := help

# -------- Variables --------
PY ?= python
PIP ?= pip
APP ?= backoffice.main:app
HOST ?= 127.0.0.1
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
run: ## Start FastAPI development server
	@echo "Starting dev server on http://$(HOST):$(PORT)"
	uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

dev: ## Migrate then run
	@$(MAKE) db-migrate
	@$(MAKE) run

# -------- Tests --------
test: ## Run all tests (unit + E2E)
	$(PY) -m pytest tests/ -v

test-unit: ## Run unit tests only
	$(PY) -m pytest tests/ -v -m "not e2e" --ignore=tests/e2e/

test-e2e: ## Run E2E tests with Playwright (chromium)
	$(PY) -m pytest tests/e2e

# -------- DB --------
db-migrate: ## Run database migrations
	alembic upgrade head

db-status: ## Show current migration status & history
	alembic current && alembic history

# -------- Quality --------
lint: ## Ruff lint
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
