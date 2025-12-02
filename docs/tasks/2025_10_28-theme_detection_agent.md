# Instruction: TrendScout Agent - Automated Theme Detection from Amazon Best Sellers

## Feature

- **Summary**: Implement TrendScout autonomous agent (Phase 1 of autonomous ebook generation pipeline) that analyzes Amazon KDP coloring book best sellers, filters viable themes, verifies uniqueness against existing themes, and generates versioned theme configuration files with AI-generated palettes and prompts.
- **Stack**: `Python 3.11`, `FastAPI`, `Amazon PA-API 5.0`, `OpenAI API`, `PyYAML 6.0`, `httpx 0.25.1`, `Pydantic 2.4.2`

## Existing files

- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/themes/dinosaurs.yml
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/themes/pirates.yml
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/themes/unicorns.yml
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/themes/schema.json
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/Makefile
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/pyproject.toml
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/src/backoffice/features/shared/infrastructure/providers/
- @/Users/blacksun/Dev/sandbox/IA/generatorEbook/backoffice/src/backoffice/features/ebook/

### New files to create

- src/backoffice/features/autonomous_generation/__init__.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/entities/catalog_item.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/entities/detected_theme.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/entities/existing_theme.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/ports/catalog_port.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/ports/theme_repository_port.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/ports/theme_content_generator_port.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/services/theme_filter_service.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/services/theme_existence_checker.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/services/theme_scoring_service.py
- src/backoffice/features/autonomous_generation/domain/subdomains/theme_detection/usecases/detect_trending_theme_usecase.py
- src/backoffice/features/autonomous_generation/infrastructure/adapters/paapi_catalog_adapter.py
- src/backoffice/features/autonomous_generation/infrastructure/repositories/yaml_theme_repository.py
- src/backoffice/features/autonomous_generation/infrastructure/providers/openai_theme_generator_provider.py
- src/backoffice/features/autonomous_generation/infrastructure/prompts/palette_generation.txt
- src/backoffice/features/autonomous_generation/infrastructure/prompts/prompt_blocks_generation.txt
- src/backoffice/features/autonomous_generation/application/agents/trendscout_agent.py
- src/backoffice/features/autonomous_generation/application/cli_orchestrator.py
- src/backoffice/features/autonomous_generation/cli.py
- src/backoffice/features/autonomous_generation/tests/unit/fakes/fake_catalog_port.py
- src/backoffice/features/autonomous_generation/tests/unit/fakes/fake_theme_repository.py
- src/backoffice/features/autonomous_generation/tests/unit/fakes/fake_theme_content_generator.py
- src/backoffice/features/autonomous_generation/tests/unit/domain/subdomains/theme_detection/services/test_theme_filter_service.py
- src/backoffice/features/autonomous_generation/tests/unit/domain/subdomains/theme_detection/services/test_theme_existence_checker.py
- src/backoffice/features/autonomous_generation/tests/unit/domain/subdomains/theme_detection/services/test_theme_scoring_service.py
- src/backoffice/features/autonomous_generation/tests/unit/domain/subdomains/theme_detection/usecases/test_detect_trending_theme_usecase.py
- src/backoffice/features/autonomous_generation/tests/unit/application/agents/test_trendscout_agent.py

## Implementation phases

### Phase 1: Setup Amazon PA-API Infrastructure with Generic Catalog Port

> Configure Amazon Product Advertising API with provider-agnostic domain abstraction

