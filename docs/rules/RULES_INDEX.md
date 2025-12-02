# Rules Index

> Reference index for all coding rules in the project
> **Last updated**: November 2025
> **Total rules**: 25 active rules

---

## 📋 Quick Reference

| Category | Rules Count | Status |
|----------|-------------|--------|
| Architecture | 3 | ✅ Up-to-date |
| Standards | 2 | ✅ Up-to-date |
| Frameworks & Libraries | 5 | ✅ Up-to-date |
| Tools & Configurations | 5 | ✅ Up-to-date |
| Templates & Models | 1 | ✅ Up-to-date |
| Quality Assurance | 8 | ✅ Up-to-date |
| Domain | 1 | ✅ Up-to-date |

---

## 🏗️ 00 - Architecture (3 rules)

### ✨ `0-feature-based-architecture.mdc` (NEW)
**100% Feature-Based Architecture (Screaming Architecture)**

- All code organized by business feature in `features/`
- No technical folders at root (`domain/`, `infrastructure/`, `presentation/` forbidden)
- Tests co-located in `features/<feature>/tests/`
- Shared code ONLY in `features/shared/`
- **Always Applied**: Yes

### ✨ `0-event-driven-architecture.mdc` (NEW)
**Event-Driven Architecture with EventBus**

- DomainEvent base class (frozen dataclass)
- Naming: `<Entity><Action>Event`
- EventBus centralized in `features/shared/infrastructure/events/`
- Events emitted AFTER successful action
- **Always Applied**: Yes

### ♻️ `0-hexagonal-architecture.mdc` (UPDATED)
**Hexagonal Architecture (Ports & Adapters)**

- Domain layer isolation (no infrastructure imports)
- Dependency inversion (domain → infrastructure → presentation)
- Ports in `features/shared/domain/ports`
- Adapters in `features/shared/infrastructure/adapters`
- **Always Applied**: Yes
- **Note**: Updated paths for feature-based architecture

---

## 📐 01 - Standards (2 rules)

### ✨ `1-domain-errors.mdc` (NEW)
**Structured Domain Error Handling**

- Use `DomainError` dataclass, not generic exceptions
- Include `code` (ErrorCode enum), `message`, `actionable_hint`
- Categories: `quality.*`, `provider.*`, `policy.*`, `validation.*`
- Never use `ValueError`, `RuntimeError`, `Exception`
- **Always Applied**: Yes

### `1-python-standards.mdc`
**Python Coding Standards**

- Type hints everywhere
- Async/await for I/O operations
- Dataclasses for immutable data
- Naming conventions (snake_case, PascalCase)
- **Always Applied**: Yes

---

## 🎨 03 - Frameworks & Libraries (5 rules)

### `3-fastapi.mdc`
**FastAPI Best Practices**

- Dependency injection via `Depends()`
- Pydantic models for validation
- APIRouter for route organization
- Async route handlers

### `3-htmx.mdc`
**HTMX Dynamic UI Patterns**

- Server-side rendering with HTMX
- Partial template responses
- HTMX attributes (hx-get, hx-post, hx-swap)

### `3-pydantic.mdc`
**Pydantic Models & Validation**

- Use Pydantic v2 syntax
- Field validators for business rules
- DTO pattern for API contracts

### `3-sqlalchemy@2.mdc`
**SQLAlchemy 2.0+ Patterns**

- Async engine and sessions
- Mapped columns with type annotations
- ORM models in infrastructure layer only

### `3-sqlalchemy-postgresql.mdc`
**PostgreSQL with SQLAlchemy**

- PostgreSQL-specific features
- Connection pooling
- Database migrations with Alembic

---

## 🛠️ 04 - Tools & Configurations (5 rules)

### `4-alembic.mdc`
**Database Migrations with Alembic**

- Auto-generate migrations from models
- Review migrations before applying
- Naming: `YYYY_MM_DD_description`

### ✨ `4-pre-commit-complete.mdc` (NEW)
**Pre-commit Hooks Suite (6 hooks)**

- Hook order: ruff → ruff-format → mypy → vulture → deptry → pytest-unit
- All 6 hooks must pass (6/6) before commit
- Fast feedback loop (<5s total)
- **Always Applied**: Yes

### `4-pyright.mdc`
**Pyright Type Checking**

- Strict mode enabled
- Check against `src` directory
- Complement to mypy

### ✨ `4-ruff-complete.mdc` (NEW)
**Ruff Lint + Format (replaces Black)**

- E402 import order ENFORCED (even in tests)
- S101 asserts allowed in tests
- Per-file ignores for special cases
- Target Python 3.11, line-length 100
- **Always Applied**: Yes

### ✨ `4-vulture-deptry.mdc` (NEW)
**Dead Code & Dependency Hygiene**

- Vulture detects unused code (80% confidence)
- Underscore prefix for side-effect fixtures
- Deptry validates imports match pyproject.toml
- Whitelist in `.vulture_whitelist.py`
- **Always Applied**: Yes

---

## 📝 06 - Templates & Models (1 rule)

### ✨ `6-feature-template.mdc` (NEW)
**Feature Creation Template**

