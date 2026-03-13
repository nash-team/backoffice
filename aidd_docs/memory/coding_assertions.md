# Coding Guidelines

> Those rules must be minimal because they MUST be checked after EVERY CODE GENERATION.

## Requirements to complete a feature

**A feature is really completed if ALL of the below are satisfied: if not, iterate to fix all until all are green.**

## Commands to run

### Before commit

| Order | Command | Description |
| ----- | ------- | ----------- |
| 1 | `ruff check .` | Lint (import sorting, code quality) |
| 2 | `ruff format .` | Auto-format code |
| 3 | `mypy src/` | Type checking |
| 4 | `vulture src/ .vulture_whitelist.py --min-confidence=80` | Dead code detection |
| 5 | `deptry src/` | Dependency analysis |
| 6 | `pytest -m "not integration and not e2e and not scenarios" -v` | Unit tests (331 tests, ~27s) |

### Before push

| Order | Command | Description |
| ----- | ------- | ----------- |
| 1 | `make precommit` | Run all pre-commit hooks on all files |
| 2 | `make test-e2e` | E2E smoke test (Playwright, Chromium) |
| 3 | `make frontend-test` | Frontend unit tests (Vitest) |

## Pre-commit Hooks

@.pre-commit-config.yaml

- Ruff lint (import sorting with `--fix --select I`)
- Ruff format
- Mypy type check (pass_filenames=false, runs on `src/`)
- Vulture dead code check
- Deptry dependency check
- Pytest unit tests (excludes integration/E2E/scenarios)
