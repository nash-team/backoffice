# Codebase Structure

## Backend

### Naming Conventions

- **Files**: `snake_case.py` (all Python modules)
- **Classes**: `PascalCase`
  - Entities: `Ebook`, `ImagePage`, `ThemeProfile`
  - Use Cases: `VerbNounUseCase` (e.g., `CreateEbookUseCase`, `ApproveEbookUseCase`)
  - Ports: `NounPort` (e.g., `EbookPort`, `FileStoragePort`, `CoverGenerationPort`)
  - Adapters: `TechnologyNounAdapter` (e.g., `GoogleDriveStorageAdapter`)
  - Providers: `TechnologyNounProvider` (e.g., `GeminiImageProvider`, `WeasyPrintAssemblyProvider`)
  - Repositories: `SqlAlchemyNounRepository` (e.g., `SqlAlchemyEbookRepository`)
  - Strategies: `NounStrategy` (e.g., `ColoringBookStrategy`)
  - Events: `NounVerbedEvent` (e.g., `EbookCreatedEvent`, `EbookApprovedEvent`)
  - Factories: `NounFactory` (e.g., `StrategyFactory`, `ProviderFactory`)
  - Services: Domain services in `PascalCase` (e.g., `CoverGenerationService`, `RegenerationService`)
- **Functions**: `snake_case()` (all functions and methods)
- **Variables**: `snake_case` (all variables)
- **Constants**: `UPPER_CASE` (constants and config values)
- **Tests**: `test_subject_scenario` (e.g., `test_approve_draft_ebook`, `test_generate_cover_success`)
- **Test Classes**: `TestNounUseCase` (e.g., `TestApproveEbookUseCase`)
- **Test Fixtures with Side Effects**: Prefix with `_` (e.g., `_sample_ebooks`)
- **Fake Implementations**: `FakeNounPort` (e.g., `FakeCoverPort`, `FakePagePort`)

### Folder Structure

