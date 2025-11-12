# Guide Architecture - Ebook Generator Backoffice

## 🎯 Vision Globale : Architecture "Screaming" (Feature-Based)

```
src/backoffice/
└── features/                           # Tout est organisé par FEATURE métier
    ├── ebook/creation/                 # Feature : Créer un ebook
    ├── ebook/lifecycle/                # Feature : Approuver/rejeter
    ├── ebook/listing/                  # Feature : Lister/filtrer
    ├── ebook/regeneration/             # Feature : Regénérer des pages
    ├── ebook/export/                   # Feature : Export PDF KDP
    ├── generation_costs/               # Feature : Coûts de génération
    └── shared/                         # Code partagé entre 2+ features
        ├── domain/                     # Entités, ports, services partagés
        ├── infrastructure/             # Adapters, providers, DB, EventBus
        │   ├── providers/              # 🎨 IMAGE PROVIDERS (OpenRouter, Gemini, ComfyUI)
        │   ├── adapters/               # Repositories, Storage adapters
        │   └── events/                 # EventBus implementation
        └── presentation/               # Auth, templates, static files
```

### 🔑 Principe Fondamental

**❌ PAS d'architecture technique en couches** (`domain/`, `infrastructure/`, `presentation/` à la racine)
**✅ Architecture par FEATURES métier** (chaque feature = 1 bounded context DDD)

---

## 📦 Structure d'une Feature

```
features/ebook/creation/
├── domain/
│   ├── entities/                       # Entités spécifiques à cette feature (si besoin)
│   ├── events/                         # Events émis par cette feature
│   ├── strategies/                     # Stratégies de génération
│   │   └── coloring_book_strategy.py
│   └── usecases/                       # Use cases (command handlers)
│       └── create_ebook_usecase.py
├── infrastructure/                     # Adapters SPÉCIFIQUES à cette feature
│   └── (souvent vide car on utilise shared/)
├── presentation/
│   ├── routes/                         # FastAPI routers
│   │   └── __init__.py                 # /ebooks/create
│   └── templates/                      # Templates Jinja2 (si besoin)
└── tests/                              # ⭐ Tests CO-LOCALISÉS
    ├── unit/                           # Tests unitaires
    └── integration/                    # Tests d'intégration
```

### 🤔 Quand Mettre du Code dans `shared/` vs dans une Feature ?

**Règle simple** :
- **Utilisé par 2+ features** → `features/shared/`
- **Utilisé par 1 seule feature** → `features/<feature>/`

**Exemples concrets** :

| Code | Localisation | Raison |
|------|--------------|--------|
| `OpenRouterImageProvider` | `features/shared/infrastructure/providers/` | Utilisé par `creation/`, `regeneration/` |
| `GeminiImageProvider` | `features/shared/infrastructure/providers/` | Utilisé par `creation/`, `regeneration/` |
| `ComfyUIImageProvider` (futur) | `features/shared/infrastructure/providers/` | Utilisé par `creation/`, `regeneration/` |
| `Ebook` entity | `features/shared/domain/entities/` | Utilisé par TOUTES les features ebook |
| `ColoringBookStrategy` | `features/ebook/creation/domain/strategies/` | Spécifique à `creation/` |
| `CreateEbookUseCase` | `features/ebook/creation/domain/usecases/` | Spécifique à `creation/` |

---

## 🔌 Ports & Adapters (Hexagonal Architecture)

### Ports (Interfaces abstraites)

Situés dans `features/shared/domain/ports/` :

```python
# Port abstrait (interface)
class CoverGenerationPort(ABC):
    @abstractmethod
    async def generate_cover(self, prompt: str, spec: ImageSpec) -> bytes:
        """Générer une image de cover."""
        pass

    @abstractmethod
    async def remove_text_from_cover(self, cover_bytes: bytes) -> bytes:
        """Retirer le texte de la cover (pour back cover)."""
        pass
```

### Adapters (Implémentations concrètes)

Situés dans `features/shared/infrastructure/providers/` :

```python
# Adapter OpenRouter (multi-héritage)
class OpenRouterImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Implémente les 2 ports car utilise le même modèle Gemini."""

    async def generate_cover(self, prompt, spec):
        # Appel API OpenRouter avec Gemini 2.5 Flash
        ...

    async def generate_page(self, prompt, spec):
        # Délègue à generate_cover (même algo)
        return await self.generate_cover(prompt, spec)
```

