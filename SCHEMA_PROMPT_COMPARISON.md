# Schema Generator Prompt Comparison

## Overview

Created two versions of the LLM schema generator prompt:

| Version | File | Lines | Size | Use Case |
|---------|------|-------|------|----------|
| **Compact** | `LLM_SCHEMA_GENERATOR_PROMPT_COMPACT.md` | 212 | 38% | Quick reference, experienced users, token-constrained |
| **Detailed** | `LLM_SCHEMA_GENERATOR_PROMPT.md` | 560 | 100% | Full documentation, learning, complex scenarios |

**Reduction**: 62% fewer lines while keeping all requirements

---

## What's Different

### Compact Version Keeps ✅
- All 10 core rules
- Complete schema structure reference
- All generator types with syntax
- All modifier types with args
- All constraint types
- Validation checklist
- Critical validations (fixes for common errors)
- Minimal working example

### Compact Version Removes ❌
- Verbose explanations and prose
- Multiple examples (keeps 1 minimal example vs 3+ detailed)
- Step-by-step interaction flow
- Best practices prose (converted to checklist)
- Detailed error handling scenarios
- Integration code examples
- Testing scenarios
- User prompt templates

### Compact Version Adds ✅
- **Critical Validations** section with common errors
- **Quick Checklist** for pre-submission
- Inline annotations (e.g., `"code" not "expr"`)
- Condensed syntax examples (all on one line where appropriate)

---

## Use Cases

### Use Compact Version When:
- ✅ Working with token-limited contexts
- ✅ User is experienced with the DSL
- ✅ Need quick syntax reference
- ✅ Generating simple to medium schemas
- ✅ Want faster LLM processing

### Use Detailed Version When:
- ✅ Learning the DSL for first time
- ✅ Complex schema with multiple edge cases
- ✅ Need examples for each feature
- ✅ Troubleshooting validation errors
- ✅ Understanding interaction patterns
- ✅ Implementing LLM integration

---

## Key Improvements in Compact

### 1. Reference-Style Format
**Before** (Detailed):
```markdown
### choice

The choice generator selects values from a list. It supports both inline
choices and references to other tables. You can specify weights to control
the probability distribution.

Example:
```json
{
  "choice": {
    "choices": ["A", "B", "C"],
    "weights": [0.5, 0.3, 0.2]
  }
}
```
```

**After** (Compact):
```markdown
### choice
```json
{"choice": {
  "choices": [val, ...],              // inline OR
  "choices_ref": "table.column",      // reference
  "weights": [num, ...],              // optional
  "weights_kind": "uniform|zipf@1.5|head_tail@{0.6,1.5}"  // NUMERIC only
}}
```
```

### 2. Critical Validations Section
New section highlighting common errors with exact fixes:
```markdown
✅ Always valid:
- weights_kind: NUMERIC values: "zipf@1.5" NOT "zipf@alpha"
- expression: use "code" NOT "expr"
- distribution: always include "clamp": [min, max]
```

### 3. Quick Checklist
Pre-submission checklist for validation:
```markdown
- [ ] All distributions have clamps
- [ ] All weights_kind use numeric values
- [ ] Expression uses "code" field
- [ ] All lookups reference existing table.column
```

---

## Token Count Comparison

Approximate token counts (using ~4 chars/token):

| Version | Characters | Est. Tokens | Reduction |
|---------|------------|-------------|-----------|
| Detailed | ~35,000 | ~8,750 | - |
| Compact | ~11,000 | ~2,750 | 69% |

**Savings**: ~6,000 tokens per prompt

---

## Recommendation

**For production LLM integration**:
- Start with **Compact** for most use cases (faster, cheaper)
- Fall back to **Detailed** if LLM struggles with complex schemas
- Use **Compact** for Claude/GPT-4 (strong instruction following)
- Use **Detailed** for weaker models that need more guidance

**For documentation**:
- Keep **Detailed** as primary documentation
- Link to **Compact** as "Quick Reference"

---

## Testing Both Versions

Test with same inputs to verify equivalence:

```bash
# Test 1: Simple NL description
echo "Generate a customer-order schema" | llm_with_compact_prompt
echo "Generate a customer-order schema" | llm_with_detailed_prompt

# Test 2: Complex schema simplification
cat complex_schema.json | llm_with_compact_prompt
cat complex_schema.json | llm_with_detailed_prompt

# Expected: Both produce valid, equivalent Datagen DSL
```

---

## Files

- **Compact**: `/Users/chocho/projects/datagen/LLM_SCHEMA_GENERATOR_PROMPT_COMPACT.md` (212 lines)
- **Detailed**: `/Users/chocho/projects/datagen/LLM_SCHEMA_GENERATOR_PROMPT.md` (560 lines)
- **Comparison**: `/Users/chocho/projects/datagen/SCHEMA_PROMPT_COMPARISON.md` (this file)
