# Datagen Feature Requests - Domain-Agnostic Analytics Enhancement

> **Goal**: Enhance Datagen's **general-purpose** capabilities to generate datasets that support advanced analytics across ANY domain (business, science, IoT, social networks, etc.) with realistic behavioral patterns, temporal dynamics, and entity interactions.

> **Design Principle**: ALL features must be domain-agnostic. Instead of "MRR" or "cohort retention", we design generic patterns like "time-based entity behavior" and "activity decay curves" that can represent ANY domain.

---

## Context

Datagen currently generates realistic synthetic data with FK integrity, distributions, and seasonality. However, advanced analysis across domains requires:

1. **Time-based entity behavior** - Entities created at different times behave differently (vintage effects)
2. **Temporal dynamics** - Metrics that change over time with growth/decay trends
3. **Entity segmentation** - Subpopulations with distinct behavioral patterns
4. **Multi-stage processes** - Sequential events with conversion/drop-off rates
5. **Multi-entity attribution** - Which combinations of entities drive outcomes
6. **Activity decay patterns** - Realistic engagement/activity curves over entity lifetime
7. **Adoption curves** - S-curves, viral spread, diffusion of innovations

---

## Testing Methodology & Validation Results ✅

### Methodology (Completed)

We validated these feature requests through **blind analysis**:

1. ✅ **Generated datasets** from 2 existing schemas
   - Simple Users & Events (1K users, 8K events, 90 days)
   - E-commerce Multi-Shop (11 tables, 740K+ rows, 3 years)
2. ✅ **Ran parallel blind analysis** - Two haiku agents analyzed data WITHOUT schemas
   - Agent 1: Head of Data (simple dataset)
   - Agent 2: VP of Growth (e-commerce dataset)
3. ✅ **Documented gaps** - What they could/couldn't analyze
4. ✅ **Validated priorities** - Based on analyst pain points

### Key Findings from Blind Analysis

**What Analysts COULD Do:**
- ✅ Basic metrics (counts, sums, averages)
- ✅ Simple rankings (top shops, products, users)
- ✅ Day-of-week patterns
- ✅ Activity-based segmentation (power users vs casual)

**What Analysts COULDN'T Do (Critical Blockers):**
- ❌ **Cohort retention analysis** - "All users signed up at once" (Simple), "All cohorts behave identically" (E-comm)
- ❌ **Growth forecasting** - "Revenue flat for 3 years, R²=0.0014" (E-comm), "No trend, high volatility" (Simple)
- ❌ **Behavioral segmentation** - "Can only segment by frequency, not by what users do or value" (Both)
- ❌ **Funnel analysis** - "No event types, blocks 80% of strategic analysis" (Simple)
- ❌ **True churn measurement** - "Zero churn over 3 years - unrealistic" (E-comm)
- ❌ **Profitability analysis** - "Can see revenue but no COGS/margins" (E-comm)

**See `BLIND_ANALYSIS_FINDINGS.md` and analyst reports for full details.**

---

## Feature Ideas (Domain-Agnostic)

### 1. Entity Vintage Effects

**Problem**: Current entity generation creates all entities with timestamps that don't affect their behavior. In real datasets, entities created at different times exhibit different patterns (e.g., early adopters vs latecomers, old equipment vs new, legacy accounts vs new).

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "entity_name",
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

**Use Cases** (across domains):
- User cohort retention (SaaS, e-commerce)
- Equipment degradation over time (manufacturing, IoT)
- Account maturity patterns (banking)
- Publication citation decay (academic)
- Device battery degradation (hardware)

---

### 2. Entity Segmentation with Behavioral Clusters

