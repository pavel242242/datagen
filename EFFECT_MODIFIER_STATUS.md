# Effect Modifier Implementation Status

Date: 2025-10-10

## Summary

Effect modifiers are **partially implemented**:
- ✅ **Column-level effects**: IMPLEMENTED
- ⚠️ **Table-level effects**: NOT YET IMPLEMENTED

## What Are Effect Modifiers?

Effect modifiers apply time-windowed multipliers from external event tables (promotions, campaigns, holidays, etc.) to make data more realistic.

### Column-Level Effects
Apply multipliers to **column values** based on matching events.

**Example**: Apply promotion discount to transaction amounts
```json
{
  "name": "amount",
  "type": "float",
  "modifiers": [{
    "transform": "effect",
    "args": {
      "effect_table": "promotion",
      "on": {"promotion_id": "promotion_id"},
      "window": {"start_col": "start_at", "end_col": "end_at"},
      "map": {"field": "discount_multiplier", "op": "mul", "default": 1.0}
    }
  }]
}
```

**Status**: ✅ Fully implemented in `src/datagen/core/modifiers.py:247-345`

**How it works**:
1. For each row, finds matching effects by join keys and time window
2. Applies effect multiplier/delta to column value
3. Uses default if no effect matches

### Table-Level Effects
Scale the **number of rows generated** (fanout) based on matching events.

**Example**: Generate 2x more communications during promotions
```json
{
  "id": "communication",
  "kind": "fact",
  "parents": ["customer"],
  "fanout": {"distribution": "poisson", "lambda": 20},
  "columns": [...],
  "modifiers": [{
    "transform": "effect",
    "args": {
      "effect_table": "promotion",
      "on": {"promotion_id": "promotion_id"},
      "window": {"start_col": "start_at", "end_col": "end_at"},
      "map": {"field": "occurrence_multiplier", "op": "mul", "default": 1.0}
    }
  }]
}
```

**Status**: ⚠️ NOT YET IMPLEMENTED

**What needs to be done**:
1. In `DatasetExecutor.generate_fact()`, detect table-level effect modifiers
2. For each parent row, find matching effects
3. Multiply sampled fanout by effect multiplier before generating child rows
4. Handle time-based effects (need datetime column in parent or context)

**Impact**: Examples generate successfully but without fanout scaling
- Promotions don't increase communication volume
- Growth effects don't scale order/inventory volumes
- Campaigns don't boost conversions

## Usage in Examples

### Column-Level (Working)
None found in current examples - all use table-level

### Table-Level (Not Working)
- `example/bank.json`:
  - `communication` table uses promotion effects
- `example/ecomm.json`:
  - `order` table uses growth_effect, campaign, shop effects
  - `inventory_movement` table uses growth_effect, shop effects
  - `purchase_order` table uses growth_effect, shop effects
- `example/gov_scaled.json`:
  - `class_meeting` uses calendar_effects (on datetime column - treated as column-level)
  - `attendance` uses calendar_effects (on datetime column - treated as column-level)

## Implementation Priority

**Low-Medium**:
- System still generates realistic data without fanout effects
- Main realism comes from seasonality patterns (working)
- Effect on column values (working) handles many use cases
- Table-level effects add volume realism but not structural realism

**Estimated effort**: 2-3 hours
- Need to refactor fanout sampling to accept multipliers
- Need to resolve effect matching before fanout sampling
- Need to handle per-parent-row effect lookup

## Workarounds

For now, users can:
1. Adjust base fanout λ values to simulate average effect
2. Use seasonality modifiers on datetime columns (working)
3. Use column-level modifiers on numeric fields (working)

## Related Features

- ✅ Seasonality modifiers: Fully working, including composite patterns
- ✅ Outliers modifiers: Working on numeric columns
- ✅ All other modifiers: Working

The effect modifier is the only partially-implemented feature in the entire system.
