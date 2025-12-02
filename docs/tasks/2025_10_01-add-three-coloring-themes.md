# Instruction: Add 3 New Coloring Book Themes (Animals, Food, Nature)

## Feature

- **Summary**: Add 3 new theme configurations for coloring book generation: Animals (mix of all animal types), Food (mix of all food types), and Nature (mix of natural elements). Remove unused ribbon configuration from theme system.
- **Stack**: `Python 3.11`, `YAML`, `Pydantic 2.x`, `FastAPI`, `Jinja2 Templates`

## Existing files

- @themes/dinosaurs.yml
- @themes/unicorns.yml
- @themes/pirates.yml
- @themes/neutral-default.yml
- @src/backoffice/domain/entities/theme_profile.py
- @src/backoffice/domain/theme_loader.py
- @src/backoffice/infrastructure/adapters/theme_repository.py
- @src/backoffice/presentation/templates/partials/themes_selection.html

### New file to create

- themes/animals.yml
- themes/food.yml
- themes/nature.yml

## Implementation phases

### Phase 1: Create Theme YAML Files

> Add 3 new theme configuration files for coloring books

1. Create `themes/animals.yml` with:
   - ID: `animals`, Label: "Animaux"
   - Palette: earthy/natural colors for animals (browns, greens, warm tones)
   - Prompt blocks: mix of all animals (farm, wild, pets, sea creatures)
   - Subject: cute animal, centered composition
   - Environment: natural habitat appropriate for various animals
   - Tone: fun, educational, kid-friendly
   - Positives: clean lines, simple design, coloring book style
   - Negatives: no text, no mockup, no borders, no complex details

2. Create `themes/food.yml` with:
   - ID: `food`, Label: "Nourriture"
   - Palette: bright, appetizing colors (reds, yellows, greens)
   - Prompt blocks: mix of all food types (fruits, vegetables, desserts, meals)
   - Subject: cute food item, centered composition
   - Environment: simple kitchen or table setting
   - Tone: fun, colorful, appetizing
   - Positives: clean lines, simple shapes, coloring book style
   - Negatives: no text, no mockup, no borders, no realistic textures

3. Create `themes/nature.yml` with:
   - ID: `nature`, Label: "Nature"
   - Palette: natural greens, earth tones, sky blues
   - Prompt blocks: mix of natural elements (trees, flowers, landscapes, seasons)
   - Subject: natural scene or element, centered composition
   - Environment: outdoor natural setting
   - Tone: peaceful, educational, calming
   - Positives: clean lines, simple design, coloring book style
   - Negatives: no text, no mockup, no borders, no photorealistic details

### Phase 2: Remove Ribbon Configuration (Cleanup)

> Remove unused ribbon styling from theme system

1. Update `src/backoffice/domain/entities/theme_profile.py`:
   - Remove `RibbonStyleModel` class (lines 43-58)
   - Remove `RibbonStyle` dataclass (lines 98-104)
   - Remove `ribbon: RibbonStyleModel` field from `ThemeProfileModel`
   - Remove `ribbon: RibbonStyle` field from `ThemeProfile`
   - Update `ThemeProfile.from_model()` to remove ribbon conversion
   - Update `ThemeProfile.to_dict()` to remove ribbon output

2. Update `src/backoffice/domain/theme_loader.py`:
   - Remove ribbon from `_create_hardcoded_fallback()` method
   - Update fallback theme instantiation to remove ribbon parameter

3. Update existing theme YAML files:
   - Remove `ribbon:` section from `themes/dinosaurs.yml`
   - Remove `ribbon:` section from `themes/unicorns.yml`
   - Remove `ribbon:` section from `themes/pirates.yml`
   - Remove `ribbon:` section from `themes/neutral-default.yml`

4. Update tests that reference ribbon:
   - Find all test files using ribbon configuration
   - Remove ribbon assertions/expectations from tests
   - Update test fixtures to not include ribbon data

5. Run tests to ensure no breakage after removal

### Phase 3: Update UI Template Icons (Optional Enhancement)

> Add visual icons for new themes in selection UI

1. Update `src/backoffice/presentation/templates/partials/themes_selection.html`:
   - Add icon mapping for `animals` theme: `fa-paw` or `fa-dog` with `text-warning`
   - Add icon mapping for `food` theme: `fa-utensils` or `fa-apple-alt` with `text-danger`
   - Add icon mapping for `nature` theme: `fa-tree` or `fa-leaf` with `text-success`

## Reviewed implementation

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3

## Validation flow

1. Start development server with `make run`
2. Navigate to ebook creation form
3. Verify 3 new themes appear in theme selection: "Animaux", "Nourriture", "Nature"
4. Create coloring book with "Animaux" theme, verify generation works
5. Create coloring book with "Nourriture" theme, verify generation works
6. Create coloring book with "Nature" theme, verify generation works
7. Verify existing themes still work (dinosaurs, unicorns, pirates)
8. Check that ribbon configuration has been removed without breaking functionality
9. Verify theme icons display correctly in UI for all themes
10. Run full test suite to ensure no regressions

## Estimations

- **Confidence**: 9/10
  - ✅ Theme system is well-structured and documented
  - ✅ YAML schema is clear and validated with Pydantic
  - ✅ Existing themes provide clear examples to follow
  - ✅ No database migrations required (file-based configuration)
  - ✅ Theme loader has caching and fallback mechanisms
  - ❌ Minor risk: removing ribbon might have edge cases in tests
- **Time to implement**: 30-45 minutes
  - Phase 1 (theme files): 15 minutes
  - Phase 2 (ribbon removal): 15-20 minutes
  - Phase 3 (UI icons): 5-10 minutes
  - Testing: 5 minutes