**Problem**: All entities of the same type behave identically. Real populations cluster into segments with distinct behavioral patterns.

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "entity_name",
  "kind": "entity",
  "columns": [
    {
      "name": "segment",
      "type": "string",
      "generator": {
        "choice": {
          "choices": ["segment_a", "segment_b", "segment_c"],
          "weights": [0.15, 0.60, 0.25]
        }
      }
    }
  ],
  "segment_behavior": {
    "segment_a": {
      "fanout_multiplier": 3.5,
      "value_multiplier": 5.0,
      "decay_rate": 0.5
    },
    "segment_b": {
      "fanout_multiplier": 1.0,
      "value_multiplier": 1.0,
      "decay_rate": 1.0
    },
    "segment_c": {
      "fanout_multiplier": 0.8,
      "value_multiplier": 0.6,
      "decay_rate": 1.8
    }
  }
}
```

**Use Cases** (across domains):
- Customer segments (enterprise vs SMB)
- Device types (mobile vs desktop vs IoT)
- Sensor clusters (high-precision vs low-cost)
- Participant groups (treatment vs control)
- Geographic regions (urban vs rural)

---

### 3. Multi-Stage Sequential Processes

**Problem**: No built-in support for multi-stage processes with realistic transition/drop-off rates between stages.

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "process_stage",
  "kind": "fact",
  "parents": ["entity"],
  "stage_config": {
    "stages": [
      {"stage_name": "stage_1", "transition_rate": 1.0},
      {"stage_name": "stage_2", "transition_rate": 0.35},
      {"stage_name": "stage_3", "transition_rate": 0.80},
      {"stage_name": "stage_4", "transition_rate": 0.65},
      {"stage_name": "stage_5", "transition_rate": 0.42}
    ],
    "segment_variation": {
      "segment_a": {"transition_multiplier": 1.3},
      "segment_c": {"transition_multiplier": 0.7}
    }
  }
}
```

**Use Cases** (across domains):
- Signup funnels (marketing/SaaS)
- Manufacturing processes (quality control)
- Clinical trials (patient progression)
- Academic progression (student advancement)
- Loan approval stages (banking)

---

### 4. Recurring Relationships with State Changes

**Problem**: No built-in support for recurring relationships that change state over time (subscriptions, memberships, contracts, monitoring).

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "recurring_relationship",
  "kind": "fact",
  "parents": ["entity"],
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
      "upgraded": {
        "transition_prob_per_period": 0.08,
        "next_states": {"active": 0.70, "churned": 0.30}
      },
      "downgraded": {
        "transition_prob_per_period": 0.12,
        "next_states": {"active": 0.50, "churned": 0.50}
      },
      "churned": {"terminal": true}
    },
    "period_unit": "month",
    "segment_variation": {
      "segment_a": {"churn_multiplier": 0.4},
      "segment_c": {"churn_multiplier": 1.8}
    }
  }
}
```

**Use Cases** (across domains):
- Subscription lifecycle (SaaS, streaming)
- Contract renewals (B2B, insurance)
- Membership status (gyms, clubs)
- Device connectivity (IoT)
- Patient treatment status (healthcare)

---

### 5. Multi-Touch Attribution Chains

**Problem**: No support for modeling influence chains where multiple entities contribute to an outcome.

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "attribution_event",
  "kind": "fact",
  "parents": ["entity"],
  "attribution_chain": {
    "touchpoint_types": ["touch_a", "touch_b", "touch_c"],
    "touchpoints_per_conversion": {
      "distribution": "poisson",
      "lambda": 3.5,
      "min": 1,
      "max": 15
    },
    "attribution_window_days": 30,
    "conversion_probability": {
      "base": 0.02,
      "multiplier_per_touch": 1.4,
      "saturation_at": 8
    }
  }
}
```

**Use Cases** (across domains):
- Marketing attribution (ad clicks → purchase)
- Healthcare outcomes (treatments → recovery)
- Academic citations (papers → impact)
- Social influence (shares → viral spread)
- Sales touchpoints (calls/emails → close)

---

### 6. Diffusion and Adoption Curves

**Problem**: No support for modeling how entities adopt/discover/engage with new capabilities over time (S-curves, viral spread).

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "adoption_event",
  "kind": "fact",
  "parents": ["entity"],
  "adoption_model": {
    "curve_type": "s_curve",
    "innovation_diffusion": {
      "innovators": {"pct": 0.025, "time_to_adopt_days": 7},
      "early_adopters": {"pct": 0.135, "time_to_adopt_days": 30},
      "early_majority": {"pct": 0.340, "time_to_adopt_days": 90},
      "late_majority": {"pct": 0.340, "time_to_adopt_days": 180},
      "laggards": {"pct": 0.160, "time_to_adopt_days": 365}
    },
    "engagement_frequency": {
      "high": {"pct": 0.15, "events_per_week": 20},
      "medium": {"pct": 0.45, "events_per_week": 5},
      "low": {"pct": 0.40, "events_per_week": 1}
    }
  }
}
```

**Use Cases** (across domains):
- Product feature adoption (SaaS)
- Technology diffusion (innovation research)
- Disease spread (epidemiology)
- Information propagation (social networks)
- New process adoption (organizational change)

---

### 7. Time Series with Growth Trends and Anomalies

**Problem**: Current datetime_series generates random timestamps. Real time series have directional trends (growth/decay), cycles, and anomalous events.

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "columns": [
    {
      "name": "value_metric",
      "type": "float",
      "generator": {
        "distribution": {
          "type": "lognormal",
          "params": {"mean": 3.0, "sigma": 0.5}
        }
      },
      "modifiers": [
        {
          "transform": "trend",
          "args": {
            "type": "exponential",
            "growth_rate": 0.08,
            "time_reference": "timestamp_column"
          }
        },
        {
          "transform": "seasonality",
          "args": {
            "dimension": "dow",
            "weights": [0.8, 0.95, 1.0, 1.05, 1.25, 1.3, 1.1]
          }
        },
        {
          "transform": "anomaly",
          "args": {
            "spike_dates": ["2024-11-29", "2024-12-25"],
            "spike_multiplier": 3.5,
            "drop_dates": ["2024-07-04"],
            "drop_multiplier": 0.3
          }
        }
      ]
    }
  ]
}
```