```python
# Adapter Gemini Direct
class GeminiImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """API directe Google Gemini (Nano Banana)."""
    ...
```

**Pourquoi dans `shared/` ?** → Ces providers sont réutilisés par **plusieurs features** (`creation/`, `regeneration/`).

---

## 🎨 Exemple Complet : Ajout d'un Provider Local (ComfyUI + Dual CLIP)

### Étape 1 : Créer le Port (si nouveau comportement)

Si tu veux un comportement différent (ex: vectorisation SVG), crée un nouveau port :

```python
# features/shared/domain/ports/vectorization_port.py
class VectorizationPort(ABC):
    @abstractmethod
    async def generate_vector_cover(self, prompt: str, spec: ImageSpec) -> bytes:
        """Générer une cover vectorielle (SVG)."""
        pass
```

**OU** réutilise les ports existants si le comportement est le même (juste une autre implémentation).

### Étape 2 : Créer l'Adapter

```python
# features/shared/infrastructure/providers/comfyui_image_provider.py
import httpx
from backoffice.features.shared.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.features.shared.domain.ports.content_page_generation_port import ContentPageGenerationPort

class ComfyUIImageProvider(CoverGenerationPort, ContentPageGenerationPort):
    """Provider local ComfyUI avec Dual CLIP."""

    def __init__(self, comfyui_url: str = "http://localhost:8188"):
        self.comfyui_url = comfyui_url
        self.client = httpx.AsyncClient(timeout=120.0)

    def is_available(self) -> bool:
        """Vérifie si ComfyUI est accessible."""
        try:
            response = self.client.get(f"{self.comfyui_url}/system_stats")
            return response.status_code == 200
        except:
            return False

    async def generate_cover(self, prompt: str, spec: ImageSpec, seed: int | None = None) -> bytes:
        """Génère une cover via ComfyUI workflow."""
        # 1. Construire le workflow JSON
        workflow = self._build_workflow(prompt, spec, seed)

        # 2. Envoyer à ComfyUI
        response = await self.client.post(
            f"{self.comfyui_url}/prompt",
            json={"prompt": workflow}
        )
        prompt_id = response.json()["prompt_id"]

        # 3. Attendre la génération (polling)
        image_bytes = await self._wait_for_image(prompt_id)

        # 4. Post-traitement si besoin (resize, border, etc.)
        if spec.color_mode == ColorMode.BLACK_WHITE:
            image_bytes = self._add_rounded_border_to_image(image_bytes)

        return image_bytes

    async def generate_page(self, prompt: str, spec: ImageSpec, seed: int | None = None) -> bytes:
        """Délègue à generate_cover (même workflow)."""
        return await self.generate_cover(prompt, spec, seed)

    async def remove_text_from_cover(self, cover_bytes: bytes) -> bytes:
        """Utilise un workflow ComfyUI pour retirer le texte."""
        # Option 1 : Workflow ComfyUI avec inpainting
        # Option 2 : Délègue à PIL (simple white rectangle)
        ...

    def _build_workflow(self, prompt: str, spec: ImageSpec, seed: int | None) -> dict:
        """Construit le workflow JSON ComfyUI avec Dual CLIP."""
        return {
            "1": {
                "class_type": "DualCLIPLoader",
                "inputs": {
                    "clip_name1": "clip_g.safetensors",
                    "clip_name2": "clip_l.safetensors",
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 0]
                }
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed or 42,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "positive": ["2", 0],
                    "model": ["4", 0],
                    "latent_image": ["5", 0]
                }
            },
            # ... autres nodes
        }

    async def _wait_for_image(self, prompt_id: str) -> bytes:
        """Polling pour attendre la fin de génération."""
        import asyncio

        while True:
            response = await self.client.get(f"{self.comfyui_url}/history/{prompt_id}")
            history = response.json()

            if prompt_id in history and history[prompt_id]["status"]["completed"]:
                # Récupérer l'image générée
                outputs = history[prompt_id]["outputs"]
                image_filename = outputs["9"]["images"][0]["filename"]

                # Télécharger l'image
                img_response = await self.client.get(
                    f"{self.comfyui_url}/view?filename={image_filename}"
                )
                return img_response.content

            await asyncio.sleep(1)  # Attendre 1 seconde avant de re-vérifier
```

