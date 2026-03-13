# Instruction: Group Ebook Features Under features/ebook/

## Feature

- **Summary**: Simple folder reorganization. Move 5 ebook features (creation, export, lifecycle, listing, regeneration) under features/ebook/. Update imports. No architectural changes, no outbox, no events, no CQRS, no billing refactor. Pure MVP.
- **Stack**: `Python 3.11, FastAPI 0.104+, SQLAlchemy 2.0+, Pytest 7.4, Ruff 0.7`

## Existing files

### Features to move
- @src/backoffice/features/ebook/creation → ebook/creation
- @src/backoffice/features/ebook/export → ebook/export
- @src/backoffice/features/ebook/lifecycle → ebook/lifecycle
- @src/backoffice/features/ebook/listing → ebook/listing
- @src/backoffice/features/ebook/regeneration → ebook/regeneration

### Keep unchanged
- @src/backoffice/features/generation_costs (no changes)
- @src/backoffice/features/shared (no changes for MVP)

### Application & config
- @src/backoffice/main.py
- @pyproject.toml
- @pytest.ini

### Documentation
- @CLAUDE.md
- @ARCHITECTURE.md

### New files to create

- src/backoffice/features/ebook/creation/ (moved from ebook/creation)
- src/backoffice/features/ebook/export/ (moved from ebook/export)
- src/backoffice/features/ebook/lifecycle/ (moved from ebook/lifecycle)
- src/backoffice/features/ebook/listing/ (moved from ebook/listing)
- src/backoffice/features/ebook/regeneration/ (moved from ebook/regeneration)
- src/backoffice/features/ebook/shared/ (optional, can stay empty for MVP)

## Implementation phases

### Phase 1: Quick Analysis

> Count files and prepare migration

1. Count Python files in each ebook_* feature
2. Grep for imports between ebook_* features to understand dependencies
3. Check if generation_costs imports from ebook_* (tolerated for MVP)
4. Prepare git mv commands list

### Phase 2: Create Ebook Parent Folder

> Establish features/ebook/ directory

1. Create src/backoffice/features/ebook/ directory
2. Create src/backoffice/features/ebook/shared/ (can be empty for MVP)
3. Create __init__.py in features/ebook/

### Phase 3: Move Creation Feature

> Git mv ebook/creation to ebook/creation

1. Git mv src/backoffice/features/ebook/creation src/backoffice/features/ebook/creation
2. Find all imports referencing ebook/creation: rg "from.*ebook/creation" -l
3. Replace imports: features.ebook/creation → features.ebook.creation
4. Update main.py router import for creation
5. Run pytest features/ebook/creation/tests/ to verify

### Phase 4: Move Export Feature

> Git mv ebook/export to ebook/export

1. Git mv src/backoffice/features/ebook/export src/backoffice/features/ebook/export
2. Find imports: rg "from.*ebook/export" -l
3. Replace imports: features.ebook/export → features.ebook.export
4. Update main.py router import for export
5. Run pytest features/ebook/export/tests/

### Phase 5: Move Lifecycle Feature

> Git mv ebook/lifecycle to ebook/lifecycle

1. Git mv src/backoffice/features/ebook/lifecycle src/backoffice/features/ebook/lifecycle
2. Find imports: rg "from.*ebook/lifecycle" -l
3. Replace imports: features.ebook/lifecycle → features.ebook.lifecycle
4. Update main.py router import for lifecycle
5. Run pytest features/ebook/lifecycle/tests/

### Phase 6: Move Listing Feature

> Git mv ebook/listing to ebook/listing

1. Git mv src/backoffice/features/ebook/listing src/backoffice/features/ebook/listing
2. Find imports: rg "from.*ebook/listing" -l
3. Replace imports: features.ebook/listing → features.ebook.listing
4. Update main.py router import for listing
5. Run pytest features/ebook/listing/tests/

### Phase 7: Move Regeneration Feature

> Git mv ebook/regeneration to ebook/regeneration