```
src/backoffice/
├── features/                          # 100% feature-based (screaming architecture)
│   ├── ebook/
│   │   ├── creation/                  # Ebook creation feature
│   │   │   ├── domain/
│   │   │   │   ├── entities/          # Feature-specific entities (CreationRequest)
│   │   │   │   ├── events/            # EbookCreatedEvent
│   │   │   │   ├── strategies/        # ColoringBookStrategy, StrategyFactory
│   │   │   │   └── usecases/          # CreateEbookUseCase
│   │   │   ├── infrastructure/
│   │   │   │   └── event_handlers/    # Event subscribers
│   │   │   ├── presentation/
│   │   │   │   ├── routes/            # form_routes.py
│   │   │   │   └── templates/partials/ # enhanced_ebook_form.html
│   │   │   ├── public/
│   │   │   │   └── events/            # Public event definitions
│   │   │   └── tests/
│   │   │       ├── contracts/         # Contract tests
│   │   │       └── unit/domain/       # Co-located unit tests
│   │   ├── lifecycle/                 # Approve/reject workflow
│   │   │   ├── domain/
│   │   │   │   ├── events/            # EbookApprovedEvent, EbookRejectedEvent
│   │   │   │   └── usecases/          # ApproveEbookUseCase, RejectEbookUseCase, GetStatsUseCase
│   │   │   ├── infrastructure/
│   │   │   │   └── event_handlers/
│   │   │   ├── presentation/
│   │   │   │   ├── routes/
│   │   │   │   └── templates/partials/ # stats.html, validation_buttons.html
│   │   │   └── tests/
│   │   │       ├── unit/
│   │   │       ├── integration/
│   │   │       └── e2e/
│   │   ├── listing/                   # List/filter ebooks
│   │   │   ├── domain/
│   │   │   │   ├── entities/          # Feature-specific entities
│   │   │   │   └── usecases/          # GetEbooksUseCase
│   │   │   ├── presentation/
│   │   │   │   ├── routes/
│   │   │   │   └── templates/
│   │   │   │       ├── ebook_detail.html
│   │   │   │       └── partials/      # ebooks_table.html, ebooks_table_row.html, pagination.html
│   │   │   └── tests/
│   │   │       └── unit/domain/
│   │   ├── regeneration/              # Regenerate pages/covers
│   │   │   ├── domain/
│   │   │   │   ├── entities/          # PageType, RegenerationRequest
│   │   │   │   ├── events/            # CoverRegeneratedEvent, ContentPageRegeneratedEvent, BackCoverRegeneratedEvent
│   │   │   │   ├── services/          # RegenerationService
│   │   │   │   └── usecases/          # RegenerateCoverUseCase, RegenerateBackCoverUseCase, RegenerateContentPageUseCase, CompleteEbookPagesUseCase
│   │   │   ├── infrastructure/
│   │   │   │   └── event_handlers/
│   │   │   ├── presentation/routes/
│   │   │   └── tests/unit/domain/
│   │   ├── export/                    # PDF/KDP export
│   │   │   ├── domain/
│   │   │   │   ├── entities/          # ExportRequest
│   │   │   │   ├── events/            # EbookExportedEvent, KdpExportGeneratedEvent
│   │   │   │   ├── usecases/          # ExportEbookPdfUseCase, ExportToKdpUseCase, ExportToKdpInteriorUseCase
│   │   │   │   └── protocols.py       # Domain protocols
│   │   │   ├── presentation/routes/
│   │   │   └── tests/unit/domain/
│   │   └── shared/                    # Ebook-specific shared code (2+ ebook features)
│   │       ├── domain/
│   │       │   ├── constants.py       # Ebook constants
│   │       │   ├── entities/          # Ebook, ImagePage, GenerationRequest, ThemeProfile, Pagination
│   │       │   ├── errors/            # ErrorTaxonomy (ebook-specific errors)
│   │       │   ├── models/            # Domain models
│   │       │   ├── policies/          # ModelRegistry, QualityValidator
│   │       │   ├── ports/             # EbookPort, EbookQueryPort, FileStoragePort, CoverGenerationPort, ContentPageGenerationPort, ContentGenerationPort, AssemblyPort, EbookGenerationStrategyPort
│   │       │   ├── services/          # CoverGenerationService, PageGenerationService, PdfAssemblyService, PromptTemplateEngine
│   │       │   ├── theme/             # ThemeLoader
│   │       │   └── value_objects/     # Value objects
│   │       ├── infrastructure/
│   │       │   ├── adapters/
│   │       │   │   ├── auth/          # Auth adapters
│   │       │   │   ├── sources/       # Source adapters
│   │       │   │   └── tests/         # Test adapters
│   │       │   ├── factories/         # Factories
│   │       │   ├── models/            # SQLAlchemy models
│   │       │   ├── providers/         # Domain-specific providers
│   │       │   │   ├── images/        # Image generation providers
│   │       │   │   │   ├── gemini/    # GeminiImageProvider
│   │       │   │   │   └── openrouter/ # OpenRouterImageProvider
│   │       │   │   ├── publishing/    # Publishing providers
│   │       │   │   │   └── kdp/       # KDP-specific providers
│   │       │   │   │       ├── assembly/ # InteriorAssemblyProvider, CoverAssemblyProvider
│   │       │   │   │       └── utils/    # spine_generator, color_utils, barcode_utils
│   │       │   │   ├── weasyprint_assembly_provider.py
│   │       │   │   └── provider_factory.py
│   │       │   ├── queries/           # SqlAlchemyEbookQuery
│   │       │   ├── repositories/      # SqlAlchemyEbookRepository, SqlAlchemyPaginationRepository
│   │       │   └── utils/             # Infrastructure utilities
│   │       ├── presentation/
│   │       │   └── templates/         # dashboard.html
│   │       └── tests/unit/
│   │           ├── config/            # Test config
│   │           ├── domain/
│   │           │   ├── entities/      # Entity tests
│   │           │   └── services/      # Service tests
│   │           ├── fakes/             # FakeCoverPort, FakePagePort, FakeAssemblyPort, FakeFileStoragePort
│   │           ├── infrastructure/
│   │           │   ├── adapters/      # Adapter tests
│   │           │   └── utils/         # KDP utility tests
│   │           └── presentation/routes/ # Route tests
│   └── shared/                        # Code used by 2+ features across domains
│       ├── domain/
│       │   └── (currently empty - all entities moved to ebook/shared)
│       ├── infrastructure/
│       │   ├── adapters/              # Cross-domain adapters
│       │   ├── database.py            # Database connection
│       │   └── events/                # EventBus, EventHandler
│       └── presentation/
│           ├── routes/                # templates.py (Jinja2 ChoiceLoader)
│           ├── static/                # Shared static files
│           │   ├── css/               # dashboard.css, login.css
│           │   ├── js/                # dashboard.js
│           │   └── fonts/             # Font files
│           └── templates/
│               ├── dashboard.html     # Main dashboard (now in ebook/shared/)
│               ├── login.html         # Login page
│               └── layouts/           # base.html
├── config/                            # @path Application config
│   ├── loader.py                      # Config loader
│   └── models_schema.py               # Model schema definitions
├── migrations/                        # @path Alembic migrations
│   └── versions/
├── main.py                            # @path FastAPI app entry point
└── conftest.py                        # @path Pytest shared fixtures
```

### Module Dependencies

- **Dependency Direction**: `presentation → infrastructure → domain` (domain has NO dependencies)
- **Feature Communication**: Via EventBus (e.g., `EbookCreatedEvent` published by creation feature)
- **Circular Dependencies**: None (enforced by hexagonal architecture)
- **Import Strategy**: Absolute imports from `backoffice.features.*`
  - Cross-domain shared: `from backoffice.features.shared.infrastructure.events.event_bus import EventBus`
  - Ebook shared entities: `from backoffice.features.ebook.shared.domain.entities.ebook import Ebook`
  - Feature use cases: `from backoffice.features.ebook.creation.domain.usecases.create_ebook import CreateEbookUseCase`
  - Ebook ports: `from backoffice.features.ebook.shared.domain.ports.ebook_port import EbookPort`

