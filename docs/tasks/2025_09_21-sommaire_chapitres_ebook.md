# Instruction: Ajout sommaire automatique et séparation chapitres pour génération ebook

## Feature

- **Summary**: Améliorer la génération d'ebook avec un sommaire automatique et la séparation de chaque chapitre sur une page distincte pour des contenus courts (histoires, coloriages), incluant options de personnalisation
- **Stack**: `Python 3.11`, `FastAPI`, `WeasyPrint`, `Jinja2`, `CSS3`, `OpenAI API`, `Google Drive API`

## Existing files

- @src/backoffice/infrastructure/adapters/openai_ebook_processor.py
- @src/backoffice/infrastructure/services/openai_service.py
- @src/backoffice/infrastructure/adapters/sources/google_drive_adapter.py
- @src/backoffice/domain/entities/ebook.py

### New file to create

- src/backoffice/infrastructure/services/pdf_generator.py
- src/backoffice/infrastructure/templates/ebook_base.html
- src/backoffice/infrastructure/templates/ebook_styles.css
- src/backoffice/domain/services/content_parser.py

## Implementation phases

### Phase 1

> Setup PDF generation infrastructure and base templates

1. Add WeasyPrint dependency to pyproject.toml
2. Create PDFGenerator service with WeasyPrint (flexible architecture for future engines)
3. Develop base HTML/CSS templates for ebook layout
4. Add PDF generation options to Ebook entity (engine, format, toc settings)

### Phase 2

> Implement automatic table of contents generation

1. Create ContentParser service to extract chapter titles from markdown
2. Build TOC generator with configurable title and auto-linking to chapters
3. Implement CSS styles for table of contents with WeasyPrint features (leader dots, target-counter)
4. Ensure responsive and professional TOC styling

### Phase 3

> Add chapter separation and numbering features

1. Implement automatic page breaks between chapters using CSS
2. Create optional chapter numbering system with configurable styles
3. Add chapter template with conditional title rendering
4. Integrate customization options (toc_title, chapter_numbering, chapter_numbering_style)

### Phase 4

> Integrate PDF generation into existing workflow

1. Replace text generation with PDF generation in OpenAIEbookProcessor
2. Update Google Drive upload to handle PDF files instead of text
3. Add configuration interface for new PDF options
4. Remove old markdown-only workflow

## Reviewed implementation

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4

## Validation flow

1. Create new ebook with sommaire and chapter separation options enabled
2. Verify automatic table of contents generation with proper links
3. Confirm each chapter starts on a new page
4. Test PDF generation quality and performance
5. Validate customization options (custom TOC title, chapter numbering)
6. Check PDF upload to Google Drive and preview functionality

## Estimations

- Confidence: 10/10
- Time to implement: 3-4 hours

**Perfect fit for use case:**

- Small documents (coloring books, short stories) = no performance concerns
- WeasyPrint excellent for creative/visual content
- PDF format ideal for print-ready coloring books
- Simple, focused implementation without complex edge cases