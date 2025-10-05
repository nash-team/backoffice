# Guide de Migration vers Feature-Based Architecture

> Documentation de référence pour migrer le code legacy vers une architecture par features respectant DDD, SOLID et Screaming Architecture

## 🎯 Vue d'ensemble

Ce guide documente le processus de migration d'une architecture hexagonale centralisée vers une **architecture par features** (Feature-Based Architecture) en respectant les principes de **DDD**, **SOLID** et **Screaming Architecture**.

### Feature de référence : `generation_costs`

La feature `generation_costs` sert de **template parfait** pour toutes les futures migrations. Elle a été migrée avec succès et respecte tous les principes architecturaux.

## 📐 Structure d'une Feature

Chaque feature doit suivre cette structure exacte :

```
features/
└── {feature_name}/              # Nom descriptif en snake_case
    ├── README.md                # Documentation de la feature
    ├── domain/                  # Cœur métier (ZERO dépendances)
    │   ├── __init__.py
    │   ├── entities/           # Entités et Value Objects
    │   │   ├── __init__.py
    │   │   └── {entity}.py
    │   ├── events/             # Domain Events
    │   │   ├── __init__.py
    │   │   └── {event}_event.py
    │   ├── ports/              # Interfaces (abstractions)
    │   │   ├── __init__.py
    │   │   └── {port}_port.py
    │   └── usecases/           # Cas d'usage métier
    │       ├── __init__.py
    │       └── {usecase}_usecase.py
    ├── infrastructure/          # Détails techniques
    │   ├── __init__.py
    │   ├── adapters/           # Implémentations des ports
    │   │   ├── __init__.py
    │   │   └── {adapter}_repository.py
    │   ├── models/             # SQLAlchemy models
    │   │   ├── __init__.py
    │   │   └── {model}_model.py
    │   └── event_handlers/     # Handlers d'événements
    │       └── __init__.py
    ├── presentation/            # Interface utilisateur
    │   ├── routes/             # Routes FastAPI
    │   │   └── __init__.py
    │   └── templates/          # Templates HTML (Jinja2)
    │       └── {page}.html
    └── tests/                   # ✅ Tests co-localisés
        ├── __init__.py
        ├── unit/
        │   ├── __init__.py
        │   └── test_{entity}.py
        ├── integration/
        │   └── __init__.py
        └── e2e/
            └── __init__.py
```

## ✅ Checklist de Migration (8 phases)

### Phase 1 : Analyse et Planification

- [ ] **Identifier le bounded context** : Quelle responsabilité métier ?
- [ ] **Lister les entités** : Quelles sont les entités du domaine ?
- [ ] **Identifier les use cases** : Quelles actions métier ?
- [ ] **Repérer les dépendances externes** : DB, APIs, fichiers ?
- [ ] **Définir les événements** : Quels événements domaine émettre ?

**Exemple `generation_costs`** :
- Bounded context : **Tracking des coûts de génération d'ebooks**
- Entités : `TokenUsage`, `ImageUsage`, `CostCalculation`
- Use cases : `TrackTokenUsageUseCase`, `CalculateGenerationCostUseCase`
- Dépendances : PostgreSQL (token_usages, image_usages tables)
- Événements : `TokensConsumedEvent`, `CostCalculatedEvent`

### Phase 2 : Créer la Structure Domain

- [ ] Créer `features/{feature_name}/domain/`
- [ ] Créer les **entités** dans `domain/entities/`
  - Utiliser `@dataclass` avec `frozen=True` pour value objects
  - ZERO import d'infrastructure
  - Logique métier pure
- [ ] Créer les **ports** dans `domain/ports/`
  - Interfaces abstraites avec `ABC` et `@abstractmethod`
  - Définir les contrats sans implémentation
- [ ] Créer les **événements** dans `domain/events/`
  - Hériter de `DomainEvent` (dans `features/shared/`)
  - Nommer en past tense : `{Action}Event` (ex: `TokensConsumedEvent`)
- [ ] Créer les **use cases** dans `domain/usecases/`
  - Un use case = une action métier
  - Dépend UNIQUEMENT de ports (abstractions)
  - Émet des événements via `EventBus`

**Exemple `generation_costs`** :

