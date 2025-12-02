# Deployment

## CI/CD Pipeline

### GitHub Actions CI Workflow

@.github/workflows/ci.yml

**Triggers**: Push to `main`, pull requests to `main` (skips PRs with branch prefix `ebook-generation-`)

**Steps**:

1. Checkout code
2. Free up disk space (remove unused tools/packages)
3. Setup Python 3.11 with pip cache
4. Install dependencies (`pip install -e .[dev]`)
5. Install Playwright browsers (Chromium with system deps)
6. Ruff lint (`ruff check .`)
7. Ruff format check (`ruff format --check .`)
8. Mypy type check (`mypy src/`)
9. Deptry dependency check (`deptry src/`)
10. Vulture dead code check (`vulture src/ .vulture_whitelist.py --min-confidence=80`)
11. Pytest unit tests (`pytest -m "not integration and not e2e and not scenarios" -v`)
12. Pytest E2E tests (`make test-e2e`)

**Test Automation**:

- Unit tests: Run on every push/PR (146 tests, ~1s)
- Integration tests: Disabled (fixture import issue)
- E2E tests: Run on every push/PR (Playwright, Chromium, ~6s)

**Deployment Triggers**:

- Manual deployments: N/A (local development tool)
- Automated deployments: None (backoffice is not deployed)

### Ebook Generation Workflow

@.github/workflows/ebook-generation.yml

**Triggers**:
- Issues opened/reopened with label `ebook-generation`
- Manual workflow dispatch with issue number

**Permissions**: `contents:write`, `issues:write`, `pull-requests:write`

**Job**: `initialize-from-issue`
- Parse issue body to create YAML spec
- Create/update branch `ebook-generation-{issue_number}`
- Commit spec file to `specs/ebook-{issue_number}.yaml`
- Trigger PR creation via repository_dispatch event
- Comment on issue with progress updates

### PR Creation Workflow

@.github/workflows/create-pr.yml

**Triggers**: `repository_dispatch` event type `create-ebook-pr`

**Permissions**: `contents:write`, `pull-requests:write`, `issues:write`

**Job**: `create-pr`
- Create draft PR from ebook generation branch
- Check if PR already exists to avoid duplicates
- Comment on source issue with PR link
- Track generation progress checklist

## Monitoring & Logging

- **Monitoring Tools**: None (local development tool)

- **Logging**:
  - Log aggregation: Console output only
  - Log levels: INFO, WARNING, ERROR (FastAPI/Uvicorn defaults)
  - Log retention: Not applicable (console only)

- **Alert Configuration**: None

## Deployment Process

**Note**: This is a local development tool, not deployed to production servers.