1. Add `python-amazon-paapi>=5.1.0` dependency to `pyproject.toml` under `dependencies` section
2. Create feature structure: `features/autonomous_generation/{domain/subdomains/theme_detection,infrastructure,application,tests}` with all subdirectories
3. Create `CatalogItem` value object (Pydantic model) in `domain/subdomains/theme_detection/entities/` with fields: `asin: str`, `title: str`, `rank: int`, `reviews_count: int | None`, `rating: float | None` (handle missing data gracefully)
4. Create `CatalogPort` abstract interface in `domain/subdomains/theme_detection/ports/` with method `search_coloring_books(top_n: int) -> list[CatalogItem]` (no vendor name in port, no PA-API types leak)
5. Implement `PAAPICatalogAdapter` in `infrastructure/adapters/` implementing `CatalogPort`, mapping PA-API response to `CatalogItem` value objects (handle None for rating/reviews), using env vars `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, `AMAZON_PARTNER_TAG`
6. Test API connection with query "coloring book" and verify response maps correctly to `CatalogItem` value objects with None handling

### Phase 2: Theme Repository Port with YAML Implementation

> Decouple domain from file system with repository abstraction

1. Create `ExistingTheme` value object (Pydantic model) in `domain/subdomains/theme_detection/entities/` with fields: `id: str`, `label: str`, `keywords: list[str]` (extracted from label, normalized)
2. Create `ThemeRepositoryPort` interface in `domain/subdomains/theme_detection/ports/` with methods: `list_all() -> list[ExistingTheme]`, `save(theme_data: dict, theme_id: str) -> str`
3. Implement `YamlThemeRepository` in `infrastructure/repositories/` reading from `themes/` directory, parsing `*.yml` files, extracting `id` and `label` fields only
4. Implement keyword extraction in repository: lowercase label, remove stop words (the, a, for, book, coloring), split by spaces/special chars, return as list
5. Implement `save()` method with filename sanitization (lowercase, underscores, `.yml`) and YAML writing with `safe_dump(default_flow_style=False, sort_keys=False)`
6. Test repository with existing themes (dinosaurs, pirates, unicorns) and verify `list_all()` returns `ExistingTheme` value objects with correct keywords

### Phase 3: Theme Filtering Service with Null Safety

> Filter catalog items by business criteria handling missing data gracefully

1. Create `ThemeFilterService` in `domain/subdomains/theme_detection/services/` with method `filter_viable_themes(items: list[CatalogItem]) -> list[CatalogItem]`
2. Implement hardcoded filter criteria: `rank <= 10`, `reviews_count is not None and reviews_count >= 50`, `rating is not None and rating >= 4.0`
3. Skip items with None rating or reviews_count (log skipped items at debug level if needed)
4. Return filtered list sorted by rank ascending (best sellers first)
5. Write 3 unit tests: (i) item with reviews_count=30 is filtered out, (ii) item with rating=3.5 is filtered out, (iii) verify Top 10 limit and rank sorting

### Phase 4: Theme Detection Use Case (Core Business Logic)

> Orchestrate theme detection workflow in use case (not in CLI/agent)

1. Create `DetectedTheme` value object (Pydantic model) in `domain/subdomains/theme_detection/entities/` with fields: `catalog_item: CatalogItem`, `keywords: list[str]`, `novelty_score: float`, `combined_score: float`
2. Create `DetectTrendingThemeUseCase` in `domain/subdomains/theme_detection/usecases/` injecting: `catalog_port: CatalogPort`, `theme_repository: ThemeRepositoryPort`, `filter_service: ThemeFilterService`
3. Implement `execute() -> DetectedTheme | None` method orchestrating: fetch items → filter → extract keywords → check duplicates → return None if all duplicates, else return best non-duplicate
4. Keep use case focused on business logic: NO logging, NO file I/O, NO API calls (those belong in agent/infrastructure)
5. Write 2 unit tests with fakes: (i) returns best theme when candidates exist, (ii) returns None when no viable candidates after filtering

### Phase 5: Duplicate Detection with Repository Port

> Prevent creating themes that already exist using keyword matching

1. Create `ThemeExistenceChecker` service in `domain/subdomains/theme_detection/services/` injecting `ThemeRepositoryPort` with method `is_duplicate(keywords: list[str]) -> bool`
2. Implement keyword matching: load existing themes via `theme_repository.list_all()`, compare incoming keywords with each `ExistingTheme.keywords`
3. Calculate Jaccard similarity: `intersection_size / union_size`, mark as duplicate if similarity >= 0.5 (50% threshold)
4. Return `True` if any existing theme matches threshold, `False` otherwise
5. Write 3 unit tests with `FakeThemeRepository`: (i) exact keyword match returns True, (ii) 60% similarity returns True, (iii) 40% similarity returns False

### Phase 6: Multi-Factor Theme Scoring Service

> Rank themes by combining sales rank, reviews, rating, and novelty

1. Create `ThemeScoringService` in `domain/subdomains/theme_detection/services/` injecting `ThemeRepositoryPort` with method `score_theme(item: CatalogItem, keywords: list[str]) -> float`
2. Implement scoring formula: `score = 0.4 * (10 - rank) / 10 + 0.3 * min(reviews / 200, 1.0) + 0.2 * rating / 5.0 + 0.1 * novelty` (hardcoded weights for MVP)
3. Calculate novelty: load existing themes, compute max Jaccard similarity with all existing, novelty = `1.0 - max_similarity` (1.0 = new, 0.0 = duplicate)
4. Handle None values: if rating or reviews_count is None, use 0.0 for that component (item should have been filtered already, but defensive)
5. Write 2 unit tests with fixed inputs: (i) theme with rank=1, reviews=100, rating=4.5, novelty=0.8 → verify expected score, (ii) verify novelty calculation with known existing themes
6. Update `DetectTrendingThemeUseCase` to use scoring service: score all filtered non-duplicate themes, return highest scored as `DetectedTheme`

### Phase 7: AI-Powered Theme Content Generation

> Generate color palette and prompt blocks using OpenAI based on detected theme

1. Create `ThemeContentGeneratorPort` interface in `domain/subdomains/theme_detection/ports/` with method `generate_palette_and_prompts(theme_name: str) -> dict`
2. Implement `OpenAIThemeGeneratorProvider` in `infrastructure/providers/` reusing existing OpenAI client initialization pattern from `features/shared/infrastructure/providers/`
3. Create `infrastructure/prompts/palette_generation.txt`: system prompt requesting JSON output with `base: list[str]` (3 hex colors), `accents_allowed: list[str]`, `forbidden_keywords: list[str]` matching existing theme format
4. Create `infrastructure/prompts/prompt_blocks_generation.txt`: system prompt for generating `subject`, `environment`, `tone`, `positives: list[str]`, `negatives: list[str]`
5. Validate response structure with Pydantic model (ensure all required fields present, hex colors valid format)
6. Test generation for "Underwater Ocean" theme and validate output matches existing `pirates.yml` structure

### Phase 8: Versioned Theme YAML Persistence

> Write detected theme to themes/ directory with versioning and source tracking

1. Update `YamlThemeRepository.save()` method to compose complete versioned YAML structure
2. Add metadata fields at top: `schema_version: 1`, `source_provider: "paapi"` (enables future migration and multi-source support)
3. Compose full structure: `schema_version`, `source_provider`, `id` (sanitized), `label` (original), `amazon_metadata` (asin, rank, reviews_count, rating, title, detected_at ISO date), `palette`, `prompt_blocks`
4. Use PyYAML `safe_dump` with `default_flow_style=False`, `sort_keys=False` for readable output preserving field order
5. Write unit test verifying generated YAML matches structure of existing themes and includes new versioning fields

### Phase 9: TrendScout Agent Orchestration (Thin Layer)

> Create autonomous agent orchestrating workflow with logging (business logic stays in use case)

1. Create `TrendScoutAgent` class in `application/agents/trendscout_agent.py` with method `run() -> dict | None`
2. Inject dependencies: `use_case: DetectTrendingThemeUseCase`, `content_generator: ThemeContentGeneratorPort`, `theme_repository: ThemeRepositoryPort`
3. Implement thin orchestration: call `use_case.execute()` → if None, log "No new themes found" and return None → else generate content → save via repository → log success → return result dict
4. Add structured logging ONLY in agent (not in use case): "Starting detection", "X candidates found", "Best theme: Y (score: Z)", "Theme saved: themes/X.yml"
5. Handle exceptions: catch and log errors from infrastructure (API, file I/O), return None gracefully

### Phase 10: CLI with Dependency Injection

> Wire dependencies and create manual CLI entry point

1. Create `cli_orchestrator.py` in `application/` with function `build_trendscout_agent() -> TrendScoutAgent` performing dependency injection
2. Instantiate infrastructure components: `PAAPICatalogAdapter` (with env vars), `YamlThemeRepository` (with `themes/` path), `OpenAIThemeGeneratorProvider`
3. Instantiate domain services: `ThemeFilterService`, `ThemeExistenceChecker` (inject repository), `ThemeScoringService` (inject repository)
4. Instantiate use case: `DetectTrendingThemeUseCase` (inject catalog_port, theme_repository, filter_service)
5. Wire into agent: `TrendScoutAgent` (inject use_case, content_generator, theme_repository)
6. Create `cli.py` with `async def main()` calling `build_trendscout_agent().run()` and printing result
7. Add Makefile target: `detect-themes: $(PY) -m backoffice.features.autonomous_generation.cli`

### Phase 11: MVP Unit Tests (Simple but Essential)

> Test critical business logic with minimal but effective test coverage

1. Create `FakeCatalogPort` in `tests/unit/fakes/` returning list of mock `CatalogItem` with configurable data
2. Create `FakeThemeRepository` in `tests/unit/fakes/` with in-memory `list[ExistingTheme]` and `save()` tracking calls
3. Create `FakeThemeContentGenerator` returning predefined palette and prompt_blocks
4. Test `ThemeFilterService` with 3 cases: (i) reviews_count < 50 filtered out, (ii) rating < 4.0 filtered out, (iii) verify Top 10 sorting by rank
5. Test `ThemeScoringService` with 1 case: fixed inputs (rank=2, reviews=150, rating=4.5, novelty=0.7) → verify expected score formula
6. Test `DetectTrendingThemeUseCase` with 2 cases: (i) fakes return candidates → use case returns best `DetectedTheme`, (ii) all candidates are duplicates → use case returns None
7. Test `ThemeExistenceChecker` with 3 cases: (i) exact match, (ii) 60% similarity, (iii) 30% similarity
8. Run `make test-unit` and verify all new tests pass (177 → 185+ tests)

## Critical Pitfalls to Avoid (MVP)

### Pitfall 1: PA-API Types Leaking into Domain
- **DON'T**: Pass PA-API response objects directly to domain services
- **DO**: Map PA-API responses to `CatalogItem` value objects in adapter boundary
- **Validation**: Domain layer has zero imports from `python-amazon-paapi` package

### Pitfall 2: Business Logic in CLI/Agent
- **DON'T**: Put filtering, scoring, duplicate detection logic in `TrendScoutAgent` or `cli.py`
- **DO**: Keep agent thin (orchestration + logging only), all business logic in use case + services
- **Validation**: Agent methods are < 30 lines, use case contains complex logic

### Pitfall 3: Missing None Handling for rating/reviews_count
- **DON'T**: Assume rating and reviews_count are always present
- **DO**: Define fields as `int | None` and `float | None` in `CatalogItem`, handle in filter service
- **Validation**: Test with `CatalogItem` having `rating=None` does not crash, item is filtered out

### Pitfall 4: Cross-Context Imports
- **DON'T**: Import from `features/ebook/` into `features/autonomous_generation/`
- **DO**: Keep bounded contexts isolated, create shared-kernel if truly needed (not for MVP)
- **Validation**: Run `grep -r "from backoffice.features.ebook" src/backoffice/features/autonomous_generation/` returns empty

## Reviewed implementation

- [ ] Phase 1: Generic `CatalogPort` abstraction, no PA-API types in domain, None handling for rating/reviews
- [ ] Phase 2: `ThemeRepositoryPort` decouples domain from file system, keyword extraction works
- [ ] Phase 3: Theme filtering handles None values gracefully, 3 unit tests pass (reviews, rating, sorting)
- [ ] Phase 4: Use case contains core business logic (not in agent), returns None when no candidates
- [ ] Phase 5: Duplicate detection uses Jaccard similarity (threshold 0.5), 3 unit tests pass
- [ ] Phase 6: Scoring formula implemented with fixed weights, 2 unit tests pass with known inputs
- [ ] Phase 7: AI generates valid palette and prompts matching existing YAML format
- [ ] Phase 8: YAML includes `schema_version: 1` and `source_provider: "paapi"`
- [ ] Phase 9: Agent is thin orchestration layer (< 30 lines), logging only in agent (not use case)
- [ ] Phase 10: CLI orchestrator performs dependency injection, `make detect-themes` works
- [ ] Phase 11: 8+ MVP unit tests pass (filter, scoring, use case, existence checker)
- [ ] Pitfall validation: No PA-API types in domain, no business logic in agent, None handling works, no cross-context imports

## Validation flow

1. Developer sets environment variables in `.env`: `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, `AMAZON_PARTNER_TAG`, `OPENAI_API_KEY`
2. Developer runs `make detect-themes` from terminal
3. System logs: "TrendScout Agent starting theme detection"
4. System logs: "Fetching Top 10 coloring books via CatalogPort"
5. System logs: "Retrieved 10 catalog items, filtering viable candidates"
6. System logs: "7 candidates passed filtering (rank <= 10, reviews >= 50, rating >= 4.0)"
7. System logs: "Loading existing themes from repository"
8. System logs: "4 existing themes found (dinosaurs, pirates, unicorns, neutral-default)"
9. System logs: "Checking for duplicates using Jaccard similarity (threshold: 0.5)"
10. System logs: "3 themes are duplicates, 4 new candidates remain"
11. System logs: "Scoring 4 candidates using multi-factor formula"
12. System logs: "Best theme selected: 'Underwater Ocean Animals' (score: 0.87, novelty: 0.92)"
13. System logs: "Generating palette and prompts with OpenAI"
14. System logs: "Content generated successfully"
15. System logs: "Saving theme to repository"
16. System logs: "Theme saved: themes/underwater_ocean_animals.yml (schema_version: 1, source_provider: paapi)"
17. Developer opens `themes/underwater_ocean_animals.yml` and verifies structure includes versioning fields
18. Developer runs `make test-unit` and all 185+ tests pass including MVP autonomous_generation tests
19. Developer triggers detection again and system logs "All themes are duplicates, no new theme created"
20. Developer verifies no imports from `features/ebook/` exist in `features/autonomous_generation/` (bounded context isolation)

