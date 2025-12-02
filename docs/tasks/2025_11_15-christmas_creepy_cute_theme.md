<!--  AI INSTRUCTIONS ONLY -- Follow those rules, do not output them.

- ENGLISH ONLY
- Text is straight to the point, no emojis, no style, use bullet points.
- Replace placeholders (`{variables}`) with actual user inputs.
- Define flow of the feature, from start to end.
- Interpret comments on this file to help you fill it.
-->

# Instruction: Add Christmas Creepy But Cute Theme

## Feature

- **Summary**: Add new standalone theme "Christmas Creepy But Cute" combining festive Christmas elements with adorable-yet-spooky aesthetics (Tim Burton style) for niche product testing
- **Stack**: `YAML 6`, `Python 3.11`, `ThemeLoader`, `ThemeRepository`, `PyYAML 6`

## Existing files

- @config/branding/themes/dinosaurs.yml
- @config/branding/themes/unicorns.yml
- @config/branding/themes/neutral-default.yml
- @src/backoffice/features/ebook/shared/domain/theme/theme_loader.py
- @src/backoffice/features/ebook/shared/infrastructure/adapters/theme_repository.py
- @src/backoffice/features/ebook/shared/domain/entities/theme_profile.py

### New file to create

- config/branding/themes/christmas-creepy-cute.yml

## Implementation phases

### Phase 1: Create Theme YAML Configuration

> Create complete theme configuration file following existing structure

1. Create `config/branding/themes/christmas-creepy-cute.yml` file
2. Define metadata: `id: christmas-creepy-cute`, `label: "Christmas Creepy But Cute"`
3. Define color palette:
   - base: dark festive colors (blood red #8b0000, dark pine green #1a4d2e, charcoal black #1c1c1c, snow white #f5f5f5)
   - accents_allowed: pumpkin orange #ff6600, dark purple #6a0dad, bone white #f8f8ff
   - forbidden_keywords: rainbow, pastel, bright neon, vibrant gradient
4. Write cover `prompt_blocks` for colorful cover generation:
   - subject: cute skeleton Santa OR zombie reindeer OR vampire elf OR ghost snowman (centered, friendly face)
   - environment: haunted house with Christmas lights, snowy cemetery with ornaments, dark toy workshop, misty forest with decorations
   - tone: festive yet mysterious, Tim Burton style, kid-friendly dark, whimsical spooky
   - positives: highly detailed, cute but creepy, glossy, professional children's book cover, Amazon bestseller style
   - negatives: no text, no mockup, no borders, no open book, no realistic gore, no truly scary elements
5. Create `coloring_page_templates.base_structure`: "Line art coloring page of a {CHARACTER} {ACTION} in a {ENV}, {SHOT}, {FOCUS}, {COMPOSITION}."
6. Define creative variables for black & white coloring pages:
   - SHOT: close-up, medium, wide, atmospheric scene
   - CHARACTER: skeleton Santa, zombie reindeer, vampire elf, ghost snowman, haunted gingerbread man, gothic Christmas angel, friendly Krampus, skeleton gift wrapper, zombie caroler, vampire toy maker
   - ACTION: delivering cursed gifts, decorating haunted tree, dancing with ghosts, flying with bats, making creepy cookies, singing carols, wrapping presents, riding sleigh through mist, hanging spooky ornaments
   - ENV: haunted house with Christmas lights, snowy cemetery with decorations, dark toy workshop, misty forest with ornaments, gothic fireplace with stockings, cobweb-covered Christmas tree, moonlit snowy rooftop, spooky North Pole
   - FOCUS: head with festive hat, full body, with Christmas props, group scene, holding ornament/cursed gift, skeleton details visible
   - COMPOSITION: left-facing, right-facing, front, 3/4 view, flying/jumping
7. Add `quality_settings` block (copy from existing themes, ensure KDP compliance):
   - Black and white line art coloring page style
   - IMPORTANT: Use ONLY black lines on white background, NO colors, NO gray shading
   - Bold clean outlines, closed shapes, thick black lines
   - NO FRAME, NO BORDER around the illustration
   - Illustration extends naturally to image boundaries
   - Printable 300 DPI, simple to medium detail for kids age 4-8
   - No text, no logo, no watermark

### Phase 2: Technical Validation

> Verify theme loads correctly in existing system

1. Validate YAML syntax (run Python YAML parser check)
2. Verify ThemeLoader automatically discovers new theme (scans `*.yml` files in config/branding/themes/)
3. Check theme appears in ThemeRepository.get_available_themes() output
4. Test fallback mechanism: rename theme file temporarily, verify system uses neutral-default
5. Restore theme file, verify it loads without errors

### Phase 3: Generation Testing

> Validate prompts generate appropriate creepy-cute Christmas content

1. Generate test cover using christmas-creepy-cute theme (verify festive-spooky aesthetic)
2. Generate 2-3 test coloring pages with different CHARACTER/ENV combinations
3. Review outputs:
   - Cover: Check for cute-but-creepy Christmas character, festive dark environment, no text artifacts
   - Coloring pages: Check for clean black lines, no gray shading, printable 300 DPI, kid-friendly creepy aesthetic
4. Adjust prompts if:
   - Too scary (not cute enough) → soften CHARACTER descriptors
   - Not festive enough → enhance Christmas elements in ENV
   - Lines too thin/broken → adjust quality_settings or generation provider

## Reviewed implementation

<!-- That section is filled by a review agent that ensures feature has been properly implemented -->

- [ ] Phase 1: Theme YAML configuration created
- [ ] Phase 2: Technical validation passed
- [ ] Phase 3: Generation testing completed

## Validation flow

<!-- What would a REAL user do to 100% validate the feature? -->

1. Navigate to ebook creation form at http://localhost:8001
2. Select "Christmas Creepy But Cute" theme from dropdown (verify it appears)
3. Fill form: Title "Spooky Christmas", Author "Test", Audience "children", Pages 24
4. Submit and wait for generation (2-5 minutes)
5. Preview generated PDF:
   - Cover shows festive-yet-spooky aesthetic (skeleton Santa, haunted Christmas scene, etc.)
   - All 24 coloring pages show variety of creepy-cute Christmas characters
   - All pages are black & white line art with bold clean outlines
   - No text artifacts on back cover
6. Verify KDP compliance: 8×10", 300 DPI, bleed margins correct
7. Approve book and download PDF
8. Confirm overall aesthetic is Tim Burton-style: creepy but adorable, kid-friendly dark, festive

## Estimations

- **Confidence**: 9/10
  - ✅ Clear YAML structure to follow (dinosaurs.yml, unicorns.yml examples exist)
  - ✅ Auto-loading system already implemented (ThemeLoader scans *.yml, no code changes needed)
  - ✅ Well-defined creative direction (Christmas + creepy-cute + Tim Burton style)
  - ✅ Simple file creation task (no complex logic or new features)
  - ✅ Theme system robust with fallback mechanism
  - ❌ Minor risk: AI prompt tuning may need 1-2 iterations to perfectly balance "creepy" vs "cute"
- **Time to implement**: 20-30 minutes
  - Phase 1: 15-20 min (YAML creation with creative content)
  - Phase 2: 3-5 min (validation checks)
  - Phase 3: 5-10 min (generation testing + potential prompt adjustments)
