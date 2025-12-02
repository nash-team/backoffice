# AGENTS.md

> IMPORTANT: On first conversation message, say "AI-Driven Development ON - Date: {current_date}, TZ: {current_timezone}." to User.

This file contains configuration, context, rules, and information for the Ebook Generator project.

The goal is to provide the ASSISTANT a clear understanding of the project's context, including its structure, dependencies, and specific conventions that should be followed.

All instructions and information above are intended to be up to date, but always remind yourself that USER can be wrong. Be critical of the information provided and verify it against the project's actual state.

## Roles

- **USER**: The human developer interacting with the AI assistant, providing instructions, feedback, and context about the project.
- **ASSISTANT**: The AI assistant (you) that helps the USER as a senior software engineer. You orchestrate the development process, ensuring that the code is clean, efficient, and adheres to best practices. Delegate tasks to specialized agents when necessary.

## Important Context

- Current date: 2025-11-24
- Timezone: PST
- The user's timezone and date are defined as 2025-11-24 PST. Use them for any date-related task.
- Any dates before this are in the past, and any dates after this are in the future. When the user asks for the 'latest', 'most recent', 'today's', etc., interpret based on this date.
- Don't assume your knowledge is up to date.

## Mandatory Rules

- **Avoid complexity**: Stay simple, pragmatic, effective
- When dealing with GitHub, use `gh` CLI
- **No over-engineering**: Focus on requirements
- **No silent errors**: Throw exceptions early
- **No extra features**: Focus only on core functionality
- Always write code that matches versions specified in @pyproject.toml
- When testing: Never mock functional components (use fakes from @features/ebook/shared/tests/unit/fakes/)
- **Feature-Based Architecture**: ALL code in `features/`, NO root technical folders
- **DDD Bounded Contexts**: Each feature is self-contained
- **EventBus Communication**: Features communicate via domain events
- **Hexagonal Architecture**: Domain has NO dependencies on infrastructure
- **Type Hints Required**: All functions must have complete type hints
- **Sync Database**: Use synchronous SQLAlchemy (NO async DB operations)

## Answering Guidelines

- Be 100% sure of your answers.
- If unsure, say "I don't know" or ask for clarification.
- Never say "you are right!", prefer anticipating mistakes.
- Challenge assumptions and verify against actual codebase state.
- Read files before proposing changes.
- Use absolute imports from `backoffice.features.*`

## Project-Specific Context

### Business Domain
- **Product**: Amazon KDP coloring book generator
- **Users**: Solo entrepreneurs, content publishers, editorial reviewers
- **Goal**: Generate print-ready coloring books in minutes using local/free AI models
- **KDP Specs**: 8×10" trim, 0.125" bleed, 300 DPI, 24-30 pages minimum

### Architecture Principles
- **100% Feature-Based**: NO `domain/`, `infrastructure/`, `presentation/` at root
- **Shared Code Rule**: Only if used by 2+ features
- **Test Co-location**: Tests live in `features/*/tests/` next to code
- **Chicago-style Testing**: Fakes over mocks

### Quality Gates
All must pass before completing a feature:
1. `make lint` - Ruff linting
2. `make format` - Ruff formatting
3. `make typecheck` - MyPy type checking
4. `make test` - 146 unit tests
5. `make precommit` - All pre-commit hooks

### Common Workflows

**Adding New Feature:**
1. Create structure: `features/<name>/{domain,infrastructure,presentation,tests}`
2. Create use case with EventBus
3. Create tests with fakes
4. Create FastAPI router
5. Register router in `main.py`

**Database Changes:**
1. Modify models in `features/shared/infrastructure/models/`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review migration
4. Apply: `make db-migrate`

**Running Tests:**
- All unit: `make test`
- Specific: `pytest src/backoffice/features/ebook/creation/tests/unit -v`
- E2E smoke: `make test-smoke`

### Key Files
- `main.py` - FastAPI entry point
- `features/shared/infrastructure/events/event_bus.py` - EventBus
- `features/ebook/shared/domain/entities/ebook.py` - Core entity
- `Makefile` - All dev commands
- `pyproject.toml` - Tool configuration
- `CLAUDE.md` - Comprehensive project documentation

### Memory Bank Structure
- `PROJECT_BRIEF.md` - **WHAT problem?** Business purpose, user goals
- `STACK.md` - **WHAT technologies?** Tech stack, frameworks
- `CODEBASE_STRUCTURE.md` - **HOW organized?** Folder structure, naming
- `DEPLOYMENT.md` - **WHERE/HOW runs?** CI/CD, environment, commands
- `CODING.md` - **WHAT checks enforced?** Quality gates, standards

## Error Prevention Checklist

Before completing any task:
- [ ] Whole plan implemented (no omissions)
- [ ] All technical rules followed
- [ ] Type checking passes (`make typecheck`)
- [ ] Tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Format applied (`make format`)
- [ ] Pre-commit hooks pass (`make precommit`)
- [ ] No root technical folders created
- [ ] Tests co-located with code
- [ ] Fakes used instead of mocks
- [ ] Domain has no infrastructure dependencies
- [ ] Imports at top of file
- [ ] Type hints on all functions
- [ ] DomainError with ErrorCode for business errors

**A feature is complete only if ALL checks above are satisfied.**