## Estimations

- **Confidence**: 9/10
  - ✅ Clear requirements with explicit thresholds (Top 10, 50 reviews, 4.0 rating)
  - ✅ Value objects prevent type leakage and improve safety
  - ✅ Repository port enables testing and future database migration
  - ✅ Generic CatalogPort prepares for Keepa without domain changes
  - ✅ Versioned YAML enables future migration
  - ✅ None handling prevents runtime crashes
  - ✅ Thin agent keeps business logic in use case (testable)
  - ✅ MVP tests focus on critical paths (filter, scoring, use case)
  - ✅ Amazon PA-API well-documented SDK
  - ✅ Bounded context isolation prevents coupling
  - ❌ Minor risk: Amazon API rate limits or credential setup friction

- **Time to implement**: 6-8 hours
  - Phase 1: 1 hour (CatalogPort + CatalogItem with None handling + PA-API adapter)
  - Phase 2: 1 hour (ThemeRepositoryPort + ExistingTheme + YAML repository)
  - Phase 3: 45 min (ThemeFilterService with None safety + 3 MVP tests)
  - Phase 4: 1 hour (DetectTrendingThemeUseCase with business logic + 2 MVP tests)
  - Phase 5: 1 hour (ThemeExistenceChecker with Jaccard + 3 MVP tests)
  - Phase 6: 1 hour (ThemeScoringService with formula + 2 MVP tests)
  - Phase 7: 1 hour (OpenAI integration + prompts + response validation)
  - Phase 8: 30 min (Versioned YAML writer)
  - Phase 9: 30 min (Thin TrendScout agent with logging only)
  - Phase 10: 45 min (CLI orchestrator with DI + Makefile)
  - Phase 11: 1.5 hours (8+ MVP unit tests with fakes)

**Post-MVP enhancements** (deferred):
- Injectable policies from config.yaml
- ClockPort + SlugService for deterministic testing
- Keepa catalog adapter (no domain changes needed)
- Database-backed theme repository
