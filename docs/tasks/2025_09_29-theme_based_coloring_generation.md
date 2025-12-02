# Instruction: Theme-based Coloring Book Generation System

## Feature

- **Summary**: Replace manual prompt input with predefined theme selection for coloring books, implementing a declarative prompt building system with YAML-based configuration. The feature simplifies user experience by reducing form complexity to 3 core fields (Theme, Type, Age) while maintaining backward compatibility for story books.
- **Stack**: `FastAPI 0.104+`, `SQLAlchemy 2.0+`, `Pydantic 2.0+`, `PyYAML 6.0+`, `Alembic`, `WeasyPrint`, `OpenAI API`, `PostgreSQL`, `Jinja2`, `HTMX`

## Existing files

- @src/backoffice/domain/entities/ebook.py
- @src/backoffice/domain/entities/ebook_theme.py
- @src/backoffice/domain/usecases/generate_coloring_pages.py
- @src/backoffice/infrastructure/adapters/openai_image_generator.py
- @src/backoffice/infrastructure/models/ebook_model.py
- @src/backoffice/presentation/templates/partials/enhanced_ebook_form.html
- @src/backoffice/presentation/templates/pages/covers/cover_coloring.html

### New file to create

- /themes/dinosaurs.yml
- /themes/unicorns.yml
- /themes/pirates.yml
- /themes/neutral-default.yml
- @src/backoffice/domain/entities/theme_profile.py
- @src/backoffice/domain/services/theme_loader.py
- @src/backoffice/domain/services/prompt_builder.py
- @src/backoffice/infrastructure/adapters/theme_repository.py

## Implementation phases

### Phase 1: Domain Model Enhancement

> Create theme-based domain entities and YAML configuration system

1. Create theme configuration directory structure (/themes/)
2. Define theme YAML schema with Pydantic validation models
3. Implement ThemeProfile, Palette, PromptBlocks, RibbonStyle dataclasses
4. Create theme loader service with YAML parsing and validation
5. Build prompt builder service with declarative pipeline composition
6. Add fallback mechanism for invalid/missing themes

### Phase 2: Infrastructure Integration

> Integrate theme system into existing database and adapters

1. Add theme metadata fields to ebook database model (theme_id, theme_version, audience)
2. Create and run database migration for new fields
3. Update ebook repository to handle theme metadata storage/retrieval
4. Modify OpenAI image generator to use theme-based prompts for coloring books
5. Update ribbon rendering system to apply theme-specific styling
6. Create theme repository adapter for loading and caching themes

### Phase 3: User Interface Modifications

> Replace manual prompt with theme selector for coloring books

1. Add theme selector dropdown to ebook creation form for coloring type
2. Hide prompt textarea when coloring book type is selected
3. Add age selector with fixed ranges (3-5, 6-8, 9-12 years)
4. Update form validation to require theme selection for coloring books
5. Modify form submission to include theme and age data
6. Update Alpine.js form logic to handle theme-based workflow

### Phase 4: Business Logic Updates

> Connect theme system to ebook generation workflow

1. Update GenerateColoringPagesUseCase to use theme-based prompt generation
2. Modify ebook creation workflow to handle theme selection and storage
3. Update cover generation to apply theme-specific styling and ribbon configuration
4. Implement age-appropriate content adjustments in prompt building
5. Ensure backward compatibility maintained for story book generation

### Phase 5: Testing and Validation

> Create initial themes and comprehensive test coverage

1. Create initial theme YAML files (dinosaurs, unicorns, pirates, neutral-default)
2. Update existing unit tests to handle theme-based generation workflow
3. Add new tests for theme loading, validation, and prompt building
4. Test fallback mechanisms for invalid themes and error conditions
5. Add E2E tests for complete theme-based coloring book creation flow

## Reviewed implementation

- [ ] Phase 1: Domain Model Enhancement
- [ ] Phase 2: Infrastructure Integration
- [ ] Phase 3: User Interface Modifications
- [ ] Phase 4: Business Logic Updates
- [ ] Phase 5: Testing and Validation

## Validation flow

1. Navigate to ebook creation page and select "Coloriage" type
2. Verify prompt field is hidden and theme selector appears
3. Select a theme (dinosaurs, unicorns, or pirates) from dropdown
4. Choose age range (3-5, 6-8, or 9-12 years)
5. Set number of coloring pages and other basic options
6. Submit form and verify ebook creation starts with theme-based generation
7. Check generated PDF has theme-appropriate images and neutral ribbon styling
8. Verify theme metadata is stored correctly in database
9. Test fallback behavior by temporarily removing a theme file
10. Confirm story book creation still uses manual prompt system unchanged

## Estimations

- **Confidence**: 9/10
- **Time to implement**: 2-3 days

**High confidence reasons:**
- ✅ Clear separation of concerns with hexagonal architecture
- ✅ Existing domain entities and use cases provide solid foundation
- ✅ YAML-based configuration is simple and well-supported
- ✅ Form modification is straightforward with existing HTMX setup
- ✅ Database migration is minimal and non-breaking

**Risk mitigation:**
- ❌ Theme YAML parsing errors handled with fallback system
- ❌ Backward compatibility ensured by type-based conditional logic
- ❌ Performance impact minimal due to theme caching strategy