```python
# domain/entities/token_usage.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)  # Immutable
class TokenUsage:
    """Value Object for token usage."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

# domain/ports/token_tracker_port.py
from abc import ABC, abstractmethod

class TokenTrackerPort(ABC):
    """Port for token tracking."""

    @abstractmethod
    async def save_token_usage(self, request_id: str, usage: TokenUsage) -> None:
        pass

# domain/usecases/track_token_usage_usecase.py
class TrackTokenUsageUseCase:
    def __init__(self, token_tracker: TokenTrackerPort, event_bus: EventBus):
        self.token_tracker = token_tracker  # Dépend d'une abstraction
        self.event_bus = event_bus

    async def execute(self, request_id: str, model: str, ...) -> None:
        usage = TokenUsage(model=model, ...)
        await self.token_tracker.save_token_usage(request_id, usage)
        await self.event_bus.publish(TokensConsumedEvent(...))
```

### Phase 3 : Créer l'Infrastructure

- [ ] Créer `features/{feature_name}/infrastructure/`
- [ ] Créer les **models DB** dans `infrastructure/models/`
  - SQLAlchemy models avec `Base`
  - Mapper vers les entités du domain
- [ ] Créer les **adapters** dans `infrastructure/adapters/`
  - Implémenter les ports du domain
  - Gérer la persistance (DB, API, fichiers)
  - Convertir entre models DB et entités domain
- [ ] (Optionnel) Créer les **event handlers** dans `infrastructure/event_handlers/`

**Exemple `generation_costs`** :

```python
# infrastructure/models/token_usage_model.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from backoffice.infrastructure.database import Base

class TokenUsageModel(Base):
    __tablename__ = "token_usages"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(255), nullable=False, index=True)
    model = Column(String(255), nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    cost = Column(Numeric(10, 6), nullable=False)

# infrastructure/adapters/token_tracker_repository.py
class TokenTrackerRepository(TokenTrackerPort):  # Implémente le port
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_token_usage(self, request_id: str, usage: TokenUsage) -> None:
        model = TokenUsageModel(
            request_id=request_id,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost=usage.cost,
        )
        self.db.add(model)
        await self.db.commit()
```

### Phase 4 : Créer la Presentation

- [ ] Créer `features/{feature_name}/presentation/routes/__init__.py`
- [ ] Créer les **routes API** (prefix: `/api/{feature-name}`)
  - `router = APIRouter(prefix="/api/{feature-name}", tags=["{Feature Name}"])`
  - GET, POST, PUT, DELETE selon besoins
  - Utiliser `AsyncRepositoryFactoryDep` pour injection de dépendances
  - Retourner des dicts (FastAPI les sérialize en JSON)
- [ ] Créer les **routes pages** (prefix: `/dashboard/{page}`)
  - `pages_router = APIRouter(prefix="/dashboard/{page}", tags=["Pages - {Feature}"])`
  - Retourner `templates.TemplateResponse()`
- [ ] (Optionnel) Créer les **templates HTML** dans `presentation/templates/`

**Exemple `generation_costs`** :

```python
# presentation/routes/__init__.py
from fastapi import APIRouter, Depends
from backoffice.infrastructure.factories.repository_factory import (
    AsyncRepositoryFactory,
    get_async_repository_factory,
)

AsyncRepositoryFactoryDep = Annotated[
    AsyncRepositoryFactory,
    Depends(get_async_repository_factory)
]

# Routes API
router = APIRouter(prefix="/api/generation-costs", tags=["Generation Costs"])

@router.get("/")
async def list_generation_costs(factory: AsyncRepositoryFactoryDep) -> dict:
    """List all costs with summary statistics."""
    token_tracker = TokenTrackerRepository(factory.db)
    calculations = await token_tracker.get_all_cost_calculations()
    return {"cost_summaries": [...], "summary_statistics": {...}}

@router.get("/{request_id}")
async def get_cost_detail(request_id: str, factory: AsyncRepositoryFactoryDep) -> dict:
    """Get detailed breakdown for a request."""
    token_tracker = TokenTrackerRepository(factory.db)
    calc = await token_tracker.get_cost_calculation(request_id)
    return {"request_id": calc.request_id, "total_cost": float(calc.total_cost), ...}

# Routes Pages
pages_router = APIRouter(prefix="/dashboard/costs", tags=["Pages - Costs"])

@pages_router.get("")
async def costs_page(request: Request, factory: AsyncRepositoryFactoryDep) -> Response:
    """Display costs page."""
    token_tracker = TokenTrackerRepository(factory.db)
    calculations = await token_tracker.get_all_cost_calculations()
    return templates.TemplateResponse("costs.html", {
        "request": request,
        "cost_summaries": [...],
    })
```