**Use Cases** (across domains):
- Revenue forecasting (business)
- Demand planning (supply chain)
- Resource utilization (infrastructure)
- Traffic patterns (transportation)
- Climate trends (environmental science)

---

### 8. Entity Lifecycle State Machines

**Problem**: No support for modeling entities that progress through defined lifecycle stages with state-dependent behavior.

**Proposed Schema Enhancement** (domain-agnostic):
```json
{
  "id": "entity_lifecycle",
  "kind": "fact",
  "parents": ["entity"],
  "lifecycle_model": {
    "stages": [
      {
        "stage_name": "stage_1_initial",
        "duration": {
          "distribution": "lognormal",
          "params": {"mean": 3, "sigma": 1}
        },
        "events_during_stage": {
          "event_types": ["event_a", "event_b"],
          "frequency": "high"
        },
        "exit_probability": 0.75,
        "next_stages": ["stage_2_active", "exited"]
      },
      {
        "stage_name": "stage_2_active",
        "duration": {"distribution": "lognormal", "params": {"mean": 30, "sigma": 10}},
        "events_during_stage": {
          "event_types": ["event_c", "event_d", "event_e"],
          "frequency": "medium"
        },
        "exit_probability": 0.90,
        "next_stages": ["stage_3_mature", "exited"]
      },
      {
        "stage_name": "stage_3_mature",
        "events_during_stage": {
          "event_types": ["event_d", "event_f"],
          "frequency": "low"
        },
        "churn_probability_per_period": 0.05
      }
    ]
  }
}
```

**Use Cases** (across domains):
- User onboarding → activation → retention (SaaS)
- Lead → opportunity → closed (sales)
- Prospect → trial → customer (marketing)
- Symptom → diagnosis → treatment → recovery (healthcare)
- Application → review → decision (admissions)

---

## Implementation Priority (Validated by Blind Analysis)

### CRITICAL Priority (Blocks 80%+ of Executive Analysis)

**These features were explicitly called out by analysts as "critical gaps" or "blockers":**

