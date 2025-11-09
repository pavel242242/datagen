# Feature Implementation Roadmap

> **Goal**: Implement validated features from blind analysis, starting with CRITICAL priority items.

---

## Phase 1: CRITICAL Features (Unblocks 80%+ of Analysis)

### Feature #7: Time Series Trends (EASIEST - Start Here)
**Status**: 🔄 Next
**Complexity**: Low (extends existing modifier system)
**Impact**: CRITICAL - "Revenue flat for 3 years, R²=0.0014 - cannot forecast"

**Implementation:**
1. Add `trend` modifier to modifier registry
2. Support exponential, linear, logarithmic growth/decay
3. Reference a time column for trend calculation
4. Apply trend multiplier based on time distance from start

**Files to modify:**
- `src/datagen/core/schema.py` - Add TrendModifier Pydantic model
- `src/datagen/core/modifiers.py` - Implement trend modifier
- Add tests in `tests/test_modifiers.py`

**Example usage:**
```json
{
  "transform": "trend",
  "args": {
    "type": "exponential",
    "growth_rate": 0.08,
    "time_reference": "order_time"
  }
}
```

**Estimated effort**: 4-6 hours

---

### Feature #2: Entity Segmentation (MEDIUM)
**Status**: ⏳ Pending
**Complexity**: Medium (extends entity generation)
**Impact**: CRITICAL - "Can only segment by frequency, not by what users do or value"

**Implementation:**
1. Add `segment_behavior` to entity node schema
2. During fact generation, look up parent segment value
3. Apply segment multipliers to fanout, value columns
4. Support segment-specific decay rates

**Files to modify:**
- `src/datagen/core/schema.py` - Add segment_behavior to Node model
- `src/datagen/core/executor.py` - Apply segment multipliers during generation
- Add tests in `tests/test_executor.py`

**Example usage:**
```json
{
  "id": "customer",
  "kind": "entity",
  "segment_behavior": {
    "enterprise": {"fanout_multiplier": 3.5, "value_multiplier": 5.0},
    "smb": {"fanout_multiplier": 1.0, "value_multiplier": 1.0}
  }
}
```

**Estimated effort**: 8-12 hours

---

### Feature #1: Entity Vintage Effects (HARDEST)
**Status**: ⏳ Pending
**Complexity**: High (affects core generation logic)
**Impact**: CRITICAL - "All users signed up at once - can't measure true churn or cohort retention"

**Implementation:**
1. Add `vintage_behavior` to entity node schema
2. Track entity age during fact generation
3. Apply age-based multipliers to fanout and value columns
4. Support array curves and parametric curves (logarithmic, exponential)

**Files to modify:**
- `src/datagen/core/schema.py` - Add vintage_behavior to Node model
- `src/datagen/core/executor.py` - Calculate entity age, apply multipliers
- `src/datagen/core/generators/primitives.py` - Fanout modifier support
- Add tests in `tests/test_vintage_effects.py`

**Example usage:**
```json
{
  "vintage_behavior": {
    "age_based_multipliers": {
      "activity_decay": {
        "curve": [1.0, 0.75, 0.60, 0.50, 0.45, 0.40],
        "time_unit": "month",
        "applies_to": "fanout"
      }
    }
  }
}
```

**Estimated effort**: 12-16 hours

---

## Phase 2: HIGH Priority Features

### Feature #3: Multi-Stage Processes
**Impact**: "No event types - blocks 80% of strategic analysis"
**Estimated effort**: 16-20 hours

### Feature #4: Recurring Relationships with State Changes
**Impact**: "Zero churn over 3 years - unrealistic"
**Estimated effort**: 20-24 hours

---

## Phase 3: MEDIUM/LOW Priority Features

### Feature #5: Multi-Touch Attribution
### Feature #6: Diffusion/Adoption Curves
### Feature #8: Entity Lifecycle State Machines

---

## Implementation Strategy

### Order of Implementation:
1. **Feature #7 (Trend)** - Quick win, immediate value
2. **Feature #2 (Segmentation)** - Moderate complexity, high value
3. **Feature #1 (Vintage)** - Complex but critical for cohort analysis
4. **Feature #3 (Multi-Stage)** - After Phase 1 complete
5. **Feature #4 (State Transitions)** - After Feature #3

### Testing Strategy:
- Unit tests for each new modifier/generator
- Integration test updating existing schemas (ecomm.json, simple_users_events.json)
- **Re-run blind analysis** after Phase 1 to validate improvements
- Generate same datasets with new features, compare analyst reports

### Documentation:
- Update `datagen_spec.md` with new modifier/config options
- Update `CLAUDE.md` with implementation details
- Create example schemas demonstrating each feature
- Update README.md with new capabilities

---

## Current Focus: Feature #7 - Time Series Trends

**Next Actions:**
1. Define Pydantic schema for TrendModifier
2. Implement trend calculation logic
3. Add unit tests
4. Update ecomm.json to use trend modifier
5. Regenerate dataset and verify trend is visible

**Success Criteria:**
- Linear regression on revenue shows R² > 0.7 (vs current 0.0014)
- Analyst can forecast future revenue with confidence
- Growth rate parameter matches observed trend

---

**Last Updated**: 2025-11-09
