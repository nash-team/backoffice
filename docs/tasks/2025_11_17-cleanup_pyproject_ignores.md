# Instruction: Cleanup Obsolete Ruff/Mypy Ignores in pyproject.toml

## Feature

- **Summary**: Remove obsolete lint/type check ignores from pyproject.toml that reference non-existent paths and validate remaining ignores are legitimate
- **Stack**: `Python 3.11`, `Ruff 0.7.1`, `Mypy 1.18.1`

## Existing files

- @pyproject.toml

### New file to create

- None

## Implementation phases

### Phase 1: Remove Obsolete Paths

> Clean configuration by removing ignores for non-existent directories

1. Remove line 108 (Ruff): `"src/backoffice/features/shared/infrastructure/providers/*.py"` - directory does not exist
2. Remove lines 145-146 (Mypy): override for `backoffice.features.shared.infrastructure.providers.*` - module does not exist

### Phase 2: Validate Remaining Ruff Ignores

> Test if S101, F821, E501 ignores are still needed for providers

1. Temporarily remove line 109 ignores: `"src/backoffice/features/ebook/shared/infrastructure/providers/*.py" = ["S101", "F821", "E501"]`
2. Run `ruff check src/backoffice/features/ebook/shared/infrastructure/providers --select S101,F821,E501`
3. Analyze violations:
   - If no violations → remove the ignore entirely
   - If S101 (assert) violations → fix code (replace assert with proper error handling)
   - If F821 (undefined names) violations → fix imports
   - If E501 (line length) violations in docstrings → keep E501 only with updated comment
4. Update pyproject.toml based on findings

### Phase 3: Validate Remaining Mypy Ignores

> Test if mypy overrides are still needed for services, adapters, export

1. Test services override (lines 148-150):
   - Temporarily remove `disable_error_code` for `backoffice.features.shared.infrastructure.services.*`
   - Run `mypy src/backoffice/features/shared/infrastructure/services --show-error-codes`
   - If no errors → remove override
   - If errors are legitimate (external lib stubs missing) → keep with justification comment
   - If errors are fixable → fix code then remove override

2. Test adapters override (lines 152-154):
   - Temporarily remove `disable_error_code` for `backoffice.features.shared.infrastructure.adapters.*`
   - Run `mypy src/backoffice/features/shared/infrastructure/adapters --show-error-codes`
   - Same analysis as services

3. Test ebook export override (lines 156-158):
   - Temporarily remove `disable_error_code` for `backoffice.features.ebook.export.*`
   - Run `mypy src/backoffice/features/ebook/export --show-error-codes`
   - Same analysis as services

### Phase 4: Add Justification Comments

> Document why remaining ignores are kept (if any)

1. For each kept ignore, add inline comment explaining:
   - Technical reason (e.g., "External library X has no type stubs")
   - Why it cannot be fixed (e.g., "Third-party interface incompatibility")
   - Future improvement plan if applicable

2. Replace generic comments with specific ones (e.g., not "Allow asserts" but "Kept for type narrowing in X function")

### Phase 5: Final Validation

> Ensure all checks pass with cleaned configuration

1. Run `make lint` - verify ruff passes
2. Run `make typecheck` - verify mypy passes
3. Run `make test` - verify no regression in tests
4. Commit changes with clean configuration

## Reviewed implementation

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
- [ ] Phase 5

## Validation flow

1. Open pyproject.toml and verify obsolete paths are removed (lines 108, 145-146)
2. Run `ruff check src/backoffice` - should pass without errors
3. Run `mypy src/backoffice` - should pass without errors
4. Check pyproject.toml comments - each remaining ignore has clear justification
5. Run `make precommit` - all hooks pass

## Estimations

- **Confidence**: 10/10
  - ✅ Code already passes all checks (no violations found)
  - ✅ Changes are purely configuration cleanup (low risk)
  - ✅ Clear validation steps with automated checks
  - ✅ No code logic changes needed
  - ✅ Easy rollback if issues (git revert)

- **Time to implement**: 15-20 minutes
  - Phase 1: 2 min (delete 2 lines)
  - Phase 2: 5 min (test ruff ignores)
  - Phase 3: 5 min (test mypy ignores)
  - Phase 4: 3 min (add comments)
  - Phase 5: 5 min (validation)
