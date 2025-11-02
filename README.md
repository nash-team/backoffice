# Ebook Generator - Amazon KDP Coloring Books

> **Automated coloring book generation for Amazon KDP** - Generate, validate, and publish professional coloring books ready for print-on-demand sales.

## What is this?

This tool **generates complete coloring books** (dinosaurs, pirates, unicorns, etc.) ready to sell on **Amazon KDP** (Kindle Direct Publishing). It automates:

- **Cover generation** (full color with title)
- **Content pages** (black & white line art for coloring)
- **Back cover generation** (text-removed line art)
- **PDF assembly** (KDP-ready format: 8×10", 300 DPI, bleed margins)
- **Quality validation** (editorial approval workflow)
- **Cost tracking** (API costs per generation)

**Use case:** Create professional coloring books in minutes instead of weeks, ready for Amazon print-on-demand.

---

## Key Features

### 🎨 AI-Powered Generation

- **Gemini 2.5 Flash Image Preview** via OpenRouter for high-quality illustrations
- **Potrace vectorization** for clean line art conversion
- **Seed-based generation** for reproducible results
- **Batch processing** with quality checks

### 📚 KDP-Compliant Output

- **Trim size:** 8.0" × 10.0" (203mm × 254mm)
- **Bleed:** 0.125" (3.175mm) on all sides
- **Resolution:** 300 DPI (print quality)
- **Format:** PDF ready for Amazon upload
- **Page count:** 24-30 pages (customizable)

### 🔄 Editorial Workflow

- **Dashboard:** View all generated ebooks with stats
- **Status tracking:** DRAFT → APPROVED → PUBLISHED → REJECTED
- **Preview:** In-browser PDF preview
- **Regeneration:** Regenerate back cover if needed
- **Drive integration:** Upload approved PDFs to Google Drive

### 💰 Cost Management

- **Per-ebook tracking:** Track API costs for each generation
- **Statistics dashboard:** Total costs, average per book
- **Provider logs:** Detailed cost breakdown per API call

---

## Architecture

**100% Feature-Based Architecture** (Screaming Architecture + Hexagonal Architecture)

```
src/backoffice/features/
├── ebook/creation/         # New ebook generation workflow
├── ebook/lifecycle/        # Approve/Reject/Stats management
├── ebook/listing/          # Dashboard & pagination
├── ebook/regeneration/     # Back cover regeneration
├── generation_costs/       # Cost tracking & analytics
└── shared/                 # Shared domain & infrastructure
    ├── domain/             # Entities, ports, services (Ebook, ImagePage, etc.)
    ├── infrastructure/     # Adapters (DB, APIs, file storage)
    ├── presentation/       # FastAPI routes, Jinja2 templates, static assets
    └── tests/              # Shared test utilities
```

**Tests co-localized:** Each feature has its own `tests/unit/` and `tests/integration/` directories.

**Current status:** ✅ 177 tests passing (137 unit, 40 integration disabled)

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation.

---

## Configuration

All configuration is externalized in YAML files under `config/`:

```
config/
├── branding/
│   ├── audiences.yaml         # Target audiences (children, adults)
│   ├── identity.yaml          # Brand identity, colors, mascot
│   └── themes/                # ✨ Coloring book themes
│       ├── dinosaurs.yml
│       ├── pirates.yml
│       ├── unicorns.yml
│       └── neutral-default.yml
├── business/
│   └── limits.yaml            # Page limits, formats, defaults
├── generation/
│   └── models.yaml            # AI model configuration
└── kdp/
    └── specifications.yaml    # Amazon KDP specs (trim, bleed, DPI)
```

**Key points:**

- **Themes** define prompts, palettes, and style guidelines for each coloring book type
- **Audiences** control complexity (simple for children, detailed for adults)
- **KDP specs** ensure compliance with Amazon printing requirements
- All config is validated at runtime and cached for performance

---

## Testing & Development with YAML Themes

### Available Themes

The system comes with 4 pre-configured themes in `config/branding/themes/`:

- **`dinosaurs.yml`** - Prehistoric creatures, jungle environments
- **`pirates.yml`** - Maritime adventures, treasure hunting
- **`unicorns.yml`** - Magical fantasy, rainbows
- **`neutral-default.yml`** - Fallback theme for generic content

### Theme File Structure

Each theme YAML file contains three main sections:

```yaml
id: dinosaurs                           # Unique identifier
label: "Dinosaurs"                      # Display name in UI

# Color palette for cover generation
palette:
  base: ["#35654d", "#6a8f49", "#e0b46b"]
  accents_allowed: ["#ffd166"]
  forbidden_keywords: ["rainbow", "neon"]

# Cover generation prompt (full-color cover)
prompt_blocks:
  subject: "a cute but majestic T-Rex dinosaur"
  environment: "lush jungle, tropical plants"
  tone: "adventurous, exciting, kid-friendly"
  positives: ["highly detailed", "professional"]
  negatives: ["no text", "no borders"]

# Content pages generation (B&W line art)
coloring_page_templates:
  base_structure: "Line art coloring page of a {SPECIES} {ACTION} in a {ENV}..."

  variables:
    SPECIES: ["T-Rex", "Triceratops", "Diplodocus"]
    ACTION: ["roaring", "eating leaves", "running"]
    ENV: ["lush jungle", "volcanic plain"]
    SHOT: ["close-up", "medium", "wide"]
    FOCUS: ["head", "full body", "group of 2-3"]
    COMPOSITION: ["left-facing", "right-facing", "front"]

  quality_settings: |
    Black and white line art only.
    Bold clean outlines, closed shapes, thick black lines.
    No frame, no border around the illustration.
    Printable 300 DPI, simple to medium detail for kids.
```

### Creating a New Theme

**Step 1: Copy an existing theme**

```bash
cp config/branding/themes/dinosaurs.yml config/branding/themes/robots.yml
```

**Step 2: Edit the new theme file**

Open `config/branding/themes/robots.yml` and modify:

1. **ID and Label:**

   ```yaml
   id: robots
   label: "Robots"
   ```

2. **Color Palette:**

   ```yaml
   palette:
     base: ["#2e3440", "#5e81ac", "#88c0d0"]  # Cool metallic blues
     accents_allowed: ["#ebcb8b"]              # Yellow/gold accents
     forbidden_keywords: ["organic", "natural"]
   ```

3. **Cover Prompts:**

   ```yaml
   prompt_blocks:
     subject: "a friendly robot with LED eyes"
     environment: "futuristic city, digital background"
     tone: "innovative, tech-forward, kid-friendly"
   ```

4. **Variables for Coloring Pages:**

   ```yaml
   variables:
     SPECIES: ["humanoid robot", "flying drone", "robot dog"]
     ACTION: ["waving", "computing", "building"]
     ENV: ["futuristic lab", "space station", "robot factory"]
   ```

**Step 3: Test your new theme**

```bash
# Start the server
make run

This allows you to:
- Test theme configurations instantly
- Iterate on prompt structures without cost
- Verify YAML syntax and structure
- Debug template variables

### Modifying Existing Themes

**Common modifications:**

1. **Add new dinosaur species:**
   ```yaml
   # In config/branding/themes/dinosaurs.yml
   variables:
     SPECIES:
       - "T-Rex"
       - "Spinosaurus"  # ← Add new species here
   ```

2. **Adjust line art complexity:**

   ```yaml
   quality_settings: |
     Printable 300 DPI, VERY SIMPLE detail for kids age 3-5.  # ← Simpler
     # Or:
     Printable 300 DPI, HIGHLY DETAILED for adults.           # ← More complex
   ```

3. **Change color palette:**

   ```yaml
   palette:
     base: ["#your-hex-color", "#another-color"]
   ```

### Debugging Theme Issues

**Theme not appearing in dropdown:**

```bash
# Check logs when starting server
make run

# Look for: "Loaded theme: your-theme-name"
# If not found, check YAML syntax
```

**Common YAML errors:**

- ❌ Using tabs instead of spaces (use 2 spaces)
- ❌ Missing required fields (`id`, `label`, `prompt_blocks`)
- ❌ Invalid hex color codes (must be `#RRGGBB`)
- ❌ Unquoted strings with special characters

**Validate YAML syntax:**

```bash
# Use Python to check YAML validity
python -c "import yaml; yaml.safe_load(open('config/branding/themes/your-theme.yml'))"
```

**Theme loads but generation fails:**

1. Check that all `{VARIABLES}` in `base_structure` have corresponding lists
2. Verify `quality_settings` prompt is clear and specific
3. Test with `USE_FAKE_*` variables first to isolate issues

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** (or SQLite for local dev)
- **Docker & Docker Compose** (optional, for containerized development)
- **OpenRouter API Key** (for image generation via Gemini)
- **Google Drive API credentials** (optional, for PDF upload)

---

## 🐳 Docker Setup (Recommended for Teams)

Docker Compose provides an isolated, reproducible environment with PostgreSQL included.

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd backoffice

# 2. Copy environment variables
cp .env.example .env
# Edit .env and add your API keys (GEMINI_API_KEY, LLM_API_KEY)

# 3. Build and start services
make docker-up
# Or manually: docker compose up -d

# 4. Access the application
open http://localhost:8001
```

### Docker Commands

```bash
# Build images
make docker-build

# Start services (detached)
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down

# Open shell in app container
make docker-shell

# Run tests inside container
make docker-test

# Clean everything (removes volumes)
make docker-clean
```

### What's Included

- **PostgreSQL 15** (exposed on port 5432)
- **Application** (exposed on port 8001)
- **Automatic migrations** on startup
- **Hot reload** (source code mounted as volume)

### Configuration

The `docker-compose.yml` uses environment variables from your `.env` file. Key variables:

```env
# Database (configured automatically in docker-compose.yml)
DATABASE_URL=postgresql://backoffice:dev_password@postgres:5432/backoffice_dev

# Security (auto-generated in docker-compose.yml for dev)
SECRET_KEY=dev-secret-key-change-in-production

# API Keys (REQUIRED - add your own keys)
GEMINI_API_KEY=your_gemini_key_here
LLM_API_KEY=your_openrouter_key_here

# Feature flags for testing
USE_FAKE_PROVIDERS=false  # Set to "true" to skip real API calls
```

**Note**: The Docker setup works out-of-the-box with default values. You only need to add your API keys if you want to test real image generation.

---

## Quick Start (Local Development)

### 1. Clone & Install

```bash
git clone <repository-url>
cd generatorEbook/backoffice

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Unix/macOS
# or
.\venv\Scripts\activate   # Windows
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ebook_db

# OpenRouter API (for image generation)
OPENROUTER_API_KEY=your_openrouter_key_here

# Google Drive (optional)
GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# Environment
ENVIRONMENT=development
```

### 3. Setup Database

```bash
# Run Alembic migrations to create/update database tables
make db-migrate

# Check current migration status
make db-status
```

**Note:** The `make db-migrate` command will automatically create all necessary tables based on SQLAlchemy models.

### 4. Run the Application

```bash
make run
```

**Access:**

- **Dashboard:** <http://localhost:8001>
- **API Docs:** <http://localhost:8001/docs>
- **Health Check:** <http://localhost:8001/healthz>

---

## Usage

### Generate a Coloring Book

1. **Go to dashboard:** <http://localhost:8001>
2. **Click "Create New Ebook"**
3. **Fill the form:**
   - Title (e.g., "Dinosaur Adventure Coloring Book")
   - Author name
   - Theme (e.g., "dinosaurs")
   - Number of pages (24-30)
   - Seed (for reproducibility, optional)
4. **Submit** → Generation starts (takes 2-5 minutes)
5. **View in dashboard** when DRAFT status appears

### Review & Approve

1. **Preview PDF** in browser
2. **Approve** → Status changes to APPROVED, PDF uploaded to Drive
3. **Reject** → Add feedback, mark for revision
4. **Regenerate back cover** if needed (removes text from cover)

### Track Costs

- **Stats page:** View total generation costs
- **Per-ebook costs:** See cost breakdown in ebook details

---

## Development Commands

**Available via `make`:**

```bash
make help              # Show all commands
make run               # Start server (localhost:8001)
make test              # Run all unit tests (177 tests)
make test-unit         # Run unit tests only
make test-smoke        # Run E2E smoke test (health check)
make lint              # Run ruff linting
make format            # Format code with ruff
make typecheck         # Run mypy type checking
make db-migrate        # Run database migrations
make db-status         # Show migration status
make clean             # Remove cache files
```

**Manual commands:**

```bash
# Run specific feature tests
pytest src/backoffice/features/ebook/creation/tests/unit -v

# Run integration tests (requires Docker)
pytest src/backoffice/features/*/tests/integration -v

# Run with coverage
pytest --cov=src/backoffice --cov-report=html
```

---

## Project Structure

```
generatorEbook/backoffice/
├── src/backoffice/
│   ├── features/              # Feature modules (100% of code)
│   │   ├── ebook/creation/
│   │   ├── ebook/lifecycle/
│   │   ├── ebook/listing/
│   │   ├── ebook/regeneration/
│   │   ├── generation_costs/
│   │   └── shared/
│   └── main.py                # FastAPI application entry point
├── tests/
│   ├── e2e/                   # End-to-end smoke tests
│   ├── fixtures/              # Shared test fixtures
│   └── conftest.py            # Pytest configuration
├── ARCHITECTURE.md            # Detailed technical documentation
├── CLAUDE.md                  # AI assistant context
├── Makefile                   # Development commands
├── pytest.ini                 # Pytest configuration
├── pyproject.toml             # Ruff configuration
└── requirements.txt           # Python dependencies
```

---

## Testing Strategy

**Chicago-style testing** (fakes > mocks):

- **Unit tests (137):** Fast, use fake implementations (no I/O)
- **Integration tests (40):** PostgreSQL via testcontainers
- **E2E tests (1):** Minimal smoke test (health check only)

**Co-localized tests:** Each feature has tests beside the code.

**Run tests:**

```bash
make test       # All unit tests (~5s)
make test-smoke # E2E smoke test (~10s)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for testing philosophy.

---

## Technology Stack

| Category | Technology |
|----------|-----------|
| **Framework** | FastAPI (async Python web framework) |
| **Database** | PostgreSQL + SQLAlchemy (async ORM) |
| **AI Generation** | OpenRouter API (Gemini 2.5 Flash) |
| **Vectorization** | Potrace (PNG → SVG line art) |
| **PDF Generation** | WeasyPrint (HTML/CSS → PDF) |
| **File Storage** | Google Drive API |
| **Templates** | Jinja2 (with HTMX for dynamic UI) |
| **Testing** | pytest + pytest-asyncio + Playwright |
| **Type Checking** | mypy (via type hints) |
| **Linting** | ruff (linting + formatting) |

---

## Troubleshooting

### Server won't start

```bash
# Check database connection
psql -U user -d ebook_db

# Check environment variables
cat .env

# Check logs
make run  # Look for error messages
```

### Tests failing

```bash
# Unit tests should pass without Docker
make test-unit

# Integration tests require Docker
docker ps  # Check if Docker is running
make test-integration  # (currently disabled due to migration)
```

### Generation fails

- **Check OpenRouter API key** in `.env`
- **Check API credits** at <https://openrouter.ai>
- **Review logs** in terminal for error messages
- **Verify theme** is supported (check `config/branding/themes/` for available themes)

---

## Contributing

1. **Create feature branch:** `git checkout -b feature/my-feature`
2. **Write tests first** (TDD recommended)
3. **Run checks:**

   ```bash
   make test
   make lint
   make typecheck
   ```

4. **Commit with conventional commits:**

   ```bash
   git commit -m "feat(ebook/creation): add new theme support"
   ```

5. **Push and create PR**

See [ARCHITECTURE.md](ARCHITECTURE.md) for architecture guidelines.

---

## License

[Add your license here]

---

## Support

- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Questions:** Open a discussion or issue

---

**Made for creators who want to automate coloring book generation for Amazon KDP.**
