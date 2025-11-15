# Configuration Files

This directory contains all externalized configuration for the ebook generation system.

## 🎯 Philosophy

**All business rules and specifications are defined here, not in Python code.**

This allows non-developers to modify KDP specs, limits, and defaults without touching the codebase.

## 📁 Structure

```
config/
├── generation/
│   └── models.yaml            # ⭐ Model selection (SOURCE OF TRUTH)
│       ├── cover              # Cover generation model
│       └── coloring_page      # Content page generation model
│
├── kdp/
│   └── specifications.yaml    # Amazon KDP specifications
│       ├── formats            # Book formats (square, standard, large)
│       ├── paper_types        # Paper types with spine formulas
│       ├── spine              # Spine width calculations
│       ├── color_profiles     # ICC profiles (RGB)
│       ├── cover              # Cover finishes and barcode specs
│       ├── validation         # File validation rules
│       ├── export             # PDF export settings
│       └── defaults           # Default values used by system
│
├── business/
│   └── limits.yaml            # Business constraints
│       ├── pages              # Min/max page counts
│       ├── formats            # Supported formats
│       ├── engines            # PDF engines
│       └── images             # Image size constraints
│
└── branding/
    ├── identity.yaml          # Brand identity (logo, colors, style)
    └── audiences.yaml         # Target audiences (children, adults)
```

## 🔑 Configuration vs Secrets (.env)

**⚠️ IMPORTANT**: This directory contains **configuration**, NOT secrets!

### What goes where?

**`config/` (YAML files)** - Business Configuration:

- ✅ Which model to use (`openrouter`, `gemini`, `local`)
- ✅ Which specific model (`gemini-2.5-flash-image`, `flux-schnell`, etc.)
- ✅ KDP specifications, business limits, brand identity
- ✅ Safe to commit to git (no secrets)

**`.env` file** - Secrets & API Keys:

- 🔐 `OPENROUTER_API_KEY=sk-or-xxx`
- 🔐 `GEMINI_API_KEY=AIza-xxx`
- 🔐 `HF_API_TOKEN=hf_xxx`
- 🔐 Database passwords, secret keys
- ❌ NEVER commit to git

**Example**: To switch from OpenRouter to Gemini Direct:

1. Edit `config/generation/models.yaml` (change `provider: openrouter` → `provider: gemini`)
2. Add `GEMINI_API_KEY=xxx` to `.env` if not already there
3. Done!

## 🚀 Quick Examples

### Choose your AI provider

**File:** `generation/models.yaml`

```yaml
models:
  cover:
    provider: gemini  # Options: openrouter, gemini, local
    model: gemini-2.5-flash-image
```

See [`generation/models.yaml`](generation/models.yaml) for 150+ lines of examples!

### Change default format from square to standard

**File:** `kdp/specifications.yaml`

```yaml
defaults:
  format: "standard_coloring_book"  # Changed from square_format
```

### Add a new paper type

**File:** `kdp/specifications.yaml`

```yaml
paper_types:
  ultra_premium:
    display_name: "Ultra Premium (80lb)"
    spine_formula: 0.0026
    min_pages: 24
    max_pages: 600
    cost_factor: 1.5
```

### Increase max pages from 30 to 50

**File:** `business/limits.yaml`

```yaml
ebook:
  pages:
    max: 50  # Changed from 30
```

## 🔍 How It Works

### 1. ConfigLoader reads YAML files

```python
from backoffice.config import ConfigLoader

config = ConfigLoader()
trim_size = config.get_kdp_trim_size("square_format")  # (8.5, 8.5)
```

### 2. Validation happens at runtime

```python
# ✅ Valid (defined in YAML)
kdp = KDPExportConfig(paper_type="premium_color")

# ❌ Invalid (not in YAML)
kdp = KDPExportConfig(paper_type="super_premium")
# ValueError: Invalid paper_type: 'super_premium'.
#             Must be one of: premium_color, standard_color, white, cream
```

### 3. Constants load from YAML

```python
from backoffice.features.ebook.shared.domain.constants import MIN_PAGES

print(MIN_PAGES)  # 24 (from business/limits.yaml)
```

## 📐 KDP Specifications

### Available Formats

| Format | Trim Size | Use Case |
|--------|-----------|----------|
| `square_format` | 8.5" × 8.5" | Default coloring books |
| `standard_coloring_book` | 8.0" × 10.0" | Vertical coloring books |
| `large_coloring_book` | 8.5" × 11.0" | Large format books |

### Paper Types

| Type | Display Name | Spine Formula | Cost Factor |
|------|--------------|---------------|-------------|
| `premium_color` | Premium Color (70lb) | 0.002347 | 1.2x |
| `standard_color` | Standard Color (60lb) | 0.002252 | 1.0x |
| `white` | Black & White (55lb) | 0.002252 | 0.8x |
| `cream` | Cream (55lb) | 0.0025 | 0.8x |

### Cover Finishes

| Finish | Cost Factor |
|--------|-------------|
| `glossy` | 1.0x |
| `matte` | 1.1x |

## 📊 Business Limits

### Current Limits

| Constraint | Value | Reason |
|------------|-------|--------|
| Min pages | 24 | KDP minimum for paperback |
| Max pages | 30 | Project limit |
| Cover min pixels | 2550 | 8.5" at 300 DPI |
| Content min pixels | 2175 | 7.25" at 300 DPI |

## 💡 Common Use Cases

### Testing a new format size

1. Add format to `kdp/specifications.yaml`
2. No code changes needed!
3. Use in code: `config.get_kdp_trim_size("my_format")`

### Adjusting validation rules

1. Edit `validation` section in `kdp/specifications.yaml`
2. Changes apply immediately on next run

### Changing defaults for all new books

1. Edit `defaults` section in `kdp/specifications.yaml`
2. All new `KDPExportConfig()` instances use new defaults

## ✅ Testing Changes

After modifying YAML files, always run tests:

```bash
make test-unit  # Should pass (146 tests)
```

## 📚 Full Documentation

See [docs/config_guide.md](../docs/config_guide.md) for detailed examples and best practices.

## 🔧 Technical Details

- **Loader:** `src/backoffice/config/loader.py`
- **Caching:** `@lru_cache(maxsize=32)` for performance
- **Validation:** Runtime validation with clear error messages
- **Type Safety:** Python type hints + runtime checks

---

**Remember: Configuration is code! Keep it clean, documented, and tested. 🎯**
