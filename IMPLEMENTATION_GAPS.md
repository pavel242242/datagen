# Implementation Gaps Audit

Date: 2025-10-10
After: Composite effect validation implementation

## Critical Gaps

### 1. **Effect Modifier** (HIGH PRIORITY)
**Status**: Not implemented
**Usage**: 14 instances across examples (bank.json, ecomm.json, gov_scaled.json, valid_schema.json)
**Location**: `src/datagen/core/modifiers.py:89` - currently logs warning and skips

**Purpose**: Apply time-windowed multipliers from external event tables
- Examples: promotions, campaigns, calendar events (holidays/snow days)
- Joins fact records with effect table on specified keys
- Applies multiplier/delta if timestamp falls within effect window

**Spec**:
```json
{
  "transform": "effect",
  "args": {
    "effect_table": "calendar_effects",
    "on": {"course_id": "course_id"},  // join keys (or {} for global)
    "window": {"start_col": "start_ts", "end_col": "end_ts"},
    "map": {"field": "multiplier", "op": "mul", "default": 1.0}
  }
}
```

**Impact**:
- Without this, promotional campaigns, calendar effects, and growth shocks are not reflected in data
- Examples generate successfully but ignore these realistic effects
- Composite effect validation includes this in target spec but it's not applied during generation

**Implementation Needed**:
1. In `apply_modifiers()`: Replace warning with actual implementation
2. Access effect table from executor's `generated_data` dict
3. For each value, find matching effect records (join + window check)
4. Apply multiplier/delta operation
5. Use default if no effect matches

---

### 2. **Entity Row Count Configuration**
**Status**: Hardcoded to 1000
**Location**: `src/datagen/core/executor.py:87`
**Comment**: `# TODO: Make this configurable in DSL`

**Current Behavior**: All entity tables get exactly 1000 rows

**Issues**:
- Can't control entity table sizes
- All examples happen to work with 1000 rows
- Not truly general - some domains need 10 entities, others need 100K

**Solution Options**:
1. Add optional `rows: int` field to entity node schema
2. Derive from timeframe + expected fanout (more complex)
3. Keep 1000 as sensible default but allow override

**Impact**: Low - current default works for all examples, but limits generality

---

## Minor Gaps

### 3. **Enum Reference Validation**
**Status**: Skipped in value validation
**Location**: `src/datagen/validation/value.py:324`
**Comment**: `# TODO: resolve enum_ref (for MVP, skip)`
**Usage**: 0 instances in examples

**Impact**: None - feature not used in any examples

---

### 4. **Dry-run Mode**
**Status**: Not implemented
**Location**: `src/datagen/cli/commands.py:66`
**Usage**: CLI flag exists but does nothing

**Impact**: None - convenience feature, not core functionality

---

### 5. **LLM Integration (Phase 5)**
**Status**: Intentionally deferred
**Location**: `src/datagen/cli/commands.py:28`

**Impact**: None - this is future work, not a gap

---

## Universality Check

### ✅ **No Domain-Specific Code**
Searched for domain keywords (bank, ecomm, education, school, student, transaction, order):
- **Result**: Only generic terms like "order" (topological), "byteorder" found
- **No hardcoded domain logic**

### ✅ **All Generators Generic**
- Sequence, choice, distribution, datetime_series, faker, lookup, expression, enum_list
- All domain-agnostic primitives

### ✅ **All Modifiers Generic** (except effect)
- multiply, add, clamp, jitter, map_values, seasonality, time_jitter, outliers
- Effect modifier is generic but not implemented

### ✅ **Schema-Driven**
- Everything configured via JSON DSL
- No business logic in code

---

## Recommendations

### Priority 1: Implement Effect Modifier
**Why**: Used in 14 places across examples, critical for realistic data
**Effort**: Medium (1-2 hours)
**Benefit**: Completes the realism layer, makes composite effect validation meaningful

### Priority 2: Make Entity Rows Configurable
**Why**: Removes hardcoded assumption, increases generality
**Effort**: Low (30 min)
**Benefit**: More flexible for different domains

### Priority 3: Skip enum_ref Validation Implementation
**Why**: Not used anywhere, can defer
**Effort**: N/A
**Benefit**: None

---

## Current State Summary

**Working Features**:
- ✅ Complete DAG-based generation
- ✅ All core generators (8 types)
- ✅ Most modifiers (8/9 types)
- ✅ Composite seasonality patterns
- ✅ Comprehensive validation (structural, value, behavioral)
- ✅ Quality scoring
- ✅ Preflight validation
- ✅ Self-referential tables
- ✅ Fanout distributions
- ✅ Seed management for reproducibility

**Missing**:
- ❌ Effect modifier (critical for realism)
- ⚠️ Hardcoded entity row count

**System is 95% general and universal** - only the effect modifier gap prevents full realism layer from working.
