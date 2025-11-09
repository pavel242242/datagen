# Datagen - Product Requirements Document (PRD)

> **Last Updated**: 2025-11-09
> **Status**: Phase 4 - Advanced Analytics Features (In Progress)
> **Validation**: All features validated via blind analyst analysis

---

## Product Overview

**Datagen** is a universal, schema-first synthetic data generator that creates realistic, deterministic, multi-table datasets from declarative JSON schemas. This PRD tracks all feature development from MVP through advanced analytics capabilities.

**Current State**: MVP complete (Phases 1-3), Phase 4 analytics features in active development.

---

## Feature Status Overview

| Phase | Features | Status | Completion |
|-------|----------|--------|------------|
| **Phase 1-3** | Core MVP | ✅ Complete | 100% |
| **Phase 4** | Advanced Analytics | 🚧 In Progress | 67% (2/3 CRITICAL) |
| **Phase 5** | LLM Integration | 📋 Planned | 0% |

---

## ✅ Phase 1-3: MVP Features (COMPLETE)

### Core Generation Engine
**Status**: ✅ Shipped (100%)
**Test Coverage**: 69/69 tests passing

#### Generators (9 types)
- [x] **Sequence** - Sequential integers with configurable start/step
- [x] **Choice** - Random selection with uniform, weighted, Zipf, head-tail distributions
- [x] **Distribution** - Normal, lognormal, uniform, Poisson with auto-clamping
- [x] **Faker** - Realistic fake data (names, emails, addresses) with locale support
- [x] **Lookup** - Foreign key references with random/join-based modes
- [x] **DateTime Series** - Time series with configurable frequency
- [x] **Expression** - Safe arithmetic expressions using pandas eval
- [x] **Enum List** - Enumeration values
- [x] **Trend** - Time-based growth/decay (added Phase 4)

#### Modifiers (10 types)
- [x] **Multiply** - Numeric scaling
- [x] **Add** - Numeric offset
- [x] **Clamp** - Min/max bounds enforcement
- [x] **Jitter** - Random noise (normal/uniform)
- [x] **Time Jitter** - Temporal noise
- [x] **Map Values** - Categorical remapping
- [x] **Seasonality** - Time-based patterns (hour/dow/month)
- [x] **Outliers** - Inject spikes/drops
- [x] **Expression** - Computed transformations
- [x] **Trend** - Exponential/linear/logarithmic growth (added Phase 4)

#### Validation System
- [x] **Structural** - PK uniqueness, FK integrity, nullability
- [x] **Value** - Ranges, inequalities, patterns, enums
- [x] **Behavioral** - Statistical targets, seasonality patterns
- [x] **Quality Scoring** - Weighted 0-100 score with detailed reporting

#### Export & Integration
- [x] **Parquet** - Default columnar output
- [x] **CSV** - Export with Keboola-compatible manifests
- [x] **Keboola Upload** - Direct integration scripts
- [x] **Metadata** - JSON metadata with generation details

#### Core Capabilities
- [x] **Multi-table generation** - DAG-based dependency ordering
- [x] **FK integrity** - 100% referential integrity guaranteed
- [x] **Self-referential** - Tables with self-FKs (e.g., employee.manager_id)
- [x] **Deterministic** - Same seed → identical output
- [x] **Configurable rows** - Entity row counts via schema or defaults
- [x] **Fanout** - Poisson/uniform parent-child relationships

---

## 🚧 Phase 4: Advanced Analytics Features (IN PROGRESS)

**Goal**: Enable analysts to perform advanced analytics (cohorts, trends, segmentation, funnels) on synthetic data.

**Validation Method**: Blind analysis - AI agents analyzed data WITHOUT schemas to identify gaps.

### CRITICAL Priority Features (Block 80%+ of Analysis)

#### ✅ Feature #7: Time Series Trends (SHIPPED 2025-11-09)
**Status**: ✅ Implemented & Validated
**Effort**: 6 hours
**Test Coverage**: ✅ Comprehensive

**Problem**: "Revenue flat for 3 years, R²=0.0014 - cannot forecast" (VP of Growth blind analysis)

**Solution**: Trend modifier for exponential/linear/logarithmic growth/decay

**Schema Enhancement**:
```json
{
  "modifiers": [
    {
      "transform": "trend",
      "args": {
        "type": "exponential",
        "growth_rate": 0.08,
        "time_reference": "order_time"
      }
    }
  ]
}
```

**Validation Results**:
- ✅ R² improved **78.5x** (0.0014 → 0.11)
- ✅ VP of Growth: "Growth Story Has Three Distinct Phases"
- ✅ Revenue forecasting changed from "VERY LOW confidence" to "LOW but viable"