**Pourquoi dans `features/shared/infrastructure/providers/` ?** → Ce provider sera utilisé par `creation/` ET `regeneration/`.

### Étape 3 : Configurer l'Injection de Dépendances

```python
# main.py
from backoffice.features.shared.infrastructure.providers.comfyui_image_provider import ComfyUIImageProvider

# Dans get_cover_port()
def get_cover_port() -> CoverGenerationPort:
    provider_type = os.getenv("IMAGE_PROVIDER", "openrouter")  # openrouter | gemini | comfyui

    if provider_type == "comfyui":
        comfyui_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
        return ComfyUIImageProvider(comfyui_url=comfyui_url)
    elif provider_type == "gemini":
        return GeminiImageProvider()
    else:
        return OpenRouterImageProvider(...)
```

### Étape 4 : Configurer `.env`

```bash
# .env
IMAGE_PROVIDER=comfyui
COMFYUI_URL=http://localhost:8188
```

---

## 🧪 Tests : Chicago-style avec Fakes

### Principe : Fakes > Mocks

```python
# features/shared/tests/unit/fakes/fake_cover_port.py
class FakeCoverPort(CoverGenerationPort, ContentPageGenerationPort):
    """Fake provider pour tests (comportement contrôlable)."""

    def __init__(self, mode: str = "succeed", image_size: int = 10000):
        self.mode = mode  # "succeed" | "fail"
        self.image_size = image_size
        self.call_count = 0
        self.last_prompt: str | None = None

    async def generate_cover(self, prompt: str, spec: ImageSpec, seed: int | None = None) -> bytes:
        self.call_count += 1
        self.last_prompt = prompt

        if self.mode == "fail":
            raise DomainError(code=ErrorCode.PROVIDER_TIMEOUT, message="Fake failure")

        # Retourne une image fake (1x1 PNG minimal)
        return b"\x89PNG\r\n..." * (self.image_size // 10)

    async def generate_page(self, prompt: str, spec: ImageSpec, seed: int | None = None) -> bytes:
        return await self.generate_cover(prompt, spec, seed)

    async def remove_text_from_cover(self, cover_bytes: bytes) -> bytes:
        return cover_bytes  # Fake : retourne tel quel
```

### Usage dans un Test

```python
# features/ebook/creation/tests/unit/domain/test_create_ebook.py
async def test_create_ebook_success():
    # Arrange
    fake_cover = FakeCoverPort(mode="succeed", image_size=10000)
    fake_page = FakeCoverPort(mode="succeed", image_size=5000)

    usecase = CreateEbookUseCase(
        cover_port=fake_cover,
        page_port=fake_page,
        repository=FakeEbookRepository(),
        event_bus=FakeEventBus()
    )

    # Act
    ebook = await usecase.execute(theme="Animals", num_pages=10)

    # Assert
    assert ebook.id is not None
    assert fake_cover.call_count == 1  # 1 cover
    assert fake_page.call_count == 10  # 10 pages
```

---

## 📊 Schéma Visuel : Flow de Création d'Ebook

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER REQUEST (FastAPI)                                        │
│    POST /ebooks/create {"theme": "Animals", "num_pages": 10}     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. PRESENTATION LAYER (features/ebook/creation/presentation/)    │
│    CreateEbookRouter.create_ebook()                              │
│    → Dependency Injection (get_create_ebook_usecase())           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. USE CASE (features/ebook/creation/domain/usecases/)           │
│    CreateEbookUseCase.execute()                                  │
│    ├─ Valide inputs                                              │
│    ├─ Appelle strategy.generate()                                │
│    ├─ Persiste ebook via repository                              │
│    └─ Publie EbookCreatedEvent                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ Strategy │  │   Repo   │  │ EventBus │
     │ (Domain) │  │  (Port)  │  │ (Shared) │
     └─────┬────┘  └─────┬────┘  └─────┬────┘
           │             │             │
           ▼             ▼             ▼
   ┌────────────┐  ┌───────────┐  ┌─────────────┐
   │ CoverPort  │  │ DB (Infra)│  │ Event       │
   │ PagePort   │  │           │  │ Handlers    │
   └─────┬──────┘  └───────────┘  └─────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. INFRASTRUCTURE (features/shared/infrastructure/providers/)    │