### Phase 5 : Enregistrer les Routes

- [ ] Importer les routers dans `src/backoffice/presentation/routes/__init__.py`
- [ ] Ajouter à la fonction `init_routes()`
  - Router API : `app.include_router(feature_router)`
  - Router pages : `app.include_router(feature_pages_router)`

**Exemple `generation_costs`** :

```python
# src/backoffice/presentation/routes/__init__.py
from backoffice.features.generation_costs.presentation.routes import (
    pages_router as costs_pages_router,
    router as generation_costs_router,
)

def init_routes(app: FastAPI) -> None:
    # ... autres routes ...
    # Feature routes
    app.include_router(generation_costs_router)  # API routes
    app.include_router(costs_pages_router)       # Page routes
```

### Phase 6 : Migrer les Tests

- [ ] Créer `features/{feature_name}/tests/`
- [ ] Déplacer les tests existants vers les sous-dossiers :
  - `tests/unit/` : Tests des entités, value objects, use cases (avec fakes)
  - `tests/integration/` : Tests avec DB réelle (testcontainers)
  - `tests/e2e/` : Tests utilisateur (Playwright)
- [ ] Mettre à jour `pytest.ini` :
  ```ini
  [pytest]
  testpaths =
      tests
      features
  ```
- [ ] Mettre à jour `pyproject.toml` (ruff) :
  ```toml
  [tool.ruff.lint.per-file-ignores]
  "features/**/tests/**" = ["S101", "E501"]  # Allow asserts and long lines
  ```
- [ ] Mettre à jour `pyproject.toml` (deptry) :
  ```toml
  [tool.deptry]
  exclude = ["tests", "features/**/tests", ...]
  ```

### Phase 7 : Nettoyer le Legacy

- [ ] **Identifier le code legacy** à supprimer
- [ ] **Chercher toutes les références** avec grep/Glob
- [ ] **Supprimer les fichiers legacy**
- [ ] **Retirer les imports legacy** dans les fichiers restants
- [ ] **Supprimer les dépendances inutilisées** dans `pyproject.toml`
- [ ] **Mettre à jour les migrations Alembic** si nécessaire

**Exemple `generation_costs`** :
- ❌ Supprimé : `get_ebook_costs.py`, `token_tracker.py`
- ❌ Supprimé : `GenerationMetadata` value object
- ❌ Supprimé : Paramètre `token_tracker` dans providers
- ✅ Migré vers : Feature `generation_costs` avec événements

### Phase 8 : Vérification Quality

**IMPORTANT** : L'ordre des vérifications est crucial pour éviter de casser le formatage.

- [ ] **Tests** : `pytest features/{feature_name}/ -v`
  - Vérifier que tous les tests passent avant les autres checks
- [ ] **Mypy** : `mypy src/backoffice/features/{feature_name}/`
  - Vérifier les types avant le formatage
- [ ] **Deptry** : `deptry .`
  - Vérifier les dépendances inutilisées
- [ ] **Frontend** : Vérifier que les templates appellent les bons endpoints
  - Chercher les templates qui utilisent la feature (ex: `grep -r "hx-put.*{feature_name}" src/backoffice/presentation/templates/`)
  - Vérifier que les endpoints correspondent aux routes de la feature
  - Vérifier que les méthodes HTTP sont correctes (GET/POST/PUT/DELETE)
  - Tester manuellement en lançant le serveur et en testant les actions UI
- [ ] **Ruff** (EN DERNIER) : `ruff check --fix src/backoffice/features/{feature_name}/`
  - Formatte automatiquement les imports et le code
  - À lancer EN DERNIER pour éviter de re-casser le formatage
- [ ] **Pre-commit** : `pre-commit run --all-files`
  - Vérifier que tous les hooks passent (incluant ruff)

**Exemple `ebook_lifecycle`** :

```bash
# 1. Tests d'abord
pytest src/backoffice/features/ebook_lifecycle/ -v

# 2. Vérifications statiques
mypy src/backoffice/features/ebook_lifecycle/
deptry .

# 3. Vérifier les templates concernés
grep -r "hx-put.*approve\|hx-put.*reject" src/backoffice/presentation/templates/

# Endpoints corrects :
# ✅ BON - Endpoint correct avec méthode HTTP correcte
<button hx-put="/api/dashboard/ebooks/{{ ebook.id }}/approve">

# ❌ MAUVAIS - Endpoint incorrect
<button hx-post="/api/ebooks/{{ ebook.id }}/approve">

# 4. Tester manuellement
# - Lancer le serveur : make run
# - Ouvrir le dashboard et tester approve/reject
# - Vérifier les logs pour les 404 ou 500

# 5. Ruff EN DERNIER (formatte automatiquement)
ruff check --fix src/backoffice/features/ebook_lifecycle/

# 6. Pre-commit final
pre-commit run --all-files
```

