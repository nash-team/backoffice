# Migration Status: Feature-Based Architecture

**Date**: 2025-10-04
**Pilot Feature**: `generation_costs`

## ✅ Completed Phases

### Phase 1: Event Infrastructure ✅
- Created `src/backoffice/features/shared/infrastructure/events/`
- Implemented `DomainEvent` base class with metadata
- Implemented `EventHandler` abstract interface
- Implemented `EventBus` with async publish/subscribe
- Unit tests passing (8/8 tests green)
- **Location**: `src/backoffice/features/shared/`

### Phase 2: Feature Structure ✅
- Created `src/backoffice/features/generation_costs/` structure
- Migrated domain entities: `TokenUsage`, `ImageUsage`, `CostCalculation`
- Created domain events: `TokensConsumedEvent`, `CostCalculatedEvent`
- Created domain ports: `TokenTrackerPort`
- Implemented use cases: `TrackTokenUsageUseCase`, `CalculateGenerationCostUseCase`
- **Location**: `src/backoffice/features/generation_costs/domain/`

### Phase 3: Infrastructure Layer ✅
- Created SQLAlchemy models: `TokenUsageModel`, `ImageUsageModel`
- Implemented `TokenTrackerRepository` adapter
- Created and ran database migration (8d8b2af47db2)
- Tables `token_usages` and `image_usages` created with indexes
- **Location**: `src/backoffice/features/generation_costs/infrastructure/`

## 🚧 Remaining Work

### Phase 4: Presentation Layer (IN PROGRESS)
**Estimated**: 1h

**Tasks**:
1. Create `src/backoffice/features/generation_costs/presentation/routes/costs_routes.py`
2. Extract `/costs` route from `dashboard.py` (lines 526-557)
3. Adapt route to use new `TokenTrackerRepository` instead of `GetEbookCostsUseCase`
4. Update template path to `generation_costs/presentation/templates/costs.html`
5. Register costs_routes in main FastAPI app
6. Test costs page rendering

**Code snippet to migrate**:
```python
@router.get("/costs")
async def get_costs_page(request: Request, factory: RepositoryFactoryDep) -> Response:
    # Use TokenTrackerRepository.get_all_cost_calculations()
    # Instead of GetEbookCostsUseCase
```

### Phase 5: Event Integration (TODO)
**Estimated**: 1h

**Tasks**:
1. Locate emission points in `OpenRouterImageProvider` (after API calls)
2. Inject `EventBus` and `TrackTokenUsageUseCase` into provider
3. Emit `TokensConsumedEvent` after successful API response
4. Locate emission points in `ColoringBookStrategy` (after ebook generation)
5. Emit `CostCalculatedEvent` with final totals
6. Wire up event bus in dependency injection
7. Test event flow end-to-end

**Files to modify**:
- `src/backoffice/infrastructure/services/openrouter_service.py`
- `src/backoffice/application/strategies/coloring_book_strategy.py`
- `src/backoffice/infrastructure/factories/repository_factory.py` (DI)

### Phase 6: Tests Migration (TODO)
**Estimated**: 1h

**Tasks**:
1. Create `tests/backoffice_features/generation_costs/{unit,integration,e2e}/`
2. Migrate existing token_tracker tests from `tests/unit/domain/services/`
3. Create integration tests for event-driven flow
4. Create E2E scenario: generate ebook → verify costs tracked
5. Ensure all tests pass

### Phase 7: Cleanup & Documentation (TODO)
**Estimated**: 0.5h

**Tasks**:
1. Delete `src/backoffice/domain/services/token_tracker.py`
2. Delete `src/backoffice/domain/usecases/get_ebook_costs.py`
3. Remove `/costs` route from `src/backoffice/presentation/routes/dashboard.py`
4. Remove old `costs.html` from `src/backoffice/presentation/templates/`
5. Update `CLAUDE.md` with new architecture section
6. Create `src/backoffice/features/generation_costs/README.md`
7. Verify no broken imports

## 🎯 Next Steps

1. **Complete Phase 4**: Finish presentation layer migration
2. **Implement Phase 5**: Wire up event emission in existing code
3. **Test end-to-end**: Generate ebook → verify events → check costs page
4. **Complete Phases 6-7**: Tests and cleanup

## 📊 Progress

- **Completed**: 3/7 phases (43%)
- **Remaining**: ~3.5 hours estimated
- **Confidence**: 8/10 (architecture validated, implementation straightforward)

## 🔍 Key Decisions

1. ✅ Features located in `src/backoffice/features/` (not root `features/`)
2. ✅ Event bus is simple in-memory async implementation (no external broker needed for MVP)
3. ✅ Domain entities duplicated per feature (DDD bounded context principle)
4. ✅ Tests follow feature structure: `tests/backoffice_features/`

## 🚀 How to Continue

```bash
# 1. Complete presentation layer
# Create costs_routes.py and wire up route

# 2. Test current state
pytest tests/backoffice_features/ -v

# 3. Integrate events
# Modify openrouter_service.py and coloring_book_strategy.py

# 4. Test end-to-end
# Generate ebook and check costs page

# 5. Cleanup old code
# Remove token_tracker.py, get_ebook_costs.py, old routes
```

## 📝 Notes

- Database migration successful (tables created)
- Event bus tests passing (8/8 green)
- No breaking changes to existing code yet (old code still intact)
- Architecture is backward compatible during transition
