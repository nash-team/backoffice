# Coding Guidelines

> Those rules must be minimal because they MUST be checked after EVERY CODE GENERATION.

## Requirements to complete a feature

In order to complete a feature at its best, always check at the end of the implementation:

- [ ] Whole plan is implemented in code (no omissions)
- [ ] All technical rules are followed
- [ ] Typechecking is enforced (`make typecheck`)
- [ ] Tests are passing (`make test`)
- [ ] Build is successful

**A feature is really completed if ALL of the above are satisfied: if not, iterate to fix all until all are green.**

## Quality Gates (Enforceable)

Run before committing (@.pre-commit-config.yaml auto-runs these):

```bash
make lint        # Must pass (ruff check)
make format      # Must apply (ruff format)
make typecheck   # Must pass (mypy)
make test        # Must pass (146 unit tests)
make precommit   # Must pass (all hooks)
```

**Pre-commit Hooks** (@.pre-commit-config.yaml):
1. Ruff import sorting (`--fix --select I`)
2. Ruff format (auto-format)
3. MyPy type checking (all of `src/`)
4. Vulture dead code detection (min confidence: 80%)
5. Deptry dependency analysis (checks unused/missing deps)
6. Pytest unit tests (excludes `integration`, `e2e`, `scenarios` markers)

## Stack specifics rules

**Type Hints (Required) (@pyproject.toml [tool.mypy]):**
- [ ] All function signatures have type hints (params + return)
- [ ] No bare `def func(x)` without types
- [ ] Use `| None` for optional types (Python 3.11+)
- [ ] Use `list[T]`, `dict[K, V]` (not `List`, `Dict`)
- [ ] MyPy must pass with: `warn_unused_ignores`, `no_implicit_optional`, `warn_redundant_casts`, `warn_return_any`

**Async/Await:**
- [ ] Database operations use sync (SQLAlchemy ORM is synchronous - NO async)
- [ ] FastAPI routes can be async for non-blocking I/O
- [ ] File operations are sync (aiofiles is available but prefer sync)
- [ ] Keep it simple: sync is the standard for DB and file I/O

**Import Rules (@pyproject.toml [tool.ruff.lint]):**
- [ ] Imports at top of file (ruff E402 enforced)
- [ ] Absolute imports from `backoffice.features.*`
- [ ] No circular imports (hexagonal architecture prevents this)
- [ ] Grouped: stdlib → third-party → local (ruff I enforced via `isort`)
- [ ] Known first-party: `backoffice` (@pyproject.toml [tool.ruff.lint.isort])

**Error Handling (@features/shared/domain/errors/error_taxonomy.py):**
- [ ] Use `DomainError` with `ErrorCode` for business errors
- [ ] Include `actionable_hint` in error messages
- [ ] No bare `Exception` or `ValueError` for business logic
- [ ] Example: `raise DomainError(code=ErrorCode.VALIDATION_ERROR, message="...", actionable_hint="...")`

**Pydantic Validation:**
- [ ] Input DTOs use Pydantic models with type hints
- [ ] Field validators for business rules
- [ ] No manual validation where Pydantic can handle it
- [ ] Use Pydantic v2 features (BaseModel with `model_config`)

**Testing (@pytest.ini, @.pre-commit-config.yaml):**
- [ ] Use fakes from `features/shared/tests/unit/fakes/` (Chicago-style testing)
- [ ] No mocks (fakes enforce real behavior)
- [ ] Test files co-located in `features/*/tests/unit/`
- [ ] Test fixtures with side effects prefixed with `_`
- [ ] All unit tests pass: `make test` (excludes markers: `integration`, `e2e`, `scenarios`)
- [ ] Tests use markers: `smoke`, `scenarios`, `integration`, `error_handling`, `workflow`, `e2e`

**Naming Conventions:**
- [ ] Use Cases: `VerbNounUseCase` (e.g., `ApproveEbookUseCase`)
- [ ] Ports (interfaces): `NounPort` (e.g., `EbookPort`, `FileStoragePort`)
- [ ] Adapters/Providers: `TechnologyNounProvider` (e.g., `OpenRouterImageProvider`)
- [ ] Tests: `test_subject_scenario` (e.g., `test_approve_draft_ebook`)
- [ ] Test fixtures with side effects: `_fixture_name`

## Functional specifics rules

**Hexagonal Architecture (Ports & Adapters):**
- [ ] Domain has NO external dependencies (no FastAPI, SQLAlchemy, Pillow, etc.)
- [ ] Ports define interfaces (abstract classes with `ABC`)
- [ ] Adapters implement ports
- [ ] Dependency flow: `presentation → infrastructure → domain` (NEVER reversed)