## 🎨 Principes Architecturaux

### DDD (Domain-Driven Design)

#### Bounded Context
- **Une feature = un bounded context**
- Responsabilité claire et délimitée
- Pas de fuite de concepts vers d'autres features

#### Ubiquitous Language
- Utiliser le vocabulaire métier partout
- Classes, méthodes, variables doivent refléter le domaine
- Exemple : `TokenUsage`, `CostCalculation`, `request_id`

#### Building Blocks
- **Entities** : Objets avec identité (id)
- **Value Objects** : Objets immuables sans identité (`@dataclass(frozen=True)`)
- **Aggregates** : Racine d'agrégat (ex: `CostCalculation` agrège `TokenUsage`)
- **Domain Events** : Événements métier (ex: `TokensConsumedEvent`)
- **Repositories** : Abstraction de persistance (port + adapter)

#### Domain Layer Purity
```python
# ✅ BON - Domain ne dépend de RIEN
from backoffice.features.generation_costs.domain.entities.token_usage import TokenUsage
from backoffice.features.generation_costs.domain.ports.token_tracker_port import TokenTrackerPort

# ❌ MAUVAIS - Domain ne doit PAS importer infrastructure
from backoffice.infrastructure.database import Base
from sqlalchemy import Column
```

### SOLID

#### Single Responsibility Principle (SRP)
```python
# ✅ BON - Une classe = une responsabilité
class TrackTokenUsageUseCase:
    """SEULE responsabilité : persister token usage + émettre événement"""
    async def execute(...) -> None:
        await self.token_tracker.save_token_usage(...)
        await self.event_bus.publish(TokensConsumedEvent(...))

# ❌ MAUVAIS - Trop de responsabilités
class EbookService:
    async def generate_ebook(...):  # Génération
        ...
    async def track_costs(...):     # Tracking coûts
        ...
    async def send_email(...):      # Notification
        ...
```

#### Open/Closed Principle (OCP)
```python
# ✅ BON - Ouvert à l'extension (nouveaux types)
@dataclass(frozen=True)
class TokenUsage:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: Decimal

@dataclass(frozen=True)
class ImageUsage:  # Extension sans modifier TokenUsage
    model: str
    input_images: int
    output_images: int
    cost: Decimal
```

#### Liskov Substitution Principle (LSP)
```python
# ✅ BON - N'importe quelle implémentation du port fonctionne
class TokenTrackerPort(ABC):
    @abstractmethod
    async def save_token_usage(...) -> None: ...

class TokenTrackerRepository(TokenTrackerPort):     # PostgreSQL
    async def save_token_usage(...) -> None: ...

class InMemoryTokenTracker(TokenTrackerPort):       # Fake pour tests
    async def save_token_usage(...) -> None: ...
```

#### Interface Segregation Principle (ISP)
```python
# ✅ BON - Port minimal avec méthodes essentielles uniquement
class TokenTrackerPort(ABC):
    @abstractmethod
    async def save_token_usage(...) -> None: pass

    @abstractmethod
    async def get_cost_calculation(...) -> CostCalculation: pass

# ❌ MAUVAIS - Port obèse avec méthodes inutiles
class TokenTrackerPort(ABC):
    @abstractmethod
    async def save_token_usage(...) -> None: pass

    @abstractmethod
    async def export_to_excel(...) -> bytes: pass  # Pas pertinent pour tous

    @abstractmethod
    async def send_email_report(...) -> None: pass  # Mélange des responsabilités
```

#### Dependency Inversion Principle (DIP)
```python
# ✅ BON - Use case dépend d'ABSTRACTION (port)
class TrackTokenUsageUseCase:
    def __init__(self, token_tracker: TokenTrackerPort, event_bus: EventBus):
        self.token_tracker = token_tracker  # Port abstrait

# ❌ MAUVAIS - Use case dépend d'IMPLÉMENTATION concrète
class TrackTokenUsageUseCase:
    def __init__(self, token_tracker: TokenTrackerRepository):  # Couplage fort
        self.token_tracker = token_tracker
```

