# Versioning Control System (VCS) Guidelines

- Main Branch: `main`
- Platform: GitHub
- CLI: `gh`
- Ticketing Tool: GitHub Issues

## Branch Naming Convention

Read:

```markdown
@aidd_docs/templates/vcs/branch.md
```

## Commit Convention

- Format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `ci`, `style`, `docs`, `test`
- Scopes: feature name (`kdp`, `cover`, `auth`, `barcode`, etc.)
- Examples from history:
  - `feat(kdp): add legal/copyright page to KDP interior export`
  - `feat: configurable colors for spine`
  - `fix: back cover overlays`
  - `ci: ruff noqa`

Read:

```markdown
@aidd_docs/templates/vcs/commit.md
```
