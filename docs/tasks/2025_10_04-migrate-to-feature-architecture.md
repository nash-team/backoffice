# Instruction: Migrate to Feature-Based Architecture (Screaming Architecture)

## Feature

- **Summary**: Refactor codebase from hexagonal architecture to feature-based screaming architecture. Start with generation_costs feature as pilot to validate approach, then migrate remaining features progressively. Apply DDD principles with event-driven communication between bounded contexts.
- **Stack**: `Python 3.11+`, `FastAPI`, `SQLAlchemy (async)`, `PostgreSQL`, `Pydantic`, `pytest`, `pytest-asyncio`

## Existing files

- @src/backoffice/domain/services/token_tracker.py
- @src/backoffice/domain/usecases/get_ebook_costs.py
- @src/backoffice/presentation/templates/costs.html
- @src/backoffice/presentation/routes/dashboard.py
- @src/backoffice/infrastructure/adapters/repositories/ebook_repository.py
- @src/backoffice/domain/entities/ebook.py
- @src/backoffice/domain/ports/pricing_port.py
- @src/backoffice/infrastructure/services/openrouter_service.py

### New files to create

- features/generation_costs/domain/entities/token_usage.py
- features/generation_costs/domain/entities/cost_calculation.py
- features/generation_costs/domain/events/cost_calculated_event.py
- features/generation_costs/domain/events/tokens_consumed_event.py
- features/generation_costs/domain/ports/token_tracker_port.py
- features/generation_costs/domain/ports/cost_calculator_port.py
- features/generation_costs/domain/usecases/calculate_generation_cost_usecase.py
- features/generation_costs/domain/usecases/track_token_usage_usecase.py
- features/generation_costs/infrastructure/adapters/token_tracker_repository.py
- features/generation_costs/infrastructure/models/token_usage_model.py
- features/generation_costs/infrastructure/event_handlers/ebook_generated_handler.py
- features/generation_costs/presentation/routes/costs_routes.py
- features/shared/infrastructure/events/event_bus.py
- features/shared/infrastructure/events/domain_event.py
- features/shared/infrastructure/events/event_handler.py
- tests/features/generation_costs/unit/test_token_tracker.py
- tests/features/generation_costs/integration/test_costs_routes.py
- tests/features/generation_costs/e2e/test_costs_scenarios.py

## Implementation phases

### Phase 1: Setup Event Infrastructure

> Create event bus and domain event abstractions in shared kernel

1. Create `features/shared/infrastructure/events/` directory structure
2. Implement `DomainEvent` base class with event metadata (event_id, occurred_at, aggregate_id)
3. Implement `EventHandler` abstract interface for event subscribers
4. Implement `EventBus` with in-memory publish/subscribe mechanism (sync initially, async later)
5. Add event bus registration to dependency injection container
6. Write unit tests for event bus publish/subscribe behavior

### Phase 2: Create generation_costs Feature Structure

> Extract and migrate token tracking code to new feature bounded context

1. Create feature directory `features/generation_costs/{domain,infrastructure,presentation}` structure
2. Extract `TokenUsage` and `ImageUsage` from token_tracker.py to `features/generation_costs/domain/entities/`
3. Create `CostCalculation` value object in domain/entities for cost aggregation logic
4. Define domain events: `TokensConsumedEvent` (emitted after API call) and `CostCalculatedEvent` (emitted after cost calculation)
5. Create domain ports: `TokenTrackerPort` and `CostCalculatorPort` interfaces
6. Implement use cases: `TrackTokenUsageUseCase` and `CalculateGenerationCostUseCase`
7. Update imports and namespace to use `features.generation_costs.domain`

### Phase 3: Infrastructure Layer for generation_costs

> Implement adapters and persistence for costs feature

1. Create SQLAlchemy model `TokenUsageModel` in `features/generation_costs/infrastructure/models/`
2. Implement `TokenTrackerRepository` adapter implementing `TokenTrackerPort`
3. Migrate cost calculation logic from `token_tracker.py` to repository adapter
4. Create event handler `EbookGeneratedHandler` to listen to generation events and track costs
5. Register event handlers with event bus in infrastructure setup
6. Wire up dependency injection for repositories and handlers

