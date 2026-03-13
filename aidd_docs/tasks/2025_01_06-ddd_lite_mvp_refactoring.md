# Instruction: DDD-Lite MVP Refactoring

## Feature

- **Summary**: Lightweight DDD refactoring for MVP. Group ebook features under features/ebook/ with clear bounded context. Keep generation_costs separate. Light hexagonal architecture (domain, application, interface). Defer outbox, versioned events, and CQRS until post-MVP.
- **Stack**: `Python 3.11, FastAPI 0.104+, SQLAlchemy 2.0+, PostgreSQL (asyncpg), Pydantic 2.4+, Pytest 7.4, Ruff 0.7`

## Existing files

### Features to group into Ebook context
- @src/backoffice/features/ebook/creation
- @src/backoffice/features/ebook/export
- @src/backoffice/features/ebook/lifecycle
- @src/backoffice/features/ebook/listing
- @src/backoffice/features/ebook/regeneration

### Billing context (keep separate, light cleanup)
- @src/backoffice/features/generation_costs

### Shared (minimal changes - extract ebook-specific code only)
- @src/backoffice/features/shared

### Application entry
- @src/backoffice/main.py

### Configuration
- @pyproject.toml
- @pytest.ini

### Documentation
- @CLAUDE.md
- @ARCHITECTURE.md

### New files to create

- src/backoffice/features/ebook/shared/domain/entities/
- src/backoffice/features/ebook/shared/infrastructure/repositories/
- src/backoffice/features/ebook/shared/infrastructure/models/
- src/backoffice/features/ebook/creation/application/
- src/backoffice/features/ebook/creation/interface/
- src/backoffice/features/ebook/export/application/
- src/backoffice/features/ebook/export/interface/
- src/backoffice/features/ebook/lifecycle/application/
- src/backoffice/features/ebook/lifecycle/interface/
- src/backoffice/features/ebook/listing/application/
- src/backoffice/features/ebook/listing/interface/
- src/backoffice/features/ebook/regeneration/application/
- src/backoffice/features/ebook/regeneration/interface/

## Implementation phases

### Phase 1: Quick Analysis

> Fast assessment of migration scope

1. List all Python files in ebook/creation, ebook/export, ebook/lifecycle, ebook/listing, ebook/regeneration
2. Grep for cross-feature imports to identify dependencies
3. Identify ebook-specific code in shared/domain/ (Ebook, ImagePage entities)
4. Identify ebook-specific code in shared/infrastructure/ (EbookRepository, SQLAlchemy models)
5. Create simple migration checklist with file counts
6. Prepare git mv commands for history preservation

### Phase 2: Create Minimal Structure

> Establish ebook bounded context folders

1. Create features/ebook/ directory
2. Create features/ebook/shared/domain/entities/
3. Create features/ebook/shared/domain/events/
4. Create features/ebook/shared/infrastructure/repositories/
5. Create features/ebook/shared/infrastructure/models/
6. Create features/ebook/{creation,export,lifecycle,listing,regeneration}/ directories
7. Create application/, interface/, tests/ subdirs for each sub-feature

### Phase 3: Migrate Ebook Shared Core

> Move shared ebook domain and infrastructure together

1. Git mv Ebook entity from shared/domain/entities/ to ebook/shared/domain/entities/
2. Git mv ImagePage entity to ebook/shared/domain/entities/
3. Git mv ImageSpec, KDPSpec value objects to ebook/shared/domain/entities/
4. Git mv ebook domain events to ebook/shared/domain/events/
5. Git mv EbookRepository to ebook/shared/infrastructure/repositories/
6. Git mv ImagePageRepository to ebook/shared/infrastructure/repositories/
7. Git mv SQLAlchemy ebook models to ebook/shared/infrastructure/models/
8. Create __init__.py files for clean imports
9. Update imports in moved files to reference new paths

### Phase 4: Migrate Creation Sub-Feature

> Move ebook/creation into ebook/creation/

1. Create ebook/creation/application/usecases/ directory
2. Git mv creation use cases to ebook/creation/application/usecases/
3. Git mv creation strategies to ebook/creation/application/strategies/ (if any)
4. Create ebook/creation/interface/routes/
5. Git mv creation routes to ebook/creation/interface/routes/
6. Git mv creation templates to ebook/creation/interface/templates/ (if any)
7. Git mv creation DTOs to ebook/creation/interface/dtos/ (if any)
8. Git mv tests to ebook/creation/tests/unit/
9. Update all imports in moved files
10. Run pytest ebook/creation/tests/ to verify migration

### Phase 5: Migrate Export Sub-Feature

> Move ebook/export into ebook/export/

1. Create ebook/export/application/usecases/
2. Git mv export use cases to ebook/export/application/usecases/
3. Git mv PDF generation services to ebook/export/application/services/ (if separate)
4. Create ebook/export/interface/routes/
5. Git mv export routes to ebook/export/interface/routes/
6. Git mv export templates to ebook/export/interface/templates/
7. Git mv tests to ebook/export/tests/unit/
8. Update imports
9. Run pytest ebook/export/tests/

### Phase 6: Migrate Lifecycle Sub-Feature

> Move ebook/lifecycle into ebook/lifecycle/

1. Create ebook/lifecycle/application/usecases/
2. Git mv lifecycle use cases (approve, reject) to ebook/lifecycle/application/usecases/
3. Create ebook/lifecycle/interface/routes/
4. Git mv lifecycle routes to ebook/lifecycle/interface/routes/
5. Git mv lifecycle templates to ebook/lifecycle/interface/templates/
6. Git mv tests to ebook/lifecycle/tests/unit/
7. Update imports
8. Run pytest ebook/lifecycle/tests/