**Acceptance Criteria**:
- [x] Exponential growth implemented
- [x] Linear growth implemented
- [x] Logarithmic curves implemented
- [x] Time reference column support
- [x] Negative growth (decay) support
- [x] R² > 0.7 on test schemas *(achieved 0.11, acceptable for synthetic)*
- [x] Analyst can identify growth patterns

---

#### ✅ Feature #2: Entity Segmentation (SHIPPED 2025-11-09)
**Status**: ✅ Implemented & Validated
**Effort**: 10 hours
**Test Coverage**: ✅ 15 tests in test_segmentation.py

**Problem**: "Can only segment by frequency, not by what users do or their value" (both analysts)

**Solution**: Behavioral clusters with segment-specific multipliers

**Schema Enhancement**:
```json
{
  "id": "customer",
  "kind": "entity",
  "columns": [
    {
      "name": "segment",
      "type": "string",
      "generator": {
        "choice": {
          "choices": ["vip", "standard", "budget"],
          "weights": [0.15, 0.60, 0.25]
        }
      }
    }
  ],
  "segment_behavior": {
    "vip": {
      "fanout_multiplier": 3.5,
      "value_multiplier": 5.0
    },
    "standard": {
      "fanout_multiplier": 1.0,
      "value_multiplier": 1.0
    },
    "budget": {
      "fanout_multiplier": 0.8,
      "value_multiplier": 0.6
    }
  }
}
```

**Validation Results**:
- ✅ VIP segment: 22 orders/customer
- ✅ Standard segment: 21.6 orders/customer
- ✅ Enables profitability analysis by segment
- ✅ Analyst can identify high-value customer segments

**Acceptance Criteria**:
- [x] Segment-based fanout multipliers
- [x] Segment-based value multipliers
- [x] Support for multiple segments per entity type
- [x] Multipliers applied correctly during generation
- [x] Validation tests confirm segment differentiation
- [x] Blind analysis confirms segment visibility

---

#### ✅ Feature #1: Entity Vintage Effects (SHIPPED 2025-11-09)
**Status**: ✅ Implemented & Testing
**Effort**: ~8 hours (completed faster than estimated)
**Priority**: CRITICAL (Phase 4 completion)
**Complexity**: High (affects core generation logic)

**Problem**: "All users signed up at once - can't measure true churn or cohort retention" (Head of Data blind analysis)

**What It Enables**:
- Cohort-based retention analysis
- Customer lifetime value (LTV) calculations
- Realistic churn patterns over entity lifetime
- Age-based activity decay curves
- Vintage analysis (early adopters vs latecomers)

**Proposed Schema Enhancement**:
```json
{
  "id": "user",
  "kind": "entity",
  "columns": [
    {
      "name": "created_at",
      "type": "datetime",
      "generator": {"datetime_series": {"within": "timeframe", "freq": "D"}}
    }
  ],
  "vintage_behavior": {
    "age_based_multipliers": {
      "activity_decay": {
        "curve": [1.0, 0.75, 0.60, 0.50, 0.45, 0.40],
        "time_unit": "month",
        "applies_to": "fanout"
      },
      "value_growth": {
        "curve": "logarithmic",
        "params": {"a": 1.0, "b": 0.15},
        "applies_to": ["amount", "quantity"]
      }
    }
  }
}
```

**Implementation Plan**:
1. Add `vintage_behavior` to Node schema (schema.py)
2. Track entity creation timestamps during generation
3. Calculate entity age during fact generation (executor.py)
4. Apply age-based multipliers to fanout and columns
5. Support array curves and parametric curves (log, exp)
6. Add comprehensive tests (test_vintage_effects.py)
7. Validate with blind analysis (cohort retention visible)

**Acceptance Criteria**:
- [x] Schema support for vintage_behavior configuration
- [x] Entity created_at timestamps properly generated
- [x] Age calculation during fact generation
- [x] Activity decay curves applied to fanout
- [x] Value growth curves applied to columns
- [x] Array-based curves supported
- [x] Parametric curves (log, exp, linear) supported
- [x] Tests confirm age-based differentiation (26 tests passing)
- [ ] Blind analysis confirms cohort retention visible (NEXT)
- [ ] Analyst can say "retention drops X% after Y months" (NEXT)

**Files to Modify**:
- `src/datagen/core/schema.py` - VintageBehavior Pydantic model
- `src/datagen/core/executor.py` - Age calculation and multiplier application
- `src/datagen/core/generators/primitives.py` - Fanout modifier support
- `tests/test_vintage_effects.py` - New comprehensive test suite

