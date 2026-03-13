# Testing Guidelines

## Tools and Frameworks

- **pytest 7**: Test runner with async support
- **pytest-asyncio 0.21**: Async test execution (@pytest.ini asyncio_mode=auto)
- **playwright 1**: Browser automation for E2E tests
- **pytest-playwright 0**: Pytest integration for Playwright
- **testcontainers 4**: PostgreSQL containers for integration tests
- **FastAPI TestClient**: HTTP client for API testing

## Testing Strategy

- **Approach**: Chicago-style (fakes over mocks)
- **Test Types**:
  - **Unit Tests (331)**: Fast, isolated, use fakes, no I/O (~27s total)
  - **Integration Tests (40)**: Real PostgreSQL via testcontainers (currently disabled - fixture import issue)
  - **E2E Tests (1)**: Minimal smoke test with Playwright (health check only)

## Test Organization

- **Co-location**: Tests live in `features/*/tests/` next to code they test
- **Fakes Location**: `@features/ebook/shared/tests/unit/fakes/` & `@features/shared/tests/unit/fakes/`
- **Fixtures**:
  - **Unit**: Inline fakes (FakeEbookRepository, FakeGenerationStrategy)
  - **Integration**: @tests/conftest.py (postgres_container, test_db_session, test_client)
  - **E2E**: @tests/e2e/conftest.py (test_server, server_url)

## Test Execution

- `make test` - Run unit tests from all features + fixtures (~27s)
- `make test-unit` - Same as above (331 tests)
- `make test-integration` - Integration tests (disabled - requires Docker + testcontainers)
- `make test-smoke` - E2E smoke test with Playwright (health check)
- `make test-e2e` - All E2E tests (chromium, screenshots on failure)

### Pytest Configuration

- **Config**: @pytest.ini
- **Test paths**: `tests/` + `src/backoffice/features/`
- **Import mode**: importlib (avoids module name conflicts with feature-based structure)
- **Markers**: smoke, scenarios, integration, error_handling, workflow, e2e

## Mocking and Stubbing

**Chicago-style**: Use **fakes** (simplified real implementations) instead of mocks

### Available Fakes

Located in `@features/ebook/shared/tests/unit/fakes/`:
- **FakeCoverPort**: Configurable cover generation (succeed, fail_quality, fail_unavailable). Returns valid PNG bytes.
- **FakePagePort**: Content page generation. Returns valid PNG bytes (Pillow-generated with gradient pattern, unique per call).
- **FakeAssemblyPort**: PDF assembly
- **FakeFileStoragePort**: File storage operations
- **FakeImageEditPort**: Image editing operations

### Fake Usage Pattern

```python
from backoffice.features.ebook.shared.tests.unit.fakes.fake_cover_port import FakeCoverPort

# Configure behavior
fake_port = FakeCoverPort(mode="succeed", image_size=10000)

# Use in test
service = CoverGenerationService(cover_port=fake_port)
result = await service.generate_cover(prompt="Test", spec=spec)

# Verify behavior
assert len(result) == 10000
assert fake_port.call_count == 1
assert fake_port.last_prompt == "Test"
```

### Fake Modes

- **succeed**: Return valid data
- **fail_quality**: Return invalid data (too small, wrong format)
- **fail_unavailable**: Simulate provider unavailable error

### Benefits Over Mocks

- Real implementation (simplified)
- Controlled behavior via constructor
- Stateful (track calls, last inputs)
- Reusable across tests
- No brittle setup/expectations

## Integration Test Setup

**Currently disabled** - fixture import issue to be resolved

### When Working

- Uses **testcontainers** for PostgreSQL 15
- Auto-creates schema via SQLAlchemy Base.metadata
- Cleans data between tests (session.rollback + table truncate)
- Overrides FastAPI `get_db` dependency with test session

## E2E Test Setup

- **Minimal approach**: Only critical health checks
- **Philosophy**: UI evolves rapidly, prefer manual testing
- **Server**: Ephemeral SQLite + uvicorn subprocess
- **Browser**: Chromium only
- **Artifacts**: Screenshots/videos on failure only

## Test Naming Conventions

- **Files**: `test_*.py` (e.g., `test_create_ebook.py`)
- **Functions**: `test_<subject>_<scenario>` (e.g., `test_approve_ebook_success`)
- **Classes**: `Test*` (e.g., `TestApproveUseCase`)
- **Fixtures with side effects**: Prefix with `_` (e.g., `_sample_ebooks`)

## Running Specific Tests

```bash
# Single feature
pytest src/backoffice/features/ebook/creation/tests/unit -v

# Single file
pytest src/backoffice/features/ebook/lifecycle/tests/unit/domain/usecases/test_approve_ebook.py -v

# Single test
pytest path/to/test.py::test_function_name -v

# With output
pytest path/to/test.py -vv -s
```

## Test Markers

Use markers to categorize tests (@pytest.ini):

```python
@pytest.mark.smoke        # Critical health checks
@pytest.mark.integration  # Requires DB
@pytest.mark.e2e          # Requires browser
@pytest.mark.scenarios    # Business scenarios
@pytest.mark.error_handling  # Error cases
@pytest.mark.workflow     # Multi-step workflows
```

## Quality Gates

- **Pre-commit**: All hooks must pass before commit
- **Unit tests**: Must pass (331 tests, ~27s)
- **Smoke test**: Must pass (E2E health check)
- **Coverage**: No explicit target (focus on critical paths)
- **Type checking**: mypy excludes test files (@pyproject.toml)

## Test Data Patterns

- **Inline builders**: Create entities directly in tests
- **Fixture factories**: For complex setups
- **Minimal data**: Only create what's needed for test
- **Cleanup**: Auto-rollback for integration tests
- **Isolation**: Each test is independent

## Known Issues

- Integration tests disabled (40 tests) - fixture import issue with feature-based structure
- TODO: Fix `test_client` fixture import for `features/*/tests/integration`
