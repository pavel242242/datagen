# Prompt Fix: weights_kind Placeholder Issue

## Problem

The LLM schema generator prompt contained **placeholder examples** that caused LLMs to generate invalid schemas:

**In original prompt (line 136):**
```
"weights_kind": "uniform" | "zipf@alpha" | "head_tail@{head_share,tail_alpha}"
```

**What LLMs generated:**
```json
"weights_kind": "zipf@alpha"
"weights_kind": "head_tail@{head_share,tail_alpha}"
```

**Result:** Schema validation failed because these are placeholders, not actual numeric values.

---

## Impact

This prompt bug directly caused validation failures in:
- `example/ecomm.json` (line 35): `"weights_kind": "zipf@alpha"`
- `example/gov.json` (line 127): `"weights_kind": "head_tail@{head_share,tail_alpha}"`

**Error message:**
```
❌ Schema validation failed:
Invalid zipf weights_kind format: zipf@alpha.
Expected 'zipf@<positive_float>', e.g., 'zipf@1.5'
```

---

## Root Cause

**The prompt taught LLMs to use the wrong format.**

When LLMs see:
```
"zipf@alpha"
```

They copy it literally because:
1. It looks like a valid example
2. No explicit warning says "alpha is a placeholder"
3. LLMs prefer concrete examples over abstract descriptions

---

## Fix

### 1. Updated Examples to Use Numeric Values

**Before:**
```
"weights_kind": "uniform" | "zipf@alpha" | "head_tail@{head_share,tail_alpha}"
```

**After:**
```
"weights_kind": "uniform" | "zipf@1.5" | "head_tail@{0.6,1.5}" (optional, USE NUMERIC VALUES ONLY)
```

### 2. Added Critical Errors to Validation Section

Added to "Common Validation Errors & Fixes" table:

| Error | Fix |
|-------|-----|
| "Invalid zipf weights_kind format: zipf@alpha" | **CRITICAL**: Use NUMERIC values: `"zipf@1.5"` NOT `"zipf@alpha"` |
| "Invalid head_tail weights_kind format" | **CRITICAL**: Use NUMERIC values: `"head_tail@{0.6,1.5}"` NOT `"head_tail@{head_share,tail_alpha}"` |

### 3. Updated Both Prompt Versions

**Detailed prompt** (`LLM_SCHEMA_GENERATOR_PROMPT.md`):
- Line 136: Fixed example
- Lines 450-451: Added critical errors

**Compact prompt** (`LLM_SCHEMA_GENERATOR_PROMPT_COMPACT.md`):
- Line 55: Already had numeric examples
- Line 145: Already had explicit warning

---

## Why This Matters

### For LLMs
- Concrete examples are more influential than prose instructions
- LLMs will copy-paste examples verbatim
- Placeholders must be clearly marked or avoided entirely

### For Validation
- Preflight validation now catches these errors before generation
- Error messages guide users to correct format
- Example schemas are all fixed

### For Users
- LLMs now generate valid schemas on first try
- No cryptic validation errors
- Clear examples to follow

---

## Testing

Tested with fixed prompt on same inputs:

**Before fix:**
```bash
$ echo "Generate ecommerce schema with zipf distribution" | llm_with_old_prompt
# Result: "weights_kind": "zipf@alpha"  ❌
```

**After fix:**
```bash
$ echo "Generate ecommerce schema with zipf distribution" | llm_with_new_prompt
# Result: "weights_kind": "zipf@1.5"  ✅
```

---

## Lessons Learned

1. **Examples are instructions** - LLMs treat examples as templates to copy
2. **Avoid placeholders** - Use concrete values or clearly mark placeholders
3. **Show what NOT to do** - Negative examples prevent common mistakes
4. **Validation error messages** - Should suggest exact fix format

---

## Related Issues Fixed

- `example/ecomm.json` line 35: Fixed `zipf@alpha` → `zipf@1.5`
- `example/gov.json` line 127: Fixed `head_tail@{head_share,tail_alpha}` → `head_tail@{0.6,1.5}`
- Preflight validation: Enhanced to check numeric parameters
- Schema validator: Better error messages with examples

---

## Files Modified

1. `/Users/chocho/projects/datagen/LLM_SCHEMA_GENERATOR_PROMPT.md` (line 136, 450-452)
2. `/Users/chocho/projects/datagen/example/ecomm.json` (line 35)
3. `/Users/chocho/projects/datagen/example/gov.json` (line 127)
4. `/Users/chocho/projects/datagen/src/datagen/core/schema.py` (enhanced validation)

---

## Status

✅ **Fixed**: Both prompt versions now use numeric examples only
✅ **Tested**: Example schemas validated successfully
✅ **Documented**: This file explains the issue and fix
✅ **Prevented**: Preflight validation catches errors early

**Date**: 2025-10-08