- **Local Development**:
  1. Clone repository
  2. Copy `.env.example` to `.env` and configure
  3. Run `make setup` (install deps + migrate DB)
  4. Run `make dev` (start server at http://127.0.0.1:8001)

- **Database Migration Process**:
  1. Generate migration: `alembic revision --autogenerate -m "Description"`
  2. Review migration in `src/backoffice/migrations/versions/`
  3. Apply migration: `make db-migrate` (runs `alembic upgrade head`)
  4. Verify with `make db-status`

- **Rollback Procedure**:
  1. Identify current migration: `make db-status`
  2. Downgrade to previous: `alembic downgrade -1`
  3. Verify rollback: `make db-status`

# Infrastructure

## Project Structure

```plaintext
backoffice/
├── src/backoffice/
│   ├── features/           # Feature-based modules
│   ├── config/             # App configuration
│   ├── migrations/         # Alembic DB migrations
│   └── main.py             # FastAPI entry point
├── tests/
│   ├── e2e/                # Playwright E2E tests
│   └── fixtures/           # Shared test data
├── ebooks/                 # Generated ebook storage (local files)
├── credentials/            # Google service account JSON
├── specs/                  # Ebook generation specs (YAML)
├── .env                    # Environment variables (gitignored)
└── Makefile                # Dev commands → @Makefile
```

## Environment Variables

### Environment Files

- @.env.example - Template with all required variables
- `.env` - Local config (gitignored, copy from .env.example)
- Loaded via `python-dotenv` at startup

### Required Environment Variables

**Core:**
- `ENVIRONMENT` - `development` | `staging` | `production`
- `SECRET_KEY` - JWT signing key (generate: `openssl rand -hex 32`)
- `DATABASE_URL` - PostgreSQL: `postgresql://user:pass@host:5432/db`
- `HOST` - Server bind (`127.0.0.1` dev, `0.0.0.0` prod)
- `PORT` - Server port (default: `8001`)
- `APP_NAME` - Application name
- `APP_VERSION` - Version string
- `DEBUG` - `True` | `False`

**Security:**
- `JWT_ALGORITHM` - Default: `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Default: `30`

**AI Services:**
- `OPENROUTER_API_KEY` - OpenRouter API key for image/text generation
- `OPENROUTER_BASE_URL` - `https://openrouter.ai/api/v1`
- `GEMINI_API_KEY` - Google Gemini direct API key (optional)
- `HF_API_TOKEN` - HuggingFace token for gated models (FLUX.1)
- `REPLICATE_API_TOKEN` - Replicate API token (alternative provider)

**Google Drive (Optional):**
- `GOOGLE_DRIVE_FOLDER_ID` - Drive folder for ebook backups
- `GOOGLE_API_KEY` - Google API key
- `GOOGLE_CREDENTIALS_PATH` - Service account JSON path (default: `credentials/google_credentials.json`)

**Local Stable Diffusion (Optional):**
- `LOCAL_SD_USE_CPU` - `true` | `false` - Force CPU usage (default: `false`, uses GPU if available)
- `SDXL_TURBO_STEPS` - SDXL-turbo generation steps (default: `6`, range: 1-10)
- `SDXL_TURBO_GUIDANCE` - SDXL-turbo guidance scale (default: `0.0`, range: 0.0-2.0)
- Note: Provider selection configured in @config/generation/models.yaml (covers, coloring_page)

**Local Storage:**
- `LOCAL_STORAGE_PATH` - Path for local PDF storage (default: `./storage`)

**Testing:**
- `TESTING` - `true` | `false` - Enable test mode
- `USE_FAKE_CATALOG` - `true` | `false` - Use fake data instead of real APIs

### CI Environment Variables

- `SECRET_KEY` - `test-key-for-ci`
- `DATABASE_URL` - `postgresql://test:test@localhost:5432/test`
- `ALGORITHM` - `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` - `30`
- `GOOGLE_DRIVE_CREDENTIALS_FILE` - From GitHub secrets

## URLs

**Development:**
- URL: http://127.0.0.1:8001
- API Docs: http://127.0.0.1:8001/docs
- Health Check: http://127.0.0.1:8001/healthz
- Purpose: Local development (localhost binding for security)

**Production:**
- URL: N/A (local development tool)
- SLA: N/A

## Containerization

```mermaid
graph LR
    A[Docker Compose] --> B[PostgreSQL Container]
    A --> C[App Container]
    C --> D[Uvicorn Server]
    D --> E[FastAPI App]
```

**Docker Commands** (@Makefile):
- `make docker-build` - Build Docker images
- `make docker-up` - Start all services (detached)
- `make docker-down` - Stop all services
- `make docker-logs` - Show logs from all services
- `make docker-shell` - Open shell in app container
- `make docker-test` - Run tests inside Docker container
- `make docker-clean` - Stop services and remove volumes
- `make docker-dev` - Alias for `docker-up`

## Database

- **Type**: PostgreSQL (local dev)
- **Connection**: Via `DATABASE_URL` environment variable
- **Driver**: psycopg2-binary (sync only)
- **Migrations**: Alembic → @src/backoffice/migrations/
- **Commands**: `make db-migrate` (upgrade head), `make db-status` (show current + history)

## Local File Storage

- **Generated Ebooks**: `ebooks/` directory at project root
- **Local PDF Storage**: Configurable via `LOCAL_STORAGE_PATH` (default: `./storage`)
- **Google Credentials**: `credentials/google_credentials.json` (path configurable via `GOOGLE_CREDENTIALS_PATH`)
- **Google Drive Backup**: Optional upload to Google Drive folder (ID in `GOOGLE_DRIVE_FOLDER_ID`)
- **Generation Specs**: `specs/` directory (YAML files created from GitHub issues)

## Server

- **ASGI Server**: Uvicorn
- **Reload**: Enabled in dev mode (`--reload`)
- **Binding**: `HOST` env var (`127.0.0.1` dev, `0.0.0.0` prod)
- **Port**: `PORT` env var (default: `8001`)
- **Entry Point**: `backoffice.main:app` (FastAPI application)

## Development Commands

All commands via `make` → @Makefile

**Setup:**
- `make install` - Install dev dependencies + Playwright (editable install with `[dev]` extras)
- `make install-dev` - Same as `make install`
- `make install-prod` - Runtime dependencies only (no dev tools)
- `make setup` - Full setup (install + migrate)

**Run:**
- `make run` - Start uvicorn dev server at http://127.0.0.1:8001 (with reload)
- `make dev` - Run migrations then start server

**Database:**
- `make db-migrate` - Run Alembic migrations (`alembic upgrade head`)
- `make db-status` - Show current migration status and history (`alembic current && alembic history`)

**Testing:**
- `make test` - Run unit tests only (146 tests, ~1s) - excludes integration/E2E
- `make test-unit` - Unit tests from all features (`pytest src/backoffice/features/*/tests/unit`)
- `make test-integration` - ⚠️ Currently disabled (fixture import issue, requires Docker + testcontainers)
- `make test-smoke` - E2E health check smoke test (Playwright, Chromium, ~6s)
- `make test-e2e` - Full E2E tests with Playwright (Chromium, screenshots on failure, video on failure)

**Code Quality:**
- `make lint` - Ruff linting (`ruff check .`)
- `make format` - Ruff auto-format (`ruff format .`)
- `make fix` - Auto-fix lint issues + format (`ruff check --fix . && ruff format`)
- `make typecheck` - Mypy type checking (`mypy src/`)
- `make deps` - Deptry dependency analysis (`deptry src`)
- `make deadcode` - Vulture dead code detection (`vulture . --min-confidence=80`)
- `make precommit` - Run all pre-commit hooks on all files

## Testing & Code Quality Execution

**Test Execution:**
- Unit tests: `pytest src/backoffice/features/*/tests/unit -v` (co-located with features) → @pytest.ini
- Integration tests: testcontainers + PostgreSQL (⚠️ disabled due to fixture import issue) → @pytest.ini
- E2E tests: Playwright (Chromium browser) → @tests/e2e/ via @pytest.ini
- Test markers: `smoke`, `scenarios`, `integration`, `error_handling`, `workflow`, `e2e`
- Pytest mode: `asyncio_mode = auto`, `import-mode=importlib`

**Code Quality Execution:**
- Linting: `ruff check .` → @pyproject.toml
- Formatting: `ruff format .` → @pyproject.toml
- Type checking: `mypy src/` → @pyproject.toml
- Pre-commit: `pre-commit run --all-files` → @.pre-commit-config.yaml
- Dead code: `vulture . --min-confidence=80` → @pyproject.toml
- Dependencies: `deptry src` → @pyproject.toml

**Pre-commit Hooks** (@.pre-commit-config.yaml):
- Ruff lint (import sorting only with `--fix --select I`)
- Ruff format
- Mypy type check (pass_filenames=false, runs on `src/`)
- Vulture dead code check (`src/ .vulture_whitelist.py --min-confidence=80`)
- Deptry dependency check (`src/`)
- Pytest unit tests (excludes integration/E2E/scenarios, `--tb=line`)
