---
description: Format all code with black and fix linting issues with ruff
---

Run code formatting and linting tools across the entire codebase.

**Your task:**
1. Run `black src/ tests/` to format all Python files
2. Run `ruff check --fix src/ tests/` to auto-fix linting issues
3. Report what was changed:
   - Number of files reformatted
   - Number of linting issues fixed
   - Remaining issues that need manual attention

**Output format:**
```
🔧 Code Formatting & Linting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Black Formatting:
✅ 14 files reformatted
✅ 58 files left unchanged

Ruff Linting:
✅ 23 issues auto-fixed
⚠️  3 issues need manual attention:
   - src/datagen/core/executor.py:125 - unused import
   - tests/test_generators.py:45 - line too long

Next Steps:
- Review changes with git diff
- Fix remaining manual issues
- Run tests to ensure nothing broke
```

**When to use:**
- Before committing code
- After implementing a feature
- When preparing for PR
- As part of cleanup workflow

**Note:** Always run tests after formatting to ensure nothing broke:
`pytest tests/ -v`
