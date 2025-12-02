# Instruction: Remove Cost Tracking Feature

## Feature

- **Summary**: Complete removal of generation cost tracking feature to simplify codebase for local/free AI strategy
- **Stack**: `FastAPI 0`, `SQLAlchemy 2`, `Alembic 1`, `PostgreSQL 16`, `Python 3.11+`

## Existing files

### Backend files to modify
- @src/backoffice/main.py
- @src/backoffice/features/ebook/shared/infrastructure/factories/repository_factory.py
- @src/backoffice/features/ebook/shared/infrastructure/providers/provider_factory.py
- @src/backoffice/features/ebook/regeneration/presentation/routes/__init__.py
- @src/backoffice/features/ebook/shared/infrastructure/providers/images/openrouter/openrouter_image_provider.py
- @src/backoffice/features/ebook/creation/domain/strategies/strategy_factory.py
- @src/backoffice/features/shared/infrastructure/database.py

### Frontend files to modify
- @src/backoffice/features/shared/presentation/templates/layouts/base.html
- @src/backoffice/features/shared/presentation/templates/dashboard.html
- @src/backoffice/features/shared/presentation/routes/templates.py

### Files to delete
- @src/backoffice/features/generation_costs/ (entire directory)
- @src/backoffice/features/generation_costs/presentation/templates/costs.html

### New files to create
- New Alembic migration to drop token_usage tables

## Implementation phases

### Phase 1: Preparation and impact analysis

> Identify all integration points before deletion

1. Run grep to find all imports from generation_costs feature
2. List all usages of AsyncRepositoryFactory across codebase
3. Review existing database migrations related to token_usage tables
4. Check frontend templates for cost tracking references

### Phase 2: Remove cost tracking from providers

> Clean provider factory and image providers from cost tracking dependencies

1. Remove track_usage_usecase parameter from ProviderFactory.create_cover_provider()
2. Remove track_usage_usecase parameter from ProviderFactory.create_content_page_provider()
3. Update OpenRouterImageProvider to remove token tracking logic and events
4. Update all calls to provider factory methods (regeneration, creation strategies)

### Phase 3: Convert regeneration to sync repository

> Replace AsyncRepositoryFactory with sync RepositoryFactory in regeneration routes

1. Update regeneration routes to use RepositoryFactoryDep instead of AsyncRepositoryFactoryDep
2. Remove calls to factory.get_track_token_usage_usecase()
3. Update provider instantiation without track_usage_usecase parameter
4. Test regeneration endpoints manually (cover, back_cover, content_page)

### Phase 4: Remove generation_costs backend

> Delete entire bounded context and async infrastructure

1. Delete features/generation_costs/ directory completely
2. Remove generation_costs router imports from main.py
3. Remove costs_pages_router registration from main.py
4. Delete AsyncRepositoryFactory class from repository_factory.py
5. Delete get_async_repository_factory() function
6. Delete get_async_db() and _get_async_engine() from database.py
7. Remove AsyncDatabaseDep type alias

### Phase 5: Remove cost tracking from frontend

> Clean UI templates and navigation from cost tracking references

1. Remove "Coûts de génération" navigation link from base.html (lines 30-35)
2. Remove "Coûts de génération" navigation link from dashboard.html (lines 29-34)
3. Delete costs.html template file
4. Update templates.py if it references costs template directory

### Phase 6: Database migration

> Create migration to drop token_usage tables cleanly

1. Create Alembic migration: alembic revision -m "drop_token_usage_tables"
2. Add downgrade logic to drop tables: token_usage, cost_calculation (if exists)
3. Run migration: make db-migrate
4. Verify tables are removed with psql

### Phase 7: Cleanup and validation

> Ensure no orphaned references and full functionality

1. Search for orphaned imports: grep -r "generation_costs" src/
2. Search for orphaned async DB references: grep -r "get_async_db\|AsyncSession" src/
3. Run unit tests: make test
4. Run smoke test: make test-smoke
5. Start application and verify no import errors: make run
6. Manual test: create ebook, regenerate page, export PDF
7. Update CLAUDE.md to remove generation_costs feature mention
8. Update ARCHITECTURE.md memory bank to reflect sync-only strategy

## Reviewed implementation

- [ ] Phase 1 - Preparation and impact analysis
- [ ] Phase 2 - Remove cost tracking from providers
- [ ] Phase 3 - Convert regeneration to sync repository
- [ ] Phase 4 - Remove generation_costs backend
- [ ] Phase 5 - Remove cost tracking from frontend
- [ ] Phase 6 - Database migration
- [ ] Phase 7 - Cleanup and validation

## Validation flow

1. Start application without errors: make run
2. Create a new ebook via dashboard form
3. Regenerate a content page from detail view
4. Export ebook as PDF (verify file downloads)
5. Check dashboard loads without "Coûts de génération" link
6. Run full test suite: make test && make test-smoke
7. Verify database has no token_usage tables: psql -c "\dt"

## Estimations

- **Confidence**: 9/10
  - ✅ Clear bounded context isolation makes deletion safe
  - ✅ Well-defined integration points (provider_factory, regeneration routes)
  - ✅ Database migration is straightforward (just drop tables)
  - ✅ No complex business logic dependencies on cost tracking
  - ❌ Risk: Missing hidden references in templates or JS (mitigated by grep)

- **Time to implement**: 60-90 minutes
  - Phase 1-2: 15 min (analysis + provider cleanup)
  - Phase 3: 15 min (regeneration sync conversion)
  - Phase 4: 20 min (delete backend + async infrastructure)
  - Phase 5-6: 10 min (frontend + migration)
  - Phase 7: 20-30 min (testing + documentation)
