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
├── ebook_creation/         # New ebook generation workflow
├── ebook_lifecycle/        # Approve/Reject/Stats management
├── ebook_listing/          # Dashboard & pagination
├── ebook_regeneration/     # Back cover regeneration
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

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** (or SQLite for local dev)
- **Docker** (for integration tests with testcontainers)
- **OpenRouter API Key** (for image generation via Gemini)
- **Google Drive API credentials** (optional, for PDF upload)

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repository-url>
cd generatorEbook/backoffice

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Unix/macOS
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
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
# Run migrations (if using Alembic)
make migrate

# Or create tables manually
make db-create
```

### 4. Run the Application

```bash
make run
```

**Access:**
- **Dashboard:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/healthz

---

## Usage

### Generate a Coloring Book

1. **Go to dashboard:** http://localhost:8000
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
make run               # Start server (localhost:8000)
make test              # Run all unit tests (177 tests)
make test-unit         # Run unit tests only
make test-smoke        # Run E2E smoke test (health check)
make lint              # Run ruff linting
make format            # Format code with ruff
make type-check        # Run mypy type checking
make db-create         # Create database tables
make clean             # Remove cache files
```

**Manual commands:**

```bash
# Run specific feature tests
pytest src/backoffice/features/ebook_creation/tests/unit -v

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
│   │   ├── ebook_creation/
│   │   ├── ebook_lifecycle/
│   │   ├── ebook_listing/
│   │   ├── ebook_regeneration/
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
- **Check API credits** at https://openrouter.ai
- **Review logs** in terminal for error messages
- **Verify theme** is supported (dinosaurs, pirates, unicorns, etc.)

---

## Contributing

1. **Create feature branch:** `git checkout -b feature/my-feature`
2. **Write tests first** (TDD recommended)
3. **Run checks:**
   ```bash
   make test
   make lint
   make type-check
   ```
4. **Commit with conventional commits:**
   ```bash
   git commit -m "feat(ebook_creation): add new theme support"
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
