# Instruction: Add Legal/Copyright Page to KDP Interior Export

## Feature

- **Summary**: Generate a legal/copyright page (white page, Poppins font, title on top, legal mentions at bottom) and insert it as the first page of the KDP interior PDF, before coloring pages. Data comes from theme YAML (title, ISBN) and a new global `config/publishing/legal.yaml` file.
- **Stack**: `Python 3.13`, `Pillow`, `img2pdf`, `PyYAML`, `Pydantic`

## Existing files

- @config/branding/themes/dinosaurs.yml
- @src/backoffice/features/ebook/shared/infrastructure/providers/publishing/kdp/assembly/interior_assembly_provider.py
- @src/backoffice/features/ebook/export/domain/usecases/export_to_kdp_interior.py
- @src/backoffice/features/ebook/shared/domain/entities/theme_profile.py
- @src/backoffice/config/loader.py
- @src/backoffice/features/ebook/shared/infrastructure/providers/publishing/kdp/utils/spine_generator.py

### New file to create

- config/publishing/legal.yaml
- src/backoffice/features/ebook/shared/infrastructure/providers/publishing/kdp/utils/legal_page_generator.py

## Implementation phases

### Phase 1: Configuration

> Add legal data sources (YAML + theme title field)

1. Create `config/publishing/legal.yaml` with copyright, publisher, printing, legal_deposit fields
2. Add `title: "Coloro Dino"` field to `dinosaurs.yml` (top-level, next to `label`)
3. Add `title` field to `ThemeProfileModel` and `ThemeProfile` dataclass (optional, defaults to `label`)
4. Add `load_legal_config()` method to `ConfigLoader`

### Phase 2: Legal Page Generator

> Pillow-based page image generator (same pattern as spine_generator.py)

1. Create `legal_page_generator.py` with a `generate_legal_page()` function
2. Input: title (str), isbn (str|None), legal config (dict), page dimensions (width_px, height_px)
3. Output: PNG bytes (RGB, 300 DPI) - white background, black text, Poppins font
4. Layout: title centered top, legal block centered bottom

### Phase 3: Integration into KDP Interior Assembly

> Insert legal page as first interior page

1. In `KDPInteriorAssemblyProvider.assemble_kdp_interior()`, load theme and legal config
2. Generate legal page image via `generate_legal_page()`
3. Prepend legal page bytes to `processed_images` list (before content pages, after cover exclusion)
4. Legal page counts toward KDP page count (affects auto-padding logic)

### Phase 4: Tests

> Unit tests with fakes, Chicago-style

1. Test `generate_legal_page()` returns valid PNG with correct dimensions
2. Test `generate_legal_page()` with ISBN=None omits ISBN line
3. Test `KDPInteriorAssemblyProvider` includes legal page as first interior page
4. Test legal page counts in total page count for KDP validation

## Reviewed implementation

- [ ] Phase 1: Configuration
- [ ] Phase 2: Legal Page Generator
- [ ] Phase 3: Integration into KDP Interior Assembly
- [ ] Phase 4: Tests

## Validation flow

1. Run `make test` - all existing tests still pass
2. Run new unit tests for legal page generator
3. Export a dinosaurs ebook via KDP interior endpoint
4. Open exported PDF and verify legal page is page 1 (after cover)
5. Verify title "Coloro Dino" at top, legal mentions at bottom, Poppins font, correct dimensions

## Estimations

- Confidence: 9/10
  - Existing Pillow pattern in spine_generator.py is directly reusable
  - ConfigLoader pattern is well-established
  - Interior assembly provider has clear insertion point (prepend to `processed_images`)
  - Risk: font path resolution (Poppins is in `config/branding/fonts/`, not in the same path as spine generator's PlayfairDisplay)
- Time to implement: ~1h
