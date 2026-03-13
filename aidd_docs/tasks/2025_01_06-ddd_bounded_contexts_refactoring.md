# Instruction: DDD Bounded Contexts Refactoring

## Feature

- **Summary**: Restructure codebase into proper DDD Bounded Contexts following Vaughn Vernon principles. Create Ebook bounded context grouping 5 sub-features (creation, export, lifecycle, listing, regeneration) with internal shared kernel. Separate Billing context (generation_costs) communicating via integration events. Minimize global shared kernel to cross-context infrastructure only.
- **Stack**: `Python 3.11, FastAPI 0.104+, SQLAlchemy 2.0+, PostgreSQL (asyncpg), Pydantic 2.4+, Alembic 1.12, Pytest 7.4, Ruff 0.7, Mypy 1.18`

## Existing files

### Features to move into Ebook context
- @src/backoffice/features/ebook/creation
- @src/backoffice/features/ebook/export
- @src/backoffice/features/ebook/lifecycle
- @src/backoffice/features/ebook/listing
- @src/backoffice/features/ebook/regeneration

### Billing context (to isolate)
- @src/backoffice/features/generation_costs

### Current shared (to split)
- @src/backoffice/features/shared

### Application entry point
- @src/backoffice/main.py

### Configuration
- @pyproject.toml
- @pytest.ini

### Documentation
- @ARCHITECTURE.md
- @CLAUDE.md
- @README.md

### New files to create

- src/backoffice/features/ebook/shared/domain/
- src/backoffice/features/ebook/shared/application/ports/
- src/backoffice/features/ebook/shared/infrastructure/
- src/backoffice/features/ebook/creation/application/
- src/backoffice/features/ebook/creation/interface/
- src/backoffice/features/ebook/export/application/
- src/backoffice/features/ebook/export/interface/
- src/backoffice/features/ebook/lifecycle/application/
- src/backoffice/features/ebook/lifecycle/interface/
- src/backoffice/features/ebook/listing/application/
- src/backoffice/features/ebook/listing/interface/
- src/backoffice/features/ebook/listing/infrastructure/read_models/
- src/backoffice/features/ebook/regeneration/application/
- src/backoffice/features/ebook/regeneration/interface/
- src/backoffice/features/generation_costs/shared/domain/
- src/backoffice/features/generation_costs/shared/application/
- src/backoffice/features/generation_costs/shared/infrastructure/
- src/backoffice/features/generation_costs/pricing/application/
- src/backoffice/features/generation_costs/pricing/interface/
- src/backoffice/features/shared/clock/
- src/backoffice/features/shared/id_generation/
- src/backoffice/features/shared/outbox/
- src/backoffice/features/shared/event_bus/
- src/backoffice/features/shared/common_types/
- src/backoffice/features/shared/common_errors/

## Implementation phases

### Phase 1: Preparation & Analysis

> Analyze current structure and map dependencies

1. List all files in each feature to migrate (ebook/creation, ebook/export, ebook/lifecycle, ebook/listing, ebook/regeneration)
2. Map import dependencies between features using grep/rg
3. Identify shared code currently in features/shared/ - categorize as ebook-specific vs cross-context
4. Identify domain events and their consumers
5. Document current event flow between generation_costs and ebook features
6. Prepare git mv commands to preserve file history
7. Create migration checklist with file counts per feature

### Phase 2: Create Target Structure

> Establish new folder hierarchy for bounded contexts

1. Create features/ebook/ root directory
2. Create features/ebook/shared/ with domain, application, infrastructure subdirs
3. Create features/ebook/{creation,export,lifecycle,listing,regeneration}/ directories
4. Create application, interface, tests subdirs for each ebook sub-feature
5. Create features/generation_costs/shared/ structure
6. Create features/generation_costs/pricing/ structure
7. Create minimal shared kernel directories: clock, id_generation, outbox, event_bus, common_types, common_errors

### Phase 3: Move Ebook Shared Domain