- Minimum structure: `domain/`, `presentation/`, `tests/`
- Use case pattern with EventBus
- Router registration in `main.py`
- README.md per feature
- **Always Applied**: No (template reference)

---

## ✅ 07 - Quality Assurance (8 rules)

### `7-coverage.mdc`
**Code Coverage Standards**

- Minimum 80% coverage for domain logic
- pytest-cov for coverage reports
- Exclude fakes and test utilities

### `7-e2e-testing.mdc`
**End-to-End Testing with Playwright**

- Minimal smoke tests only
- Test critical user paths
- Cross-feature scenarios

### `7-performance.mdc`
**Performance Standards**

- Response time targets
- Database query optimization
- Caching strategies

### ✨ `7-pytest-fakes.mdc` (NEW)
**Chicago-Style Testing with Fakes**

- Use Fakes (real simplified implementations), not Mocks
- Fakes in `features/shared/tests/unit/fakes/`
- Configurable behavior modes (`succeed`, `fail_*`)
- Call tracking for assertions
- **Always Applied**: Yes

### ✨ `7-pytest-markers.mdc` (NEW)
**Pytest Markers & Selective Execution**

- Markers: `integration`, `e2e`, `scenarios`
- Module-level: `pytestmark = pytest.mark.integration`
- Pre-commit runs only unit tests
- Underscore prefix for side-effect fixtures
- **Always Applied**: Yes

### ♻️ `7-pytest.mdc` (UPDATED)
**Pytest Testing Standards**

- Chicago style (Fakes over Mocks)
- Tests co-localized in `features/<feature>/tests/`
- Async fixtures for async operations
- Given-When-Then structure
- **Always Applied**: Yes
- **Note**: Updated for co-localized tests and fakes

### `7-security.mdc`
**Security Best Practices**

- No hardcoded secrets
- Input validation with Pydantic
- SQL injection prevention
- CORS configuration

### ✨ `7-tests-colocated.mdc` (NEW)
**Co-localized Test Structure**

- Tests live next to code in `features/<feature>/tests/`
- Mirror domain structure in test directories
- Root `tests/` ONLY for cross-feature E2E
- Each feature owns its tests
- **Always Applied**: Yes

---

## 🎯 08 - Domain (1 rule)

### ✨ `8-domain-error-handling.mdc` (NEW)

**Domain Error Handling with DomainError**

- Use `DomainError` with `ErrorCode` enum taxonomy
- Required fields: `code`, `message`, `actionable_hint`
- Categories: `quality.*`, `provider.*`, `policy.*`, `validation.*`
- Apply in domain layer and infrastructure layer
- Never use generic `ValueError` or `Exception`
- **Always Applied**: No (domain/infrastructure only)

---

## 📊 Statistics

### Rules by Status
- ✨ **New rules created**: 11
- ♻️ **Rules updated**: 2
- ❌ **Rules deleted**: 3 (obsolete)
- ✅ **Total active rules**: 25

### Coverage by Category
- 🏗️ Architecture: **3 rules** (100% feature-based aligned)
- 📐 Standards: **2 rules** (error handling + Python)
- 🎨 Frameworks: **5 rules** (FastAPI, SQLAlchemy, HTMX, Pydantic)
- 🛠️ Tools: **5 rules** (pre-commit 6 hooks, ruff, vulture, deptry)
- 📝 Templates: **1 rule** (feature creation guide)
- ✅ QA: **8 rules** (tests co-localized, fakes, markers, coverage, security)
- 🎯 Domain: **1 rule** (DomainError taxonomy)

---

## 🎯 Rule Usage Guide

### When Creating a New Feature
1. ✅ `0-feature-based-architecture.mdc` - Follow feature structure
2. ✅ `6-feature-template.mdc` - Use template commands
3. ✅ `0-event-driven-architecture.mdc` - Emit domain events
4. ✅ `7-tests-colocated.mdc` - Create tests/ directory

### When Writing Tests
1. ✅ `7-tests-colocated.mdc` - Tests in feature directory
2. ✅ `7-pytest-fakes.mdc` - Use fakes, not mocks
3. ✅ `7-pytest-markers.mdc` - Add appropriate markers
4. ✅ `7-pytest.mdc` - Follow naming conventions

### Before Committing
1. ✅ Run `pre-commit run --all-files` (6 hooks)
2. ✅ Check `4-pre-commit-complete.mdc` if hooks fail
3. ✅ All 6/6 hooks must pass

### When Handling Errors

1. ✅ `1-domain-errors.mdc` - Use DomainError with ErrorCode (standards)
2. ✅ `8-domain-error-handling.mdc` - Full taxonomy guide (domain)
3. ✅ Include actionable_hint
4. ✅ Never use generic exceptions

---

## 🔗 Related Documentation

- **CLAUDE.md** - Main project context (conversational guide)
- **ARCHITECTURE.md** - Detailed architecture documentation
- **aidd-docs/memory-bank/CODING.md** - Quality checklist
- **docs/rules/** - All coding rules (this index)

---

**Maintained by**: Backoffice Team
**Last audit**: November 2025
**Next review**: When new patterns emerge
