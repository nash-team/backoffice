# Code Review for Cover Title & Footer Image Overlay

Feature adds the ability to overlay transparent PNG images (title and footer) onto AI-generated coloring book covers. Applies to all 3 cover generation paths (creation, regeneration, preview). Title images are per-theme, footer image is shared. KDP safe-zone margins are respected (113px padding).

- Statuts: **APPROVED with minor remarks**
- Confidence: **HIGH** (292 tests passing, all feature paths covered)

## Main expected Changes

- [x] `CoverCompositor` domain service for PNG overlay with Pillow
- [x] `cover_title_image` / `cover_footer_image` fields in theme model + entity
- [x] All 6 theme YAMLs updated with paths and "without text" in comfy prompts
- [x] Compositor integrated in `ColoringBookStrategy.generate()`
- [x] Compositor integrated in `RegenerateCoverUseCase`
- [x] Compositor integrated in `PreviewRegenerateCoverUseCase`
- [x] `FakeCoverPort` returns valid PNG (gradient, >1KB)
- [x] 5 new tests for `CoverCompositor`
- [x] Existing test assertions updated

## Scoring

### Potentially Unnecessary Elements

- [🟢] No dead code or unused imports detected in new files

### Standards Compliance

- [🟢] **Naming conventions followed** — `CoverCompositor`, `compose_cover()`, `_fit_width()` all match project patterns
- [🟢] **Type hints complete** — All function signatures have full type annotations
- [🟢] **Coding rules ok** — ruff, mypy, pre-commit all passing
- [🟡] **Inconsistent compositor instantiation**: [regenerate_cover.py:115](src/backoffice/features/ebook/regeneration/domain/usecases/regenerate_cover.py#L115) and [preview_regenerate_cover.py:123](src/backoffice/features/ebook/regeneration/domain/usecases/preview_regenerate_cover.py#L123) create `CoverCompositor()` inline via lazy import, while [coloring_book_strategy.py:71](src/backoffice/features/ebook/creation/domain/strategies/coloring_book_strategy.py#L71) receives it as constructor dependency. Ideally all 3 paths would use DI for testability consistency. Low priority since compositor is stateless.

### Architecture

- [🟢] **Feature-based structure respected** — New service in `shared/domain/services/`, tests co-localized
- [🟢] **Proper separation of concerns** — Compositor only handles image composition, theme loading stays in ThemeRepository
- [🟢] **DI in strategy** — `CoverCompositor` is injectable via constructor with sensible default
- [🟡] **Lazy imports in use cases**: [preview_regenerate_cover.py:81-86](src/backoffice/features/ebook/regeneration/domain/usecases/preview_regenerate_cover.py#L81-L86) and [regenerate_cover.py:77-83](src/backoffice/features/ebook/regeneration/domain/usecases/regenerate_cover.py#L77-L83) use inline `from ... import` for `ThemeRepository` and `workflow_helper`. These were pre-existing but the new compositor import at [preview_regenerate_cover.py:123](src/backoffice/features/ebook/regeneration/domain/usecases/preview_regenerate_cover.py#L123) follows the same pattern. Not blocking — moving these to top-level would be cleaner but is a pre-existing concern.
- [🟡] **Code duplication across 3 cover paths**: The compositor overlay block (load theme_profile, check if paths non-empty, call `compose_cover`) is repeated in 3 places with identical logic. Consider extracting a small helper (e.g. `apply_cover_overlays(cover_data, theme_id, theme_repo)`) to reduce duplication. Low priority.

### Code Health

- [🟢] **Function sizes** — `compose_cover()` is 40 lines, `_fit_width()` is 5 lines. Clean and focused.
- [🟢] **No magic numbers** — KDP constants are named (`KDP_SAFE_ZONE_INCHES`, `KDP_BLEED_INCHES`, `COVER_DPI`, `PADDING_PX`) with calculation formula in comment
- [🟢] **Error handling** — Missing overlay files are gracefully skipped with `logger.warning()`, no crash
- [🟢] **Cyclomatic complexity** — Low, clean conditionals
- [🟡] **`assert` in production code**: [regenerate_cover.py:72](src/backoffice/features/ebook/regeneration/domain/usecases/regenerate_cover.py#L72) and [preview_regenerate_cover.py:62](src/backoffice/features/ebook/regeneration/domain/usecases/preview_regenerate_cover.py#L62) use `assert ebook.structure_json is not None`. Pre-existing pattern, but `assert` can be stripped by `-O` flag. Consider replacing with explicit DomainError raise.

### Security

- [🟢] No SQL injection risks (no raw SQL)
- [🟢] No XSS vulnerabilities (no user-rendered HTML)
- [🟢] No authentication flaws (feature is internal service layer)
- [🟢] No data exposure points
- [🟡] **Path traversal**: [cover_compositor.py:49-50](src/backoffice/features/ebook/shared/domain/services/cover_compositor.py#L49-L50) opens files from paths stored in YAML configs. Since these paths come from developer-controlled YAML files (not user input), the risk is minimal. However, if in the future YAML themes become user-configurable, this would need path validation.

### Error management

- [🟢] Missing overlay files → warning log + skip (graceful degradation)
- [🟢] Invalid/corrupt PNG in overlay → Pillow raises `UnidentifiedImageError`, which will bubble up naturally
- [🟢] `_make_fake_png()` cache prevents test performance regression

### Performance

- [🟢] `_fit_width()` uses `Image.LANCZOS` for quality downsampling
- [🟢] Fake PNG cached with `_FAKE_PNG_CACHE` global to avoid regenerating 500x500 gradient per test
- [🟢] Compositor opens base image once, overlays in-place, saves once
- [🟡] **RGBA conversion**: [cover_compositor.py:37](src/backoffice/features/ebook/shared/domain/services/cover_compositor.py#L37) always converts base to RGBA. Since the final output is PNG this is fine, but the additional alpha channel increases memory for large covers (2626x2626x4 = ~26MB). Negligible for batch sizes of 1.

### Backend specific

#### Logging

- [🟢] Logging implemented — compositor logs overlay positions and sizes at INFO level, missing files at WARNING

### Tests

- [🟢] **5 new tests** for CoverCompositor covering: both overlays, title centering, footer positioning, missing files, oversized resize
- [🟢] **FakeCoverPort** now returns valid PNG (gradient pattern, >1KB) — proper Chicago-style fake
- [🟢] **Existing test assertions updated** — replaced exact byte-size checks (`== 10000`, `== 12000`) with threshold checks (`> 1024`, `> 0`)
- [🟡] **No compositor unit test in regeneration**: The compositor integration in `RegenerateCoverUseCase` and `PreviewRegenerateCoverUseCase` is not directly tested. The cover generation tests pass because `FakeCoverPort` returns valid PNG, but there's no assertion that the compositor was called. Low priority since compositor itself is well-tested.

## Final Review

- **Score**: 8.5/10
- **Feedback**: Solid implementation. Clean Pillow-based compositor with KDP-compliant padding. All 3 cover paths are covered. Tests are thorough for the new service. Good use of existing project patterns (fakes, co-located tests, domain service).
- **Follow-up Actions**:
  1. (Optional) Extract duplicated compositor overlay block into a shared helper
  2. (Optional) Move lazy imports to top-level in regeneration use cases
  3. (Future) Add path validation if theme YAMLs ever become user-editable
  4. (Future) Replace `assert` with explicit `DomainError` in production code
- **Additional Notes**: The "without text, no letters, no words" suffix added to comfy prompts in all 6 theme YAMLs is the correct approach — prompt lives in theme config, not in Python code. Asset directories (`config/branding/assets/`, `config/branding/themes/assets/`) are created but PNG files need to be provided by the user before the compositor will have any visible effect.