> Migrate shared domain models to ebook internal shared

1. Move Ebook aggregate from shared/domain/entities/ to ebook/shared/domain/entities/
2. Move ImagePage entity to ebook/shared/domain/entities/
3. Move ImageSpec, KDPSpec value objects to ebook/shared/domain/value_objects/
4. Move domain services (if any) to ebook/shared/domain/services/
5. Move ebook-related domain events to ebook/shared/domain/events/
6. Move domain exceptions to ebook/shared/domain/exceptions/
7. Update __init__.py files for clean imports

### Phase 4: Move Ebook Shared Infrastructure

> Migrate repositories, models, and infrastructure to ebook context

1. Move SQLAlchemy models (ebook_model.py, image_page_model.py) to ebook/shared/infrastructure/models/
2. Move EbookRepository to ebook/shared/infrastructure/repositories/
3. Move ImagePageRepository to ebook/shared/infrastructure/repositories/
4. Create ebook/shared/application/ports/ and move repository interfaces
5. Move mappers (entity <-> model) to ebook/shared/infrastructure/mappers/
6. Move file storage ports to ebook/shared/application/ports/
7. Update repository imports to use new paths

### Phase 5: Migrate Creation Sub-Feature

> Restructure ebook/creation into hexagonal layers

1. Create ebook/creation/application/commands/ for CreateEbookCommand
2. Move CreateEbookUseCase to ebook/creation/application/handlers/
3. Move creation strategies to ebook/creation/application/strategies/
4. Create ebook/creation/interface/routes/ and move FastAPI routes
5. Create ebook/creation/interface/dtos/ for request/response models
6. Move creation templates to ebook/creation/interface/templates/
7. Move tests to ebook/creation/tests/unit/ and update imports
8. Update all internal imports to new paths
9. Run pytest on creation tests to verify migration

### Phase 6: Migrate Export Sub-Feature

> Restructure ebook/export into hexagonal layers

1. Create ebook/export/application/commands/ for ExportEbookCommand
2. Move export use cases to ebook/export/application/handlers/
3. Move PDF generation service to ebook/export/application/services/
4. Create ebook/export/interface/routes/ and move FastAPI routes
5. Create ebook/export/interface/dtos/
6. Move export templates to ebook/export/interface/templates/
7. Move tests to ebook/export/tests/unit/ and update imports
8. Update all internal imports
9. Run pytest on export tests

### Phase 7: Migrate Lifecycle Sub-Feature

> Restructure ebook/lifecycle into hexagonal layers

1. Create ebook/lifecycle/application/commands/ for ApproveEbook, RejectEbook commands
2. Move lifecycle use cases (approve, reject) to ebook/lifecycle/application/handlers/
3. Create ebook/lifecycle/interface/routes/ and move routes
4. Create ebook/lifecycle/interface/dtos/
5. Move lifecycle templates to ebook/lifecycle/interface/templates/
6. Move tests to ebook/lifecycle/tests/unit/ and update imports
7. Update internal imports
8. Run pytest on lifecycle tests

### Phase 8: Migrate Listing Sub-Feature

> Restructure ebook/listing with CQRS read models

1. Create ebook/listing/application/queries/ for listing queries
2. Move listing query handlers to ebook/listing/application/handlers/
3. Create ebook/listing/infrastructure/read_models/ for projections (if needed)
4. Create ebook/listing/interface/routes/ and move routes
5. Create ebook/listing/interface/dtos/
6. Move listing templates (costs.html) to ebook/listing/interface/templates/
7. Move tests to ebook/listing/tests/unit/ and update imports
8. Update internal imports
9. Run pytest on listing tests

### Phase 9: Migrate Regeneration Sub-Feature

> Restructure ebook/regeneration into hexagonal layers

