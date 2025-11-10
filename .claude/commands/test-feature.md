---
description: Run tests for a specific feature or module
---

Run pytest tests for the specified feature or module.

**Usage Examples:**
- `/test-feature generators` - Test all generators
- `/test-feature segmentation` - Test segmentation feature
- `/test-feature modifiers` - Test all modifiers
- `/test-feature vintage` - Test vintage effects (when implemented)
- `/test-feature all` - Run all tests

**Your task:** Run the appropriate pytest command based on the feature name provided by the user.

**Common test files:**
- `tests/test_generators.py` - Generator tests
- `tests/test_modifiers.py` - Modifier tests
- `tests/test_segmentation.py` - Segmentation feature tests
- `tests/test_dag.py` - DAG building tests
- `tests/test_seed.py` - Seed derivation tests
- `tests/test_schema.py` - Schema validation tests

If the user provides a specific feature name:
1. Map it to the appropriate test file(s)
2. Run `pytest <test_file> -v`
3. Show the results
4. If failures, show the relevant error messages

If the user says "all":
1. Run `pytest tests/ -v`
2. Show pass/fail summary

Always provide context about what was tested and what the results mean.