### Screaming Architecture

#### Structure qui "crie" son intention
```
✅ BON - On voit immédiatement ce que fait l'app
features/
├── generation_costs/    ← "Je gère les COÛTS DE GÉNÉRATION !"
├── ebook_validation/    ← "Je gère la VALIDATION d'ebooks !"
└── publishing/          ← "Je gère la PUBLICATION sur KDP !"

❌ MAUVAIS - Structure technique qui cache l'intention
src/
├── controllers/
├── services/
├── repositories/
└── models/
# → Impossible de savoir ce que fait l'app sans lire le code
```

#### Feature 100% autonome
```
✅ BON - Tout dans un seul dossier
features/generation_costs/
├── domain/           # Logique métier
├── infrastructure/   # Détails techniques
├── presentation/     # Routes + templates
└── tests/            # Tests co-localisés

❌ MAUVAIS - Code éparpillé
src/domain/entities/token_usage.py
src/infrastructure/repositories/token_tracker_repository.py
tests/unit/test_token_usage.py
# → Code dispersé, difficile à extraire
```

## 🚀 Event-Driven Architecture

### Émission d'événements

```python
# Use case émet un événement
class TrackTokenUsageUseCase:
    async def execute(self, request_id: str, ...) -> None:
        # 1. Persister
        await self.token_tracker.save_token_usage(request_id, usage)

        # 2. Émettre événement
        event = TokensConsumedEvent(
            request_id=request_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )
        await self.event_bus.publish(event)
```

### Écoute d'événements

```python
# Event handler réagit à l'événement
from backoffice.features.shared.infrastructure.events.event_handler import EventHandler

class UpdateEbookCostHandler(EventHandler[CostCalculatedEvent]):
    async def handle(self, event: CostCalculatedEvent) -> None:
        if event.ebook_id:
            ebook = await self.ebook_repo.get_by_id(event.ebook_id)
            ebook.generation_cost = event.total_cost
            await self.ebook_repo.save(ebook)

# Enregistrement
event_bus.subscribe(CostCalculatedEvent, UpdateEbookCostHandler())
```

### Avantages
- ✅ **Découplage** : Features ne se connaissent pas directement
- ✅ **Extensibilité** : Ajouter des handlers sans modifier le code existant
- ✅ **Testabilité** : Tester les handlers indépendamment

## 📝 Conventions de Nommage

### Fichiers et Dossiers
- **Features** : `snake_case` (ex: `generation_costs`, `ebook_validation`)
- **Fichiers Python** : `snake_case` (ex: `token_usage.py`, `track_token_usage_usecase.py`)
- **Templates** : `snake_case` (ex: `costs.html`, `ebook_detail.html`)

### Classes
- **Entities** : `PascalCase` (ex: `TokenUsage`, `CostCalculation`)
- **Use Cases** : `VerbNounUseCase` (ex: `TrackTokenUsageUseCase`, `CalculateGenerationCostUseCase`)
- **Ports** : `NounPort` (ex: `TokenTrackerPort`, `EbookRepositoryPort`)
- **Adapters** : `TechnologyNounAdapter/Repository` (ex: `TokenTrackerRepository`, `GoogleDriveStorageAdapter`)
- **Events** : `NounActionEvent` ou `ActionEvent` (ex: `TokensConsumedEvent`, `CostCalculatedEvent`)

### Méthodes
- **Use cases** : `async def execute(...)` (toujours)
- **Repositories** : `get_by_id`, `save`, `delete`, `get_all`
- **Event handlers** : `async def handle(self, event: EventType)`

### Tests
- **Unit tests** : `test_subject_scenario` (ex: `test_generate_cover_success`)
- **E2E tests** : `test_persona_can_action` (ex: `test_creator_can_generate_first_ebook`)

## 🧪 Stratégie de Tests

### Unit Tests (Chicago Style)
```python
# Utiliser des FAKES (vraies implémentations simplifiées)
class FakeTokenTracker(TokenTrackerPort):
    def __init__(self):
        self.usages: dict[str, list[TokenUsage]] = {}

    async def save_token_usage(self, request_id: str, usage: TokenUsage) -> None:
        if request_id not in self.usages:
            self.usages[request_id] = []
        self.usages[request_id].append(usage)

# Test avec fake
async def test_track_token_usage_saves_to_repository():
    fake_tracker = FakeTokenTracker()
    usecase = TrackTokenUsageUseCase(fake_tracker, EventBus())

    await usecase.execute("req-123", model="gpt-4", ...)

    assert "req-123" in fake_tracker.usages
    assert len(fake_tracker.usages["req-123"]) == 1
```

