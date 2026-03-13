# Testing Guidelines

## Backend

### Tools and Frameworks

- **pytest 7**: Test runner with async support
- **pytest-asyncio 0.21**: Async test execution (@pytest.ini asyncio_mode=auto)
- **playwright 1**: Browser automation for E2E tests
- **testcontainers 4**: PostgreSQL containers for integration tests
- **FastAPI TestClient**: HTTP client for API testing

### Testing Strategy

- **Approach**: Chicago-style (fakes over mocks)
- **Test Types**:
  - **Unit Tests (331)**: Fast, isolated, use fakes, no I/O (~27s total)
  - **Integration Tests (40)**: Real PostgreSQL via testcontainers (currently disabled - fixture import issue)
  - **E2E Tests (1)**: Minimal smoke test with Playwright (health check only)

### Test Organization

- **Co-location**: Tests live in `features/*/tests/` next to code they test
- **Fakes Location**: `@features/ebook/shared/tests/unit/fakes/` & `@features/shared/tests/unit/fakes/`
- **Fixtures**:
  - **Unit**: Inline fakes (FakeEbookRepository, FakeGenerationStrategy)
  - **Integration**: @tests/conftest.py (postgres_container, test_db_session, test_client)
  - **E2E**: @tests/e2e/conftest.py (test_server, server_url)

### Test Execution

- `make test` - Unit tests from all features + fixtures (~27s)
- `make test-unit` - Same as above (331 tests)
- `make test-integration` - Integration tests (disabled)
- `make test-smoke` - E2E smoke test with Playwright
- `make test-e2e` - All E2E tests (chromium)

### Available Fakes

Located in `@features/ebook/shared/tests/unit/fakes/`:
- **FakeCoverPort**: Configurable cover generation. Returns valid PNG bytes.
- **FakePagePort**: Content page generation. Returns valid PNG bytes (Pillow-generated with gradient pattern, unique per call).
- **FakeAssemblyPort**: PDF assembly
- **FakeFileStoragePort**: File storage operations
- **FakeImageEditPort**: Image editing operations

### Fake Usage Pattern

```python
from backoffice.features.ebook.shared.tests.unit.fakes.fake_cover_port import FakeCoverPort

fake_port = FakeCoverPort(mode="succeed", image_size=10000)
service = CoverGenerationService(cover_port=fake_port)
result = await service.generate_cover(prompt="Test", spec=spec)

assert len(result) == 10000
assert fake_port.call_count == 1
```

### Fake Modes

- **succeed**: Return valid data
- **fail_quality**: Return invalid data (too small, wrong format)
- **fail_unavailable**: Simulate provider unavailable error

### Test Naming Conventions

- **Files**: `test_*.py` (e.g., `test_create_ebook.py`)
- **Functions**: `test_<subject>_<scenario>` (e.g., `test_approve_ebook_success`)
- **Classes**: `Test*` (e.g., `TestApproveUseCase`)
- **Fixtures with side effects**: Prefix with `_` (e.g., `_sample_ebooks`)

### Test Markers

```python
@pytest.mark.smoke        # Critical health checks
@pytest.mark.integration  # Requires DB
@pytest.mark.e2e          # Requires browser
@pytest.mark.scenarios    # Business scenarios
@pytest.mark.error_handling  # Error cases
@pytest.mark.workflow     # Multi-step workflows
```

### Known Issues

- Integration tests disabled (40 tests) - fixture import issue with feature-based structure

## Frontend

### Tools

- **Vitest 3**: Test runner (Vite-native)
- **jsdom**: DOM simulation environment
- Config: @frontend/vitest.config.ts

### Strategy

- **Chicago-style**: Fakes over mocks (mirrors backend approach)
- **Co-located tests**: `features/ebooks/tests/unit/`
- **Global fakes**: `src/tests/fakes/`

### Execution

- `npm run test` — Run once
- `npm run test:watch` — Watch mode
- `make frontend-test` — From project root

### Available Fakes

Located in `@frontend/src/tests/fakes/`:

| Fake | Implements | Tracks |
|------|-----------|--------|
| `FakeEbookGateway` | `EbookGateway` | `callCounts` per method, in-memory ebook store |
| `FakeExportGateway` | `ExportGateway` | Call counts |
| `FakeRegenerationGateway` | `RegenerationGateway` | Call counts |

### Test Coverage

- Use case thunks (list, create, approve, reject, stats, formConfig)
- Redux selectors
- No component/E2E tests yet (UI evolves rapidly)

## Quality Gates

- **Pre-commit**: All hooks must pass before commit
- **Unit tests**: Must pass (331 tests, ~27s)
- **Smoke test**: Must pass (E2E health check)
- **Type checking**: mypy excludes test files (@pyproject.toml)
