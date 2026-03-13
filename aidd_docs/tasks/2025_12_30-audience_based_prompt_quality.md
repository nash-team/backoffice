# Instruction: Audience-Based Prompt Quality Settings

## Feature

- **Summary**: Add support for audience-specific prompt generation (children vs adults) with different complexity levels while maintaining KDP compliance. Enables generating simpler prompts for kids (4-8) with large shapes and minimal backgrounds, and more detailed prompts for adults with intricate patterns.
- **Stack**: `Python 3.12`, `PyYAML`, `pytest`

## Existing files

- @src/backoffice/features/ebook/shared/domain/services/prompt_template_engine.py
- @config/branding/themes/christmas-creepy-cute.yml

### New file to create

- src/backoffice/features/ebook/shared/domain/services/tests/unit/test_prompt_template_audience.py

## Implementation phases

### Phase 1: Extend PromptTemplate dataclass

> Add support for audience-specific quality settings in the data model

1. Add `AudienceQualityProfile` dataclass with `prefix` and `suffix` fields
2. Add `quality_settings_by_audience: dict[str, AudienceQualityProfile] | None` to `PromptTemplate`
3. Keep existing `quality_settings` field for backward compatibility

### Phase 2: Update YAML parser

> Parse new quality_settings_by_audience structure from theme files

1. Modify `load_template_from_yaml()` to detect and parse `quality_settings_by_audience`
2. Create `AudienceQualityProfile` instances for each audience key (children, adults)
3. Fallback to existing `quality_settings` parsing if new structure absent

### Phase 3: Implement audience selection logic

> Select correct profile based on audience parameter

1. Modify `_generate_single_prompt()` to check for `quality_settings_by_audience`
2. Select profile based on `audience` parameter (default: "children")
3. Build prompt with `prefix + base_prompt + suffix` structure
4. Fallback to existing `quality_settings` behavior when new structure absent
5. Log warning if requested audience profile not found

### Phase 4: Add SECONDARY_ELEMENTS variable support

> Enable optional secondary elements in prompts

1. Add `SECONDARY_ELEMENTS` to theme variables (can include empty string)
2. No code change needed - existing variable substitution handles it

### Phase 5: Migrate pilot theme

> Update christmas-creepy-cute.yml with new structure

1. Define shared KDP constraints (black/white, bold outlines, no colors)
2. Create `children` profile with simple shapes, minimal background, no textures
3. Create `adults` profile with detailed patterns, rich backgrounds, cross-hatching allowed
4. Add `SECONDARY_ELEMENTS` variable with 3-4 small element options
5. Keep existing `quality_settings` as fallback anchor

### Phase 6: Unit tests

> Ensure correct behavior and backward compatibility

1. Test prompt generation with `audience="children"` uses children profile
2. Test prompt generation with `audience="adults"` uses adults profile
3. Test prompt generation with `audience=None` defaults to children
4. Test theme without `quality_settings_by_audience` uses existing `quality_settings`
5. Test missing audience profile falls back to children with warning

## Reviewed implementation

- [ ] Phase 1: Extend PromptTemplate dataclass
- [ ] Phase 2: Update YAML parser
- [ ] Phase 3: Implement audience selection logic
- [ ] Phase 4: Add SECONDARY_ELEMENTS variable support
- [ ] Phase 5: Migrate pilot theme
- [ ] Phase 6: Unit tests

## Validation flow

1. Run `make test` - all existing tests pass (backward compatibility)
2. Generate prompts with `audience="children"` for christmas-creepy-cute theme
3. Verify prompt contains: "Single main character centered", "minimal details", "Kid-friendly, ages 4-7"
4. Generate prompts with `audience="adults"` for same theme
5. Verify prompt contains: "intricate patterns", "detailed", adult-specific constraints
6. Generate prompts for a non-migrated theme (e.g., dinosaurs)
7. Verify existing behavior unchanged (uses quality_settings)

## Estimations

- Confidence: 9/10
  - ✅ Clear requirements with reference prompt
  - ✅ Existing code is well-structured and easy to extend
  - ✅ Backward compatibility straightforward with fallback pattern
  - ✅ No external API changes, internal refactor only
  - ❌ Minor risk: prompt quality depends on YAML content crafting (not code)