### Phase 4: Presentation Layer for generation_costs

> Migrate costs routes and templates to feature

1. Create `features/generation_costs/presentation/routes/costs_routes.py`
2. Extract `/costs` route from `dashboard.py` to new costs_routes.py
3. Move `costs.html` template to `features/generation_costs/presentation/templates/`
4. Update route registration in main FastAPI app to include costs_routes
5. Update template paths and imports
6. Test costs page rendering with existing data

### Phase 5: Event Integration with Existing Code

> Connect existing generation code to emit events for cost tracking

1. Identify emission points in `OpenRouterImageProvider` after API calls
2. Emit `TokensConsumedEvent` after successful OpenRouter API response
3. Identify emission points in `ColoringBookStrategy` after ebook generation completes
4. Emit `EbookGeneratedEvent` with ebook_id and total cost after generation
5. Verify event handlers receive and process events correctly
6. Add logging for event emission and handling for observability

### Phase 6: Tests Migration

> Reorganize tests by feature structure

1. Create `tests/features/generation_costs/{unit,integration,e2e}` structure
2. Migrate existing token_tracker tests to `tests/features/generation_costs/unit/`
3. Create integration tests for event-driven cost tracking flow
4. Create E2E scenario test for full generation-to-cost-tracking workflow
5. Migrate costs route tests to `tests/features/generation_costs/integration/`
6. Ensure all tests pass with new architecture

### Phase 7: Cleanup and Documentation

> Remove old code and update documentation

1. Delete old token_tracker.py from `domain/services/`
2. Delete old get_ebook_costs.py from `domain/usecases/`
3. Remove costs route from `dashboard.py`
4. Update `CLAUDE.md` with new feature-based architecture documentation
5. Create `features/generation_costs/README.md` with feature context and boundaries
6. Document event contracts and communication patterns
7. Update dependency injection setup documentation

## Reviewed implementation

- [ ] Phase 1: Setup Event Infrastructure
- [ ] Phase 2: Create generation_costs Feature Structure
- [ ] Phase 3: Infrastructure Layer for generation_costs
- [ ] Phase 4: Presentation Layer for generation_costs
- [ ] Phase 5: Event Integration with Existing Code
- [ ] Phase 6: Tests Migration
- [ ] Phase 7: Cleanup and Documentation

## Validation flow

1. Navigate to `/dashboard/costs` page in browser
2. Verify costs page loads with existing cost data displayed correctly
3. Generate a new ebook via dashboard form
4. Verify `TokensConsumedEvent` and `EbookGeneratedEvent` are emitted in logs
5. Verify event handlers process events and update cost tracking
6. Refresh costs page and verify new ebook cost appears in table
7. Run `pytest tests/features/generation_costs/` and verify all tests pass
8. Check that no import errors or broken references exist in codebase
9. Verify total cost calculation matches expected values
10. Generate multiple ebooks and verify cost aggregation works correctly

## Estimations

- **Confidence**: 8/10
  - ✅ Clear bounded context for pilot feature (generation_costs is well isolated)
  - ✅ DDD event-driven patterns are well understood and proven
  - ✅ Existing code is well structured (hexagonal) making extraction easier
  - ✅ Tests exist for migration validation
  - ✅ MVP scope allows for pragmatic approach without over-engineering
  - ❌ Event bus implementation complexity (sync vs async, error handling, retry logic)
  - ❌ Potential circular dependencies during migration if not careful with imports

- **Time to implement**: 6-8 hours
  - Phase 1 (Event infrastructure): 1.5h
  - Phase 2 (Feature structure): 1.5h
  - Phase 3 (Infrastructure): 1.5h
  - Phase 4 (Presentation): 1h
  - Phase 5 (Event integration): 1h
  - Phase 6 (Tests migration): 1h
  - Phase 7 (Cleanup & docs): 0.5h