│    OpenRouterImageProvider.generate_cover()                      │
│    ComfyUIImageProvider.generate_cover()  ← TON COPAIN ICI      │
│    GeminiImageProvider.generate_cover()                          │
│    ├─ Appelle API externe OU local ComfyUI                      │
│    ├─ Post-traite l'image (resize, borders)                     │
│    └─ Retourne bytes                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔥 Points Clés à Retenir

### 1. Pourquoi Multi-héritage sur les Providers ?

**Situation** : OpenRouter utilise **le même modèle** (Gemini 2.5 Flash) pour covers ET pages.
**Solution** : Multi-héritage permet de réutiliser `generate_cover()` pour `generate_page()`.

**Alternative pour ComfyUI** :
- Si ton workflow ComfyUI est **différent** pour covers vs pages → Crée 2 adapters séparés
- Si c'est le **même workflow** → Multi-héritage OK (comme OpenRouter)

**Avantage du multi-héritage** :
- ✅ **DRY** : Pas de duplication de code
- ✅ **Simplicité** : Un seul provider à configurer
- ✅ **Flexibilité** : Les use cases peuvent injecter le port qui les intéresse

**Alternative (composition)** :
```python
class ComfyUICoverProvider(CoverGenerationPort):
    def __init__(self, engine: ComfyUIEngine):
        self.engine = engine

class ComfyUIPageProvider(ContentPageGenerationPort):
    def __init__(self, engine: ComfyUIEngine):
        self.engine = engine
```

Mais si le code est identique, **multi-héritage est plus simple**.

### 2. Où Mettre le Code ?

| Type de Code | Localisation | Exemple |
|--------------|-------------|---------|
| **Use Case** spécifique | `features/<feature>/domain/usecases/` | `CreateEbookUseCase` |
| **Port** (interface) | `features/shared/domain/ports/` | `CoverGenerationPort` |
| **Adapter partagé** | `features/shared/infrastructure/providers/` | `ComfyUIImageProvider` |
| **Adapter spécifique** | `features/<feature>/infrastructure/` | (rare, exemple : `EbookExportAdapter` si utilisé QUE par export/) |
| **Entity** partagée | `features/shared/domain/entities/` | `Ebook`, `ImagePage` |
| **Event** spécifique | `features/<feature>/domain/events/` | `EbookCreatedEvent` |
| **Tests** | À côté du code testé | `features/<feature>/tests/unit/` |

### 3. Communication Entre Features

**❌ Import direct** entre features (couplage fort)
**✅ EventBus** pour communication asynchrone (découplage)

```python
# ❌ BAD - Import direct
from backoffice.features.generation_costs.domain.usecases import TrackCostUseCase

class CreateEbookUseCase:
    async def execute(self, ...):
        await self.track_cost_usecase.execute(...)  # Couplage fort

# ✅ GOOD - Via EventBus
class CreateEbookUseCase:
    async def execute(self, ...):
        event = EbookCreatedEvent(ebook_id=ebook.id, cost=0.15)
        await self.event_bus.publish(event)  # Découplage
```

---

## 🛠️ Commandes Utiles

```bash
# Lancer l'app
make run                          # Port 8001

# Tests
make test                         # Tests unitaires (177 tests, ~1s)
pytest features/ebook/creation/tests/unit -v  # Tests d'une feature spécifique

# Qualité
make lint                         # Ruff linting
make typecheck                    # Mypy type checking
make format                       # Auto-format

# DB
make db-migrate                   # Appliquer les migrations
```

---

## 📚 Ressources

- **Memory Bank** : `aidd-docs/memory-bank/` (documentation structurée pour AI)
- **CLAUDE.md** : Instructions pour Claude Code
- **README.md** : Guide utilisateur

---

## 💬 Pour Ton Copain

**Si tu veux ajouter un provider ComfyUI local** :

1. **Crée le fichier** : `features/shared/infrastructure/providers/comfyui_image_provider.py`
2. **Implémente les ports** : `CoverGenerationPort` + `ContentPageGenerationPort`
3. **Configure l'injection** : Dans `main.py`, ajoute `comfyui` dans les choix de providers
4. **Teste** : Crée un fake dans `features/shared/tests/unit/fakes/fake_comfyui_port.py`

**Pourquoi dans `shared/` ?** → Parce que ce provider sera utilisé par **plusieurs features** (`creation/`, `regeneration/`).

**Questions ?** N'hésite pas à explorer le code ou à poser des questions ! 🚀