**Feature-Based Organization (Screaming Architecture):**
- [ ] New code in `features/<name>/`
- [ ] Shared code only if used by 2+ features → `features/shared/`
- [ ] NO root-level technical folders (`domain/`, `infrastructure/`, `presentation/` at root)
- [ ] Tests in `features/<name>/tests/` (co-located)
- [ ] Each feature is a DDD Bounded Context

**DDD Patterns:**
- [ ] Use Cases handle commands/queries (one `execute()` method)
- [ ] Entities contain business logic (no anemic models)
- [ ] Value Objects are immutable
- [ ] Domain Events published via EventBus

**EventBus Communication (@features/shared/infrastructure/events/event_bus.py):**
- [ ] Features communicate via domain events (NOT direct calls)
- [ ] EventBus publishes after business action
- [ ] EventHandlers subscribe to events
- [ ] Example: `await event_bus.publish(EbookApprovedEvent(...))`

**Database Transactions:**
- [ ] Use cases wrapped in DB transactions (via repository pattern)
- [ ] Rollback on business errors
- [ ] Commit only on success
- [ ] Use synchronous SQLAlchemy (no async DB operations)

**Security (@pyproject.toml [tool.ruff.lint] select S):**
- [ ] No secrets in code (use env vars via python-dotenv)
- [ ] JWT for authentication
- [ ] Input sanitization via Pydantic
- [ ] SQL injection prevented (SQLAlchemy ORM)
- [ ] Bandit security rules enforced (ruff S rules)

**FastAPI Dependency Injection:**
- [ ] Services injected via `Depends()`
- [ ] Repository instances from DI
- [ ] No global state

## Linting & Formatting (@pyproject.toml)

**Ruff Configuration:**
- Line length: **200 chars** (enforced)
- Target: Python 3.11
- Select: `E` (errors), `W` (warnings), `F` (pyflakes), `I` (isort), `B` (bugbear), `C4` (comprehensions), `UP` (pyupgrade), `S` (bandit security)
- Per-file ignores:
  - Tests (`tests/**`, `**/tests/**`): Allow `S101` (assert), `E501` (long lines), `E402` (late imports)
  - Main (`src/backoffice/main.py`): Allow `S104` (0.0.0.0 binding for Docker)
  - Migrations (`src/backoffice/migrations/**`): Allow `E501` (long SQL lines)
- Exclude: `.vulture_whitelist.py`, `test_local_sd.py`

**MyPy Configuration:**
- Python version: 3.11
- Plugins: `pydantic.mypy`
- `warn_unused_ignores = true`
- `no_implicit_optional = true`
- `warn_redundant_casts = true`
- `warn_return_any = true`
- `show_error_codes = true`
- Exclude: `scripts/`, `tests/`, `features/.*/tests/`
- Ignore missing imports for: `googleapiclient.*`, `weasyprint`, `img2pdf`, `replicate`, `torch`, `diffusers`, etc.

**Vulture Configuration (@.pre-commit-config.yaml):**
- Min confidence: 80%
- Exclude: `**/__init__.py`
- Whitelist: `.vulture_whitelist.py`

**Deptry Configuration (@pyproject.toml [tool.deptry]):**
- Exclude: `tests`, `features/**/tests`, `migrations`, `scripts`, `.venv`, etc.
- Dev dependency groups: `dev` (ignored for unused dep checks)
- Per-rule ignores:
  - `DEP002`: Framework-used deps (`jinja2`, `python-multipart`, `aiofiles`, `psycopg2-binary`, `asyncpg`)
  - `DEP004`: Dev tools imported in code (`alembic`, `pytest`)
- Package name mappings: `google-api-python-client` → `googleapiclient`, `psycopg2-binary` → `psycopg2`, `pillow` → `PIL`

## Test Configuration (@pytest.ini)

- `asyncio_mode = auto`
- `testpaths = tests, src/backoffice/features` (co-located tests)
- `python_files = test_*.py *_test.py`
- `python_classes = Test*`
- `python_functions = test_*`
- `--import-mode=importlib` (prevents module conflicts in features/*/tests)
- `--strict-markers` (all markers must be declared)
- `--strict-config` (enforce pytest configuration)
- Markers: `smoke`, `scenarios`, `integration`, `error_handling`, `workflow`, `e2e`
- No recursion into: `.venv`, `migrations`, `static`, `templates`, `__pycache__`