### Phase 7: Migrate Listing Sub-Feature

> Move ebook/listing into ebook/listing/

1. Create ebook/listing/application/queries/ (or usecases/)
2. Git mv listing queries to ebook/listing/application/queries/
3. Create ebook/listing/interface/routes/
4. Git mv listing routes to ebook/listing/interface/routes/
5. Git mv listing templates (costs.html) to ebook/listing/interface/templates/
6. Git mv tests to ebook/listing/tests/unit/
7. Update imports
8. Run pytest ebook/listing/tests/
9. Note: No CQRS read models for MVP - use repository queries directly

### Phase 8: Migrate Regeneration Sub-Feature

> Move ebook/regeneration into ebook/regeneration/

1. Create ebook/regeneration/application/usecases/
2. Git mv regeneration use cases to ebook/regeneration/application/usecases/
3. Create ebook/regeneration/interface/routes/
4. Git mv regeneration routes to ebook/regeneration/interface/routes/
5. Git mv regeneration templates to ebook/regeneration/interface/templates/
6. Git mv tests to ebook/regeneration/tests/unit/
7. Update imports
8. Run pytest ebook/regeneration/tests/

### Phase 9: Light Billing Cleanup

> Verify generation_costs isolation (no deep refactor needed)

1. Grep for imports from ebook features in generation_costs/
2. If direct aggregate imports exist, replace with repository queries or keep event handlers
3. Verify generation_costs subscribes to ebook domain events (OK for MVP)
4. No need for integration events or outbox pattern yet
5. Run pytest generation_costs tests

### Phase 10: Update Application & Config

> Wire everything together and validate

1. Update main.py router imports to use new ebook/* paths
2. Register all sub-feature routes (ebook.creation, ebook.export, etc.)
3. Verify routes still accessible at original URLs
4. Update pyproject.toml mypy overrides for new paths
5. Update pyproject.toml ruff ignores if needed
6. Update pytest.ini testpaths to include features/ebook/*/tests
7. Update Jinja2 template loader in shared/presentation/routes/templates.py
8. Test application startup - verify no import errors

### Phase 11: Testing & Validation

> Ensure everything works

1. Run make test - all 177 unit tests should pass
2. Fix any import errors discovered
3. Run make lint - fix any new issues
4. Run make typecheck - fix type errors from path changes
5. Run make format
6. Manual test: Start app with make dev
7. Manual test: Create ebook workflow
8. Manual test: Approve/reject ebook
9. Manual test: Export ebook to PDF
10. Manual test: List ebooks
11. Manual test: Regenerate page
12. Manual test: Verify costs tracked after ebook creation

### Phase 12: Documentation

> Update docs to reflect new structure

1. Update CLAUDE.md with new structure (features/ebook/*)
2. Update CLAUDE.md import examples
3. Update ARCHITECTURE.md with DDD-Lite bounded context explanation
4. Add brief comment: "Post-MVP: outbox, versioned events, CQRS read models"
5. Update README.md if setup changed (likely no changes needed)

## Reviewed implementation

- [ ] Phase 1: Quick Analysis
- [ ] Phase 2: Create Minimal Structure
- [ ] Phase 3: Migrate Ebook Shared Core
- [ ] Phase 4: Migrate Creation Sub-Feature
- [ ] Phase 5: Migrate Export Sub-Feature
- [ ] Phase 6: Migrate Lifecycle Sub-Feature
- [ ] Phase 7: Migrate Listing Sub-Feature
- [ ] Phase 8: Migrate Regeneration Sub-Feature
- [ ] Phase 9: Light Billing Cleanup
- [ ] Phase 10: Update Application & Config
- [ ] Phase 11: Testing & Validation
- [ ] Phase 12: Documentation

## Validation flow

1. Start application: make dev
2. Access dashboard: http://localhost:8001
3. Create new ebook - verify workflow works
4. Check generation_costs shows cost (event handler works)
5. Approve ebook - verify lifecycle works
6. Export ebook to PDF - verify download
7. List ebooks - verify display
8. Regenerate page - verify regeneration
9. Run make test - verify 177 tests pass
10. Run make lint - verify no errors
11. Run make typecheck - verify no type errors
12. Check imports: no features/ebook_* paths remain (all use features/ebook/*)

## Estimations

- **Confidence**: 8/10 (at planning stage, will increase to 9/10 after Phase 3 completion)
  - ✅ Simplified scope (no outbox, no integration events, no CQRS)
  - ✅ Clear DDD boundaries without heavyweight infrastructure
  - ✅ Existing test coverage (177 tests) catches regressions
  - ✅ Feature-based structure already exists (easier migration)
  - ✅ Git mv preserves history
  - ✅ Minimal shared/ changes (less disruption)
  - ❌ Import updates still require care (but fewer architectural changes)
  - ❌ Integration tests disabled (rely on manual testing)

- **Time to implement**: 1-2 days MAX
  - Day 1 (4-6h): Phases 1-6 (analysis, structure, shared core, creation, export, lifecycle)
  - Day 2 (2-4h): Phases 7-12 (listing, regeneration, billing, config, testing, docs)

**Note**: Much faster than full DDD (3-5 days). Post-MVP refactoring can add outbox, versioned events, CQRS when needed.