1. Git mv src/backoffice/features/ebook/regeneration src/backoffice/features/ebook/regeneration
2. Find imports: rg "from.*ebook/regeneration" -l
3. Replace imports: features.ebook/regeneration → features.ebook.regeneration
4. Update main.py router import for regeneration
5. Run pytest features/ebook/regeneration/tests/

### Phase 8: Update Configuration Files

> Update tool configs for new paths

1. Update pyproject.toml mypy overrides: ebook/export → ebook.export
2. Update pyproject.toml ruff ignores if any reference old paths
3. Update pytest.ini testpaths if explicit (likely auto-discovers)
4. Update Jinja2 template loader paths in shared/presentation/routes/templates.py
5. Verify no hardcoded paths in Makefile

### Phase 9: Full Testing & Validation

> Ensure everything works

1. Run make test - all 177 unit tests should pass
2. Search for remaining old imports: rg "features\.ebook_(creation|export|lifecycle|listing|regeneration)"
3. Fix any missed imports
4. Run make lint
5. Run make typecheck
6. Run make format
7. Manual test: make dev - verify app starts
8. Manual test: Create ebook - verify workflow
9. Manual test: Export ebook - verify PDF download
10. Manual test: List ebooks - verify display
11. Manual test: Approve ebook - verify lifecycle
12. Manual test: Regenerate page - verify regeneration

### Phase 10: Documentation Update

> Update docs to reflect new structure

1. Update CLAUDE.md: change all examples from ebook/creation to ebook/creation
2. Update CLAUDE.md: update import examples
3. Update ARCHITECTURE.md: mention features/ebook/ grouping
4. Add note: "Post-MVP: move ebook entities to ebook/shared/, add outbox, versioned events"
5. Update README.md if any paths referenced (likely none)

## Reviewed implementation

- [ ] Phase 1: Quick Analysis
- [ ] Phase 2: Create Ebook Parent Folder
- [ ] Phase 3: Move Creation Feature
- [ ] Phase 4: Move Export Feature
- [ ] Phase 5: Move Lifecycle Feature
- [ ] Phase 6: Move Listing Feature
- [ ] Phase 7: Move Regeneration Feature
- [ ] Phase 8: Update Configuration Files
- [ ] Phase 9: Full Testing & Validation
- [ ] Phase 10: Documentation Update

## Validation flow

1. Start application: make dev
2. Verify app starts without errors
3. Access dashboard: http://localhost:8001
4. Create new ebook - full workflow works
5. Approve ebook - lifecycle works
6. Export ebook to PDF - download works
7. List ebooks - display works
8. Regenerate page - regeneration works
9. Run make test - 177 tests pass
10. Run make lint - no errors
11. Run make typecheck - no errors
12. Search codebase: rg "ebook_(creation|export|lifecycle|listing|regeneration)" - no matches in imports

## Estimations

- **Confidence**: 9/10 (high confidence - simple folder move)
  - ✅ No architectural changes (just folder reorganization)
  - ✅ Git mv preserves history
  - ✅ Simple find/replace for imports
  - ✅ Tests validate after each move
  - ✅ Existing 177 tests catch regressions
  - ✅ No billing refactor (zero risk)
  - ✅ No shared cleanup (zero risk)
  - ❌ Import updates require care (but easily verified with grep)

- **Time to implement**: 4-6 hours (can be done in one session)
  - Phase 1: 30 min (analysis)
  - Phases 2-7: 2-3h (moves + import updates, ~30min per feature)
  - Phase 8: 30 min (config updates)
  - Phase 9: 1-1.5h (testing)
  - Phase 10: 30 min (docs)

**Post-MVP improvements** (deferred):
- Move Ebook, ImagePage entities to ebook/shared/domain/
- Move ebook repositories to ebook/shared/infrastructure/
- Add integration events for billing context
- Add outbox pattern
- Add CQRS read models if performance needed
- Clean up features/shared/ to minimal kernel