1. **Entity Vintage Effects** (#1) - **VALIDATED AS CRITICAL**
   - Analyst quote: "All users signed up at once - can't measure true churn or cohort retention"
   - Impact: Enables cohort retention, LTV analysis, churn prediction
   - Domains: SaaS, e-commerce, healthcare, finance, education

2. **Time Series Trends** (#7) - **VALIDATED AS CRITICAL**
   - Analyst quote: "Revenue flat for 3 years, R²=0.0014 - cannot forecast"
   - Impact: Enables growth forecasting, seasonality detection, trend analysis
   - Domains: Any domain with time-series metrics

3. **Entity Segmentation** (#2) - **VALIDATED AS HIGH PRIORITY**
   - Analyst quote: "Can only segment by frequency, not by what users do or their value"
   - Impact: Enables profitability analysis, targeted strategies, segment-specific insights
   - Domains: Any domain with heterogeneous populations

### HIGH Priority (Frequently Requested by Analysts)

4. **Multi-Stage Processes** (#3) - **VALIDATED AS HIGH**
   - Analyst quote: "No event types - blocks 80% of strategic analysis, can't build funnels"
   - Impact: Enables conversion funnels, user journey analysis, drop-off identification
   - Domains: Marketing, sales, onboarding, clinical trials

5. **Recurring Relationships with State Changes** (#4) - **VALIDATED AS MEDIUM-HIGH**
   - Analyst quote: "Zero churn over 3 years - unrealistic and limits analysis"
   - Impact: Enables subscription analytics, churn modeling, lifecycle analysis
   - Domains: SaaS, memberships, contracts, monitoring

### MEDIUM Priority (Nice-to-Have)

6. **Multi-Touch Attribution** (#5) - **MENTIONED BY E-COMM ANALYST**
   - Analyst quote: "Every order tied to one campaign - can't do multi-touch attribution"
   - Impact: Enables marketing ROI, channel optimization, attribution modeling
   - Domains: Marketing, sales, healthcare outcomes

7. **Diffusion/Adoption Curves** (#6) - **NOT MENTIONED IN BLIND ANALYSIS**
   - Impact: Models realistic feature adoption, technology diffusion
   - Domains: Product analytics, innovation research, epidemiology

### LOWER Priority (Advanced/Niche)

8. **Entity Lifecycle State Machines** (#8) - **NOT MENTIONED IN BLIND ANALYSIS**
   - Impact: Advanced journey modeling with complex state transitions
   - Domains: Sales pipelines, patient care pathways, legal processes

---

## Next Steps

1. ✅ Create this document
2. ✅ Generate test datasets from multiple domains
3. ✅ Run blind analysis with haiku agents (2 agents, 2 domains)
4. ✅ Identify gaps between what analysts need vs what data supports
5. ✅ Refine feature proposals based on validated findings
6. ✅ Prioritize implementation roadmap (validated by analyst pain points)
7. 🔄 **Create implementation plan for Phase 1 (Critical features)**
8. 🔄 **Prototype Entity Vintage Effects feature**
9. 🔄 **Prototype Time Series Trends feature**
10. 🔄 **Update example schemas demonstrating new capabilities**

---

## Test Domains for Blind Analysis

We will generate datasets from multiple domains, export them to CSV/Parquet, and give them to haiku agents WITHOUT the schema. The agents will play the role of analysts for executives.

### Domain 1: E-commerce Multi-Shop
- **Schema**: `example/ecomm.json` (existing)
- **Analyst Persona**: VP of Growth
- **Analysis Tasks**:
  - Calculate revenue trends over time
  - Identify top-performing shops and products
  - Analyze customer behavior patterns
  - Measure campaign effectiveness
  - Find growth opportunities
- **Expected Gaps**: No cohort analysis, no customer segments, no trend attribution

### Domain 2: Simple Users & Events
- **Schema**: `examples/simple_users_events.json` (existing)
- **Analyst Persona**: Head of Data
- **Analysis Tasks**:
  - User engagement metrics
  - Activity patterns over time
  - User value segmentation
  - Retention proxy metrics
  - Event frequency analysis
- **Expected Gaps**: No true cohorts, all users created equally, no lifecycle stages

### Domain 3: Marketing Attribution (to be created)
- **Schema**: Create simple marketing schema (campaigns, clicks, conversions)
- **Analyst Persona**: CMO
- **Analysis Tasks**:
  - Campaign ROI
  - Channel effectiveness
  - Conversion funnels
  - Multi-touch attribution
  - Customer acquisition cost
- **Expected Gaps**: No attribution chains, no funnel modeling, random conversions

---

## Success Criteria

A successful domain-agnostic feature set should enable analysts across ANY domain to:

1. ✅ Calculate time-based growth/decay rates
2. ✅ Perform vintage/cohort-based analysis
3. ✅ Identify distinct behavioral segments
4. ✅ Track multi-stage process conversion rates
5. ✅ Measure entity interaction effectiveness
6. ✅ Forecast future metrics based on observable trends
7. ✅ Identify anomalies and outliers in patterns
8. ✅ Calculate entity-level lifetime metrics

---

## Open Questions

1. Should cohort behavior be defined at schema time or inferred from data patterns?
2. How to balance realism vs configurability?
3. Should we support custom behavior functions (e.g., Python callbacks)?
4. How to handle cross-table behavior dependencies (e.g., high-value customers use premium features)?
5. Should we generate "messy" data (duplicates, nulls, outliers) by design?

---

**Status**: ✅ **VALIDATED** - Blind analysis complete, priorities confirmed by analyst feedback
**Last Updated**: 2025-11-09

**Files Generated:**
- `DATAGEN_FEATURE_REQUESTS.md` - This document (refined with validated priorities)
- `BLIND_ANALYSIS_FINDINGS.md` - Comprehensive gap analysis from blind testing
- `ANALYSIS_REPORT_SIMPLE.md` - Head of Data report (660 lines, simple dataset)
- `ANALYSIS_REPORT_ECOMM.md` - VP of Growth report (757 lines, e-commerce dataset)

**Datasets Generated for Testing:**
- `output_simple/` - Simple users & events (1K users, 8K events)
- `output_ecomm/` - E-commerce multi-shop (11 tables, 740K+ rows)
- `analysis_data/` - CSV exports for blind analysis