1. Create ebook/regeneration/application/commands/ for RegeneratePageCommand
2. Move regeneration use cases to ebook/regeneration/application/handlers/
3. Create ebook/regeneration/interface/routes/ and move routes
4. Create ebook/regeneration/interface/dtos/
5. Move regeneration templates to ebook/regeneration/interface/templates/
6. Move tests to ebook/regeneration/tests/unit/ and update imports
7. Update internal imports
8. Run pytest on regeneration tests

### Phase 10: Refactor Billing Context

> Isolate generation_costs as separate bounded context

1. Audit generation_costs for direct imports from ebook features
2. Identify domain events consumed by generation_costs (EbookCreatedEvent, etc)
3. Create generation_costs/shared/domain/entities/ for Cost aggregate
4. Create generation_costs/shared/domain/events/ for cost-related events
5. Move cost tracking logic to generation_costs/pricing/application/handlers/
6. Create event subscribers in generation_costs/pricing/infrastructure/event_handlers/
7. Remove direct ebook imports - replace with integration event handlers
8. Create generation_costs/pricing/interface/routes/
9. Move cost templates to generation_costs/pricing/interface/templates/
10. Update tests and verify no direct ebook dependencies

### Phase 11: Define Integration Events

> Create versioned integration event contracts for cross-context communication

1. Create features/shared/integration_events/ directory
2. Define EbookCreated.v1 integration event schema
3. Define EbookApproved.v1 integration event schema
4. Define EbookRejected.v1 integration event schema
5. Define EbookRegenerated.v1 integration event schema
6. Create event versioning strategy documentation
7. Update ebook context to publish integration events alongside domain events
8. Update billing context to subscribe to integration events only

### Phase 12: Implement Outbox Pattern

> Add outbox for reliable cross-context messaging

1. Create features/shared/outbox/domain/outbox_message.py entity
2. Create features/shared/outbox/infrastructure/outbox_repository.py
3. Create SQLAlchemy model for outbox table in features/shared/outbox/infrastructure/models/
4. Generate Alembic migration for outbox table
5. Implement outbox publisher in ebook context for integration events
6. Implement outbox consumer/relay for dispatching to EventBus
7. Add outbox processing job (cron or background task)
8. Update integration tests to verify outbox behavior

### Phase 13: Clean Shared Kernel

> Reduce shared/ to minimal cross-context infrastructure

1. Move EventBus abstraction to features/shared/event_bus/
2. Create features/shared/clock/ for time utilities (if any)
3. Create features/shared/id_generation/ for ID utilities (if any)
4. Move common error types to features/shared/common_errors/
5. Move common types (primitives, base classes) to features/shared/common_types/
6. Keep authentication in features/shared/auth/ (cross-context infrastructure)
7. Keep static file handling in features/shared/presentation/ (cross-context)
8. Delete empty directories from old shared structure
9. Update all imports from old shared paths to new minimal kernel
10. Verify no business logic remains in shared kernel

### Phase 14: Update Application Bootstrap

> Update main.py and dependency injection

1. Update router imports in main.py for new paths
2. Register ebook sub-feature routes: ebook/creation, ebook/export, ebook/lifecycle, ebook/listing, ebook/regeneration
3. Register billing routes: generation_costs/pricing
4. Update Jinja2 template loader paths for new structure
5. Update static file paths if needed
6. Verify all routes still accessible at same URLs
7. Test application startup without errors

### Phase 15: Update Configuration Files

> Update tool configurations for new structure

