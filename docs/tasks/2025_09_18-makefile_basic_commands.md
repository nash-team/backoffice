# Instruction: Met en place un Makefile avec les commandes de bases

## Feature

- **Summary**: Create a Makefile with essential development workflow commands for local development including installation, server management, testing, and database operations
- **Stack**: `Makefile`, `Python 3.11+`, `FastAPI`, `Uvicorn`, `Pytest`, `Playwright`, `SQLAlchemy`, `Alembic`, `SQLite`

## Existing files

- @requirements.txt
- @main.py
- @pytest.ini
- @alembic.ini
- @tests/e2e/
- @infrastructure/database/

### New file to create

- Makefile

## Implementation phases

### Phase 1: Core Development Workflow

> Setup essential commands for daily development tasks

1. Create Makefile with install command using pip and requirements.txt
2. Add run command with uvicorn server startup configuration
3. Add clean command for removing Python cache, test artifacts, and temporary files

### Phase 2: Testing Integration

> Integrate existing pytest and Playwright test infrastructure

1. Add test command to run all tests with proper environment setup
2. Add test-unit command for running unit tests only
3. Add test-e2e command for Playwright E2E tests with browser setup

### Phase 3: Database Management

> Database operations using existing Alembic configuration

1. Add db-migrate command using Alembic for running migrations
2. Add db-reset command for dropping and recreating database
3. Add db-status command to check current migration status

### Phase 4: Quality and Documentation

> Additional helpful commands and project documentation

1. Add help command displaying all available commands with descriptions
2. Add development setup verification commands
3. Document Makefile usage and integrate with project workflow

## Reviewed implementation

- [ ] Phase 1: Core Development Workflow
- [ ] Phase 2: Testing Integration
- [ ] Phase 3: Database Management
- [ ] Phase 4: Quality and Documentation

## Validation flow

1. Run `make help` to see all available commands
2. Run `make install` on fresh environment to setup dependencies
3. Run `make db-migrate` to setup database
4. Run `make run` to start development server
5. Run `make test` to execute all tests
6. Run `make clean` to cleanup generated files
7. Verify commands work across different local environments

## Estimations

- High confidence (9/10)
- 2-3 hours to implement and test all commands