### Code Organization Principles

- **Feature-Based (Screaming Architecture)**: ALL code organized by business feature
- **NO Root Technical Folders**: `domain/`, `infrastructure/`, `presentation/` DO NOT exist at root
- **DDD Bounded Contexts**: Each feature = one bounded context with clear boundaries
- **Test Co-location**: Tests live in `features/*/tests/` next to code they test
- **Shared Kernel Rules**:
  - `features/shared/` = Code used by 2+ features across domains (EventBus, database, templates loader)
  - `features/ebook/shared/` = Code used by 2+ ebook features only (Ebook entity, ebook ports, ebook providers)
  - If only 1 feature uses it, keep in that feature
  - Providers organized by technology domain: `images/`, `publishing/kdp/`
  - Fakes for testing live in `features/ebook/shared/tests/unit/fakes/`
- **Feature Structure Pattern**: Each feature follows `domain/ → infrastructure/ → presentation/ → tests/`
- **Public API Pattern**: Features expose public contracts via `public/` folder (e.g., events)

### Feature Internal Structure

```
features/<feature_name>/
├── domain/
│   ├── entities/          # Feature-specific entities
│   ├── events/            # Domain events (NounVerbedEvent)
│   ├── usecases/          # Use cases (VerbNounUseCase)
│   ├── services/          # Domain services
│   ├── strategies/        # Strategies (NounStrategy)
│   └── protocols.py       # Domain protocols (optional)
├── infrastructure/        # Usually empty or minimal
│   ├── adapters/          # External service adapters
│   └── event_handlers/    # EventBus subscribers
├── presentation/
│   ├── routes/            # FastAPI routers (__init__.py or named files)
│   └── templates/         # Jinja2 templates
│       └── partials/      # HTMX partial templates
├── public/                # Public API (optional)
│   └── events/            # Public event definitions
└── tests/                 # Co-localized tests
    ├── contracts/         # Contract tests (optional)
    ├── unit/
    │   └── domain/        # Mirror domain structure
    ├── integration/
    └── e2e/
```

## Frontend

### Naming Conventions

- **Files**: `snake_case.html` (Jinja2 templates)
- **Partials**: `noun_context.html` (e.g., `ebooks_table.html`, `validation_buttons.html`)
- **CSS Classes**: `kebab-case` (e.g., `ebook-card`, `validation-btn`)
- **JavaScript Functions**: `camelCase` (e.g., `handleSubmit`, `updateTable`)
- **JavaScript Variables**: `camelCase`
- **CSS Files**: `snake_case.css` (e.g., `dashboard.css`, `login.css`)

### Template Organization

```
features/
├── shared/presentation/
│   ├── templates/
│   │   ├── login.html               # Login page
│   │   └── layouts/
│   │       └── base.html            # Base layout
│   └── static/
│       ├── css/                     # Shared styles
│       ├── js/                      # Shared scripts
│       └── fonts/                   # Font files
├── ebook/shared/presentation/templates/
│   └── dashboard.html               # Main dashboard
├── ebook/listing/presentation/templates/
│   ├── ebook_detail.html            # Detail view
│   └── partials/
│       ├── ebooks_table.html        # HTMX partial
│       ├── ebooks_table_row.html    # HTMX partial
│       └── pagination.html          # HTMX partial
├── ebook/creation/presentation/templates/partials/
│   └── enhanced_ebook_form.html
└── ebook/lifecycle/presentation/templates/partials/
    ├── stats.html
    └── validation_buttons.html
```

### Module Dependencies

- **Template Loader**: Jinja2 ChoiceLoader (multi-feature template resolution)
  - Configured in `features/shared/presentation/routes/templates.py`
- **Static Files**: Served from `features/shared/presentation/static/`
- **Template Includes**: Use relative paths within feature (e.g., `{% include "partials/stats.html" %}`)

## Configuration

- **Root Config Files**:
  - Environment variables: `.env.example` @path
  - Database migrations: `alembic.ini` @path
  - Python dependencies & tools: `pyproject.toml` (ruff, mypy, deptry) @path
  - Testing: `pytest.ini` @path
  - Pre-commit hooks: `.pre-commit-config.yaml` @path
  - Development commands: `Makefile` @path
  - AI developer instructions: `CLAUDE.md` (symlink to `aidd-docs/AGENTS.md`) @path
  - Docker: `Dockerfile`, `docker-compose.yml` @path
  - Type checking: `pyrightconfig.json` @path
  - Dead code detection: `.vulture_whitelist.py` @path
  - Tool versions: `.tool-versions` @path
- **App Config Location**: `src/backoffice/config/` @path
  - `loader.py` (config loader)
  - `models_schema.py` (model schema definitions)
- **Database Config**: `src/backoffice/features/shared/infrastructure/database.py` @path