### Integration Tests (avec testcontainers)
```python
# PostgreSQL réel + mocks pour APIs externes
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

async def test_token_tracker_persists_to_database(db_session):
    tracker = TokenTrackerRepository(db_session)
    usage = TokenUsage(model="gpt-4", ...)

    await tracker.save_token_usage("req-123", usage)

    result = await tracker.get_cost_calculation("req-123")
    assert result.total_tokens > 0
```

### E2E Tests (scénarios utilisateur)
```python
# Tests narratifs avec personas
async def test_creator_can_view_generation_costs(page: Page, server_url: str):
    """
    GIVEN Marie est une créatrice qui a généré plusieurs ebooks
    WHEN elle accède à la page des coûts
    THEN elle voit le coût total et le détail par ebook
    """
    await page.goto(f"{server_url}/dashboard/costs")

    # Vérifier le coût total
    total_cost = await page.locator(".total-cost").text_content()
    assert "$" in total_cost

    # Vérifier le tableau de détails
    rows = await page.locator("table tbody tr").count()
    assert rows > 0
```

## 🔍 Anti-Patterns à Éviter

### ❌ Domain dépend d'Infrastructure
```python
# MAUVAIS
from sqlalchemy import Column, Integer
from backoffice.infrastructure.database import Base

class TokenUsage(Base):  # ❌ Entité domaine ne doit PAS hériter de Base
    __tablename__ = "token_usages"
```

### ❌ Use Case retourne une entité DB
```python
# MAUVAIS
class GetEbookUseCase:
    async def execute(self, ebook_id: int) -> EbookModel:  # ❌ Retourne model DB
        return await self.db.get(EbookModel, ebook_id)

# BON
class GetEbookUseCase:
    async def execute(self, ebook_id: int) -> Ebook:  # ✅ Retourne entité domain
        model = await self.db.get(EbookModel, ebook_id)
        return self.repository._to_domain(model)
```

### ❌ Feature dépend directement d'une autre feature
```python
# MAUVAIS
from backoffice.features.generation_costs.infrastructure.adapters.token_tracker_repository import (
    TokenTrackerRepository
)

class EbookService:
    def __init__(self):
        self.token_tracker = TokenTrackerRepository(db)  # ❌ Couplage direct
```

### ❌ Code métier dans les routes
```python
# MAUVAIS
@router.post("/ebooks")
async def create_ebook(request: EbookRequest, db: AsyncSession):
    # ❌ Logique métier dans la route
    ebook = EbookModel(title=request.title, status="DRAFT")
    if not ebook.title or len(ebook.title) < 3:
        raise ValueError("Title too short")
    db.add(ebook)
    await db.commit()

# BON
@router.post("/ebooks")
async def create_ebook(request: EbookRequest, factory: AsyncRepositoryFactoryDep):
    # ✅ Déléguer au use case
    usecase = CreateEbookUseCase(factory.get_ebook_repository())
    ebook = await usecase.execute(request.title, request.theme_id)
    return {"id": ebook.id}
```

## 📚 Ressources

### Documentation interne
- [CLAUDE.md](../CLAUDE.md) - Contexte global du projet
- [features/generation_costs/README.md](../src/backoffice/features/generation_costs/README.md) - Feature de référence

### Concepts DDD
- **Bounded Context** : Limite claire d'une feature
- **Ubiquitous Language** : Vocabulaire métier partagé
- **Aggregates** : Racine d'agrégat avec invariants
- **Domain Events** : Événements métier pour découplage

### Patterns
- **Ports & Adapters** : Abstraction (port) + Implémentation (adapter)
- **Use Case Pattern** : Point d'entrée unique pour action métier
- **Repository Pattern** : Abstraction de persistance
- **Event-Driven Architecture** : Communication asynchrone via événements

## 🎓 Exemple Complet : Migration d'une Feature

Voir la feature `generation_costs` pour un exemple complet de migration respectant tous les principes :

```bash
tree src/backoffice/features/generation_costs/
```

Cette feature sert de **template parfait** pour toutes les futures migrations.

---

**Version** : 1.0
**Dernière mise à jour** : 2025-01-05
**Auteur** : Migration team
**Status** : ✅ Validé et appliqué sur `generation_costs`
