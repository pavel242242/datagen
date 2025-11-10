---
description: Format, test, and commit feature changes with proper commit message
---

Automate the commit workflow: format code, run tests, and create a well-structured commit.

**Your task:**

1. **Format code:**
   - Run `black src/ tests/`
   - Run `ruff check --fix src/ tests/`

2. **Run tests:**
   - Run `pytest tests/ -v`
   - If tests fail, STOP and report failures

3. **Check git status:**
   - Run `git status`
   - Show what files changed

4. **Create commit:**
   - Ask user for commit message components:
     - Type: feat/fix/docs/test/refactor/chore
     - Scope: what feature/module changed
     - Summary: one-line description
   - Format as conventional commit:
     ```
     <type>(<scope>): <summary>

     <detailed description if needed>

     - Key changes
     - Test coverage
     - Validation results
     ```

5. **Stage and commit:**
   - `git add <files>`
   - `git commit -m "<message>"`

**Example commit messages:**

```
feat(vintage-effects): Implement entity vintage effects feature

Add age-based activity decay and value growth multipliers for entities.
Enables cohort retention analysis and LTV calculations.

- Added VintageBehavior to schema.py (Pydantic model)
- Implemented age calculation in executor.py
- Added array-based and parametric curves
- Test coverage: 15 tests in test_vintage_effects.py
- Validation: Blind analysis confirms cohort retention visible

Closes #1 (Entity Vintage Effects)
```

```
fix(modifiers): Fix trend modifier time reference bug

Trend modifier was not correctly handling datetime columns as time reference.

- Fixed datetime parsing in modifiers.py:234
- Added regression test
- All 69 tests passing
```

**Safety checks:**
- ❌ Don't commit if tests fail
- ❌ Don't commit if linting has errors
- ✅ Always show git diff before committing
- ✅ Confirm commit message with user
