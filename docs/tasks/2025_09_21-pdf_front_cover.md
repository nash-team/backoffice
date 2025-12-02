# Instruction: Add PDF Front Cover Generation

## Feature

- **Summary**: Add professional front cover as first page of generated PDF ebooks with configurable title, author display and fallback handling
- **Stack**: `Python 3.11`, `FastAPI 0.104+`, `WeasyPrint 61.0+`, `Jinja2 3.1+`, `Pydantic 2.4+`

## Existing files

- @src/backoffice/domain/entities/ebook.py
- @src/backoffice/domain/entities/ebook_structure.py
- @src/backoffice/infrastructure/services/pdf_generator.py
- @src/backoffice/infrastructure/adapters/pdf_generator_adapter.py
- @src/backoffice/presentation/templates/ebook_base.html

### New file to create

- src/backoffice/presentation/templates/cover.html
- src/backoffice/presentation/static/css/cover.css
- src/backoffice/domain/services/cover_generator.py

## Implementation phases

### Phase 1: Configuration Extension

> Extend EbookConfig to support cover options and title handling logic

1. Add cover fields to EbookConfig (enabled, title_override, title_max_lines)
2. Add DEFAULT_AUTHOR constant and title generation algorithms
3. Update domain entities validation and backward compatibility
4. Add slug generation utility function

### Phase 2: Cover Template Creation

> Create responsive HTML/CSS template for cover page

1. Create cover.html Jinja2 template with responsive title handling
2. Implement CSS with clamp sizing and line clamping for long titles
3. Add fallback styling for missing information cases
4. Test template rendering with various title lengths

### Phase 3: Cover Generation Service

> Implement cover generation logic with fallback handling

1. Create CoverGenerator service with title algorithm logic
2. Implement automatic title extraction from first chapter
3. Add comprehensive error handling and warning generation
4. Create cover HTML rendering with template integration

### Phase 4: PDF Integration

> Integrate cover generation into existing PDF workflow

1. Modify PDFGeneratorAdapter to call cover generation
2. Update HTML assembly to prepend cover page before content
3. Adjust WeasyPrint page breaks and pagination
4. Add warning collection and JSON response integration

## Reviewed implementation

- [ ] Phase 1: Configuration Extension
- [ ] Phase 2: Cover Template Creation
- [ ] Phase 3: Cover Generation Service
- [ ] Phase 4: PDF Integration

## Validation flow

1. Generate PDF with standard title/author - verify cover appears as first page
2. Generate PDF with missing author - verify "Assistant IA" appears on cover
3. Generate PDF with missing title - verify auto-generated title from first chapter
4. Generate PDF with very long title - verify responsive sizing and line clamping
5. Test cover generation failure - verify PDF continues without cover + warning in response
6. Verify backward compatibility with existing PDFs when cover disabled

## Estimations

- High confidence (9/10) - CSS/pagination details to be handled during implementation
- 4-6 hours implementation time