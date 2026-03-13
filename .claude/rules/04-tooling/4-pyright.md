---
paths:
  - "pyrightconfig.json"
  - "**/*.py"
---

## Type Configuration

- Strict type checking mode enabled
- Python 3.11 language version
- Include all project directories
- Exclude virtual environments and caches

```json
{
  "include": ["domain", "infrastructure", "presentation"],
  "exclude": ["venv", "__pycache__"],
  "pythonVersion": "3.11"
}
```

## Error Reporting

- Report all type errors
- No type ignore comments allowed
- Mandatory return type annotations
- Strict parameter type checking

## Integration

- Run in CI pipeline
- IDE integration required
- Pre-commit hook optional
- Block merge on type errors