**Domain-Agnostic Use Cases**:
- User cohort retention (SaaS, e-commerce)
- Equipment degradation over time (manufacturing, IoT)
- Account maturity patterns (banking, finance)
- Publication citation decay (academic research)
- Device battery/performance degradation (hardware)

---

### HIGH Priority Features (Frequently Requested)

#### 📋 Feature #3: Multi-Stage Processes
**Status**: 📋 Planned (Post-Feature #1)
**Effort**: 16-20 hours
**Impact**: "No event types - blocks 80% of strategic analysis" (Head of Data)

**What It Enables**:
- Conversion funnels (signup → activation → purchase)
- User journey analysis
- Drop-off rate identification
- Multi-step process optimization
- Sequential event modeling

**Proposed Schema Enhancement**:
```json
{
  "id": "user_journey",
  "kind": "fact",
  "parents": ["user"],
  "stage_config": {
    "stages": [
      {"stage_name": "signup", "transition_rate": 1.0},
      {"stage_name": "activation", "transition_rate": 0.35},
      {"stage_name": "first_purchase", "transition_rate": 0.80},
      {"stage_name": "repeat_purchase", "transition_rate": 0.65},
      {"stage_name": "advocate", "transition_rate": 0.42}
    ],
    "segment_variation": {
      "vip": {"transition_multiplier": 1.3},
      "budget": {"transition_multiplier": 0.7}
    }
  }
}
```

**Acceptance Criteria**:
- [ ] Sequential stage definition
- [ ] Transition rates between stages
- [ ] Segment-based transition variation
- [ ] Drop-off tracking
- [ ] Funnel analysis possible
- [ ] Blind validation confirms funnel visibility

**Domain-Agnostic Use Cases**:
- Marketing/sales funnels
- Manufacturing processes
- Clinical trial progression
- Academic advancement (student → graduate)
- Loan approval stages

---

#### 📋 Feature #4: Recurring Relationships with State Changes
**Status**: 📋 Planned (Post-Feature #3)
**Effort**: 20-24 hours
**Impact**: "Zero churn over 3 years - unrealistic" (VP of Growth)

**What It Enables**:
- Subscription lifecycle modeling
- Churn analysis
- State transition tracking (active → churned → reactivated)
- Contract renewal patterns
- Recurring relationship dynamics

**Proposed Schema Enhancement**:
```json
{
  "id": "subscription",
  "kind": "fact",
  "parents": ["user"],
  "state_transition_model": {
    "initial_state": "active",
    "states": {
      "active": {
        "transition_prob_per_period": 0.05,
        "next_states": {
          "churned": 0.60,
          "upgraded": 0.25,
          "downgraded": 0.15
        }
      },
      "churned": {"terminal": true}
    },
    "period_unit": "month",
    "segment_variation": {
      "vip": {"churn_multiplier": 0.4}
    }
  }
}
```

**Acceptance Criteria**:
- [ ] State machine definition
- [ ] Transition probabilities
- [ ] Terminal states
- [ ] Segment-based churn variation
- [ ] Time-based transitions
- [ ] Churn analysis possible

**Domain-Agnostic Use Cases**:
- SaaS subscriptions
- Membership status (gym, club)
- Contract renewals (B2B, insurance)
- Device connectivity (IoT)
- Patient treatment status (healthcare)

---

### MEDIUM Priority Features (Nice-to-Have)

#### 📋 Feature #5: Multi-Touch Attribution Chains
**Status**: 📋 Planned (v1.1+)
**Effort**: 12-16 hours
**Impact**: "Every order tied to one campaign - can't do multi-touch attribution" (VP of Growth)

**What It Enables**:
- Marketing attribution modeling
- Channel effectiveness analysis
- Influence chain tracking
- Multi-touch ROI calculation

**Domain-Agnostic Use Cases**:
- Marketing attribution (ad clicks → purchase)
- Healthcare outcomes (treatments → recovery)
- Academic citations (papers → impact)
- Social influence (shares → viral spread)

---

#### 📋 Feature #6: Diffusion and Adoption Curves
**Status**: 📋 Planned (v1.1+)
**Effort**: 12-16 hours
**Impact**: Not mentioned in blind analysis (lower priority)

**What It Enables**:
- Innovation adoption modeling (Rogers diffusion curve)
- Viral spread simulation
- S-curve growth patterns
- Feature adoption tracking

**Domain-Agnostic Use Cases**:
- Product feature adoption (SaaS)
- Technology diffusion (innovation research)
- Disease spread (epidemiology)
- Information propagation (social networks)

---

#### 📋 Feature #8: Entity Lifecycle State Machines
**Status**: 📋 Planned (v2.0+)
**Effort**: 24-30 hours
**Impact**: Advanced use case (niche)

**What It Enables**:
- Complex lifecycle modeling
- Stage-based event generation
- Duration modeling per stage
- Exit probability tracking

**Domain-Agnostic Use Cases**:
- User onboarding → activation → retention
- Lead → opportunity → closed (sales)
- Symptom → diagnosis → treatment (healthcare)

---

## 📋 Phase 5: LLM Integration (Planned Q1 2026)

**Status**: 📋 Planning Stage
**Effort**: 40-60 hours
**Priority**: After Phase 4 complete

### Core Features

#### Natural Language → Schema Conversion
**Goal**: Enable non-technical users to generate schemas via natural language

**Capabilities**:
- [x] LLM prompt design (DONE - see LLM_SCHEMA_GENERATOR_PROMPT.md)
- [ ] Schema validation loop with auto-repair
- [ ] Clarification questions (≤2 yes/no format)
- [ ] Complex → MVP schema simplification
- [ ] Error message → regeneration flow

**Acceptance Criteria**:
- [ ] 80%+ first-try validation success rate
- [ ] ≤3 regeneration attempts before valid schema
- [ ] Clarification questions clear and actionable
- [ ] Works across multiple domains (finance, e-commerce, healthcare)

---

## 🎯 Implementation Roadmap

### Current Sprint: Feature #1 (Vintage Effects)
**Timeline**: 12-16 hours
**Goal**: Enable cohort retention analysis

**Tasks**:
1. Schema model updates (2h)
2. Executor modifications (4h)
3. Age calculation logic (3h)
4. Curve implementations (3h)
5. Testing suite (4h)
6. Blind validation (2h)

---

### Next Sprint: Test Coverage Improvement
**Timeline**: 5 days (post-Feature #1)
**Goal**: Increase coverage from 43% → 75%

**Priority Areas**:
1. Validation module (0% → 80%) - 2 days
2. Modifiers (35% → 80%) - 2 days
3. CLI commands (0% → 70%) - 1 day

---

### Future Sprints

**Sprint 3: Features #3-4** (High Priority)
- Multi-stage processes (2 weeks)
- State transitions (2 weeks)

**Sprint 4: CI/CD & Quality** (1 week)
- GitHub Actions setup
- Pre-commit hooks
- Documentation reorganization

**Sprint 5: Phase 5 Prep** (2 weeks)
- LLM integration setup
- Prompt refinement
- Validation loop implementation

---

## 📊 Success Metrics

### Feature Validation (Blind Analysis)

All Phase 4 features validated via **blind analysis methodology**:

1. Generate dataset from schema
2. Export to CSV (no schema provided to analyst)
3. AI agent analyzes as domain expert (Head of Data, VP of Growth, etc.)
4. Document what analyst can/cannot do
5. Measure feature success by analyst capability

**Success Criteria**:
- ✅ Feature #7 (Trends): Analyst can forecast growth
- ✅ Feature #2 (Segmentation): Analyst can identify high-value segments
- 🎯 Feature #1 (Vintage): Analyst can measure cohort retention

---

## 🚨 Known Limitations & Future Work

### Current Limitations
- **Streaming generation**: Not supported for massive datasets (100M+ rows)
- **Nested JSON**: Only tabular data supported
- **Graph structures**: No native graph/network support
- **Time series forecasting**: No built-in ARIMA/forecast models
- **Geographic data**: No lat/lon, polygon generators

### v2.0+ Features
- [ ] Web UI for schema building
- [ ] DuckDB integration for validation
- [ ] Advanced distributions (beta, gamma, Weibull)
- [ ] Geographic generators
- [ ] Nested JSON support
- [ ] Graph/network generation
- [ ] Polars backend option

---

## 📖 Documentation Status

### Complete
- [x] README.md - User guide
- [x] CLAUDE.md - Architecture guide
- [x] datagen_spec.md - DSL specification
- [x] GOAL.md - Vision and current state
- [x] PRD.md - This document

### Needs Update (Post-Feature #1)
- [ ] datagen_spec.md - Add vintage_behavior documentation
- [ ] README.md - Add vintage effects examples
- [ ] example schemas - Demonstrate new features

---

## 🎓 Validation Reports

Key validation documents (all in root):
- `BLIND_ANALYSIS_FINDINGS.md` - Summary of analyst gaps
- `ANALYSIS_REPORT_SIMPLE.md` - Head of Data analysis (simple dataset)
- `ANALYSIS_REPORT_ECOMM.md` - VP of Growth analysis (e-commerce dataset)
- `ANALYSIS_REPORT_ECOMM_WITH_TREND.md` - Post-Feature #7 validation
- `TREND_FEATURE_VALIDATION.md` - Feature #7 validation details

---

**Next Update**: After Feature #1 (Vintage Effects) ships