1. Update pyproject.toml mypy overrides for new paths
2. Update pyproject.toml ruff per-file-ignores for new paths
3. Update pytest.ini testpaths to include features/ebook/*/tests
4. Update Makefile if any paths are hardcoded
5. Update .gitignore if needed
6. Verify all linting and type checking still passes

### Phase 16: Testing & Validation

> Ensure all tests pass and functionality intact

1. Run all unit tests (177 tests) - fix any import errors
2. Run integration tests (if fixed) - verify DB interactions work
3. Run E2E smoke test - verify health check passes
4. Manual testing: Create ebook workflow
5. Manual testing: Approve/reject ebook workflow
6. Manual testing: Export ebook to PDF
7. Manual testing: Regenerate pages workflow
8. Manual testing: Cost tracking after ebook creation
9. Verify EventBus publishes integration events correctly
10. Verify billing context reacts to ebook events

### Phase 17: Code Quality & Documentation

> Final cleanup and documentation updates

1. Run make lint - fix any new linting issues from refactoring
2. Run make typecheck - fix any type errors from path changes
3. Run make format - ensure consistent formatting
4. Update ARCHITECTURE.md with new bounded context structure
5. Update CLAUDE.md with new file paths and structure examples
6. Update README.md if setup instructions changed
7. Add inline documentation for integration event contracts
8. Add README.md in features/ebook/ explaining bounded context
9. Add README.md in features/generation_costs/ explaining billing context
10. Document cross-context communication patterns

## Reviewed implementation

- [ ] Phase 1: Preparation & Analysis
- [ ] Phase 2: Create Target Structure
- [ ] Phase 3: Move Ebook Shared Domain
- [ ] Phase 4: Move Ebook Shared Infrastructure
- [ ] Phase 5: Migrate Creation Sub-Feature
- [ ] Phase 6: Migrate Export Sub-Feature
- [ ] Phase 7: Migrate Lifecycle Sub-Feature
- [ ] Phase 8: Migrate Listing Sub-Feature
- [ ] Phase 9: Migrate Regeneration Sub-Feature
- [ ] Phase 10: Refactor Billing Context
- [ ] Phase 11: Define Integration Events
- [ ] Phase 12: Implement Outbox Pattern
- [ ] Phase 13: Clean Shared Kernel
- [ ] Phase 14: Update Application Bootstrap
- [ ] Phase 15: Update Configuration Files
- [ ] Phase 16: Testing & Validation
- [ ] Phase 17: Code Quality & Documentation

## Validation flow

1. Start application with make dev
2. Access dashboard at http://localhost:8001
3. Create new ebook via UI - verify creation workflow
4. Check generation_costs reflects cost of ebook creation (integration event worked)
5. Approve ebook via UI - verify lifecycle transition
6. Export ebook to PDF - verify export downloads successfully
7. Regenerate specific page - verify regeneration workflow
8. List all ebooks - verify listing displays correctly
9. Check logs for integration events published
10. Run make test - verify all 177 unit tests pass
11. Run make lint - verify no linting errors
12. Run make typecheck - verify no type errors
13. Verify no direct imports between ebook and generation_costs contexts
14. Review event_bus logs to confirm cross-context communication via events only

## Estimations

- **Confidence**: 7/10 (at planning stage, will increase to 8/10 after Phase 1 analysis, 9/10 after Phase 4 completion)
  - ✅ Clear DDD architecture principles following Vaughn Vernon
  - ✅ Well-defined bounded contexts with clear responsibilities
  - ✅ Existing test coverage (177 tests) will catch regressions
  - ✅ Feature-based structure already in place (easier migration)
  - ✅ FastAPI makes route refactoring straightforward
  - ✅ Git mv preserves file history for traceability
  - ❌ Large-scale refactoring with many import updates (risk of missed imports)
  - ❌ Integration event contracts need careful design (breaking changes possible)
  - ❌ Outbox pattern adds complexity (new infrastructure)
  - ❌ Current integration tests disabled (can't validate DB layer during migration)
  - ❌ Manual testing required for full validation (no comprehensive E2E suite)

- **Time to implement**: 3-5 days
  - Day 1: Phases 1-4 (analysis, structure, shared domain/infrastructure)
  - Day 2: Phases 5-7 (migrate creation, export, lifecycle)
  - Day 3: Phases 8-10 (migrate listing, regeneration, billing refactor)
  - Day 4: Phases 11-15 (integration events, outbox, shared kernel cleanup, config updates)
  - Day 5: Phases 16-17 (testing, validation, documentation, refinement)

**Note**: Confidence will increase to 9/10 after Phase 1 analysis reveals exact file counts and dependency complexity.
