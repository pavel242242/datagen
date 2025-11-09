# Domain-Agnostic Testing Checklist

> **Purpose**: Ensure datagen schemas and features are **domain-agnostic** - they represent **technical data patterns**, not business logic. This allows the same feature to work across any industry.

---

## Core Principle

**Datagen schemas should describe HOW data looks, not WHAT it means.**

- ✅ **Good**: "Entity with created_at timestamp, activity decay curve, age-based multipliers"
- ❌ **Bad**: "Customer with signup date, cohort retention, monthly recurring revenue"

**Why This Matters**:
1. **Portability**: Same schema works for SaaS, e-commerce, manufacturing, healthcare
2. **LLM-Friendly**: LLMs can generate schemas without domain expertise
3. **Testability**: Can validate across multiple domains
4. **Maintainability**: One feature implementation serves all use cases

---

## Testing Protocol for New Features

**Every new feature MUST pass domain-agnostic testing before completion.**

### Step 1: Schema Audit (Pre-Implementation)

**Checklist for Schema Design**:

```json
// ❌ DOMAIN-SPECIFIC (bad)
{
  "id": "customer",
  "columns": [{
    "name": "mrr",  // Monthly Recurring Revenue - SaaS-specific
    "name": "cohort_month",  // Business concept
    "name": "churn_probability"  // Business metric
  }],
  "vintage_behavior": {
    "retention_curve": {...}  // Business term
  }
}

// ✅ DOMAIN-AGNOSTIC (good)
{
  "id": "entity",  // Or: user, customer, device, patient - generic entity
  "columns": [{
    "name": "value",  // Or: amount, quantity, metric - generic measure
    "name": "created_at",  // Technical timestamp
    "name": "category"  // Generic classification
  }],
  "vintage_behavior": {
    "age_based_multipliers": {  // Technical description
      "activity_decay": {  // Pattern name, not business metric
        "curve": [1.0, 0.75, 0.6],  // Technical curve
        "applies_to": "fanout"  // Technical application
      }
    }
  }
}
```

**Schema Field Naming Audit**:

| Category | ❌ Domain-Specific | ✅ Domain-Agnostic |
|----------|-------------------|-------------------|
| **Entity Names** | customer, subscriber, patient | entity, user, record |
| **Metrics** | mrr, ltv, cac, nps | value, amount, score, metric |
| **Time Concepts** | cohort_month, churn_date | created_at, event_time, timestamp |
| **Behaviors** | retention, conversion, engagement | activity, transition, state |
| **Curves** | retention_curve, adoption_s_curve | decay_curve, growth_curve |
| **Multipliers** | vip_boost, enterprise_premium | segment_multiplier, value_multiplier |

**Pass Criteria**:
- [ ] NO business terms in field names
- [ ] NO domain-specific metrics (MRR, LTV, CAC, etc.)
- [ ] Configuration describes PATTERNS, not BUSINESS LOGIC
- [ ] Same schema could be used in 3+ different industries

---

### Step 2: Multi-Domain Translation Test

**Goal**: Verify the same schema can be interpreted across multiple domains

**Test**: Create 5 domain translations of your schema

**Example: Feature #1 (Vintage Effects)**

**Base Schema** (domain-agnostic):
```json
{
  "id": "entity",
  "vintage_behavior": {
    "created_at_column": "created_at",
    "age_based_multipliers": {
      "activity_decay": {
        "curve": [1.0, 0.75, 0.6, 0.5, 0.4],
        "time_unit": "month",
        "applies_to": "fanout"
      },
      "value_growth": {
        "curve": {"curve_type": "logarithmic", "params": {"a": 1.0, "b": 0.15}},
        "time_unit": "month",
        "applies_to": ["amount"]
      }
    }
  }
}
```

**Translation 1: SaaS / Subscription Business**
- `entity` = customer
- `created_at` = signup_date
- `activity_decay` = retention decay / churn increase
- `value_growth` = expansion revenue / upsell
- **Use Case**: Cohort retention analysis, LTV forecasting

**Translation 2: E-Commerce**
- `entity` = customer
- `created_at` = first_purchase_date
- `activity_decay` = repeat purchase frequency decline
- `value_growth` = average order value increase
- **Use Case**: Customer lifetime value, repeat rate analysis

**Translation 3: Manufacturing / IoT**
- `entity` = device / sensor
- `created_at` = installation_date
- `activity_decay` = data reporting frequency decline (wear/tear)
- `value_growth` = data quality improvement (calibration)
- **Use Case**: Predictive maintenance, sensor health tracking

**Translation 4: Healthcare**
- `entity` = patient
- `created_at` = admission_date / enrollment_date
- `activity_decay` = appointment frequency decline
- `value_growth` = treatment complexity increase
- **Use Case**: Patient engagement, long-term care analysis

**Translation 5: Publishing / Content**
- `entity` = author / publication
- `created_at` = publication_date
- `activity_decay` = citation rate decline over time
- `value_growth` = citation impact growth (seminal papers)
- **Use Case**: Citation analysis, research impact measurement

**Pass Criteria**:
- [ ] Schema works for ≥5 different domains
- [ ] No schema changes needed per domain (just interpretation)
- [ ] Each domain has clear, realistic use case
- [ ] Analysts in each domain would find the data realistic

---

### Step 3: Blind Analysis Cross-Validation

**Goal**: Analysts from different domains interpret data correctly WITHOUT being told the domain

**Test Procedure**:

1. **Generate data** from domain-agnostic schema
2. **Present to 3 analysts** from different domains (SaaS, E-commerce, Healthcare)
3. **Ask each**: "What domain is this data from? What business are we analyzing?"
4. **Expected Result**: Each analyst should be able to map it to THEIR domain

**Example Prompt for Analysts**:
```markdown
You are a VP of Growth. Analyze this dataset (customer.csv, purchase.csv).

Question: Based on the data patterns, what type of business is this?

Expected answers (all valid):
- "This looks like SaaS subscription data with cohort retention"
- "This looks like e-commerce with repeat purchase patterns"
- "This looks like healthcare patient engagement data"
```

**Pass Criteria**:
- [ ] ≥3 analysts from different domains find data plausible for THEIR domain
- [ ] No analyst says "this doesn't look like real [domain] data"
- [ ] Analysts describe patterns using domain-specific terms (good!)
- [ ] But underlying data structure is domain-agnostic (good!)

---

### Step 4: Schema Documentation Review

**Goal**: Documentation uses domain-agnostic language

**Checklist for Feature Documentation**:

```markdown
# Feature #1: Entity Vintage Effects

## Description
Entities created at different times exhibit different behavioral patterns over their lifetime.
Supports age-based activity decay and value growth curves.

## Use Cases (domain-agnostic)
- Time-based entity behavior analysis
- Cohort-style comparisons
- Lifetime value patterns
- Activity engagement trends

## Use Cases (domain examples)
- SaaS: Customer cohort retention and expansion revenue
- E-commerce: Repeat purchase patterns and customer LTV
- Manufacturing: Device degradation and maintenance scheduling
- Healthcare: Patient engagement and treatment progression
```

**Pass Criteria**:
- [ ] Feature description uses TECHNICAL terms, not domain terms
- [ ] Use cases section lists 4+ different domains
- [ ] Examples show SAME feature applied to different domains
- [ ] Configuration parameters are domain-neutral

---

### Step 5: Implementation Validation

**Goal**: Verify implementation has NO domain-specific logic

**Code Audit Checklist**:

```python
# ❌ DOMAIN-SPECIFIC CODE (bad)
def calculate_mrr(entity_ages):
    """Calculate Monthly Recurring Revenue based on cohort."""
    if entity_type == "customer":  # Domain check - bad!
        return base_value * retention_curve[cohort_month]

# ✅ DOMAIN-AGNOSTIC CODE (good)
def apply_vintage_multipliers_to_values(
    values: np.ndarray,
    entity_ages: np.ndarray,
    column_name: str,
    vintage_config: dict
) -> np.ndarray:
    """Apply age-based multipliers to column values.

    Works for ANY domain - just multiplies values by age-based curve.
    """
    # No domain-specific logic - just apply curve
    multipliers = evaluate_curve(entity_ages, curve_spec)
    return values * multipliers
```

**Pass Criteria**:
- [ ] NO domain-specific variable names (mrr, ltv, cohort, retention)
- [ ] NO conditional logic based on entity type or domain
- [ ] Functions are PURE transformations (input → output)
- [ ] Parameters are GENERIC (curve, multiplier, age, value)

---

### Step 6: Schema Example Library

**Goal**: Provide examples across multiple domains to prove portability

**Required Examples Per Feature**:

For each new feature, create **3+ example schemas** in different domains:

**Example for Feature #1 (Vintage Effects)**:

1. **`examples/vintage_effects_saas.json`**
   - Customer retention with activity decay
   - Expansion revenue with value growth
   - Comment: "SaaS cohort retention analysis"

2. **`examples/vintage_effects_ecommerce.json`**
   - Customer repeat purchase frequency decay
   - Average order value growth
   - Comment: "E-commerce customer lifetime value"

3. **`examples/vintage_effects_iot.json`**
   - Device reporting frequency decay
   - Sensor data quality growth
   - Comment: "IoT device health monitoring"

**Pass Criteria**:
- [ ] ≥3 example schemas in different domains
- [ ] All use SAME feature configuration structure
- [ ] Comments explain domain interpretation
- [ ] Examples generate realistic data for each domain

---

## Summary Checklist

**For every new feature, verify**:

### Design Phase
- [ ] Schema audit: No domain-specific terms in field names
- [ ] Multi-domain translation: Works for ≥5 domains
- [ ] Documentation: Uses domain-agnostic language

### Implementation Phase
- [ ] Code audit: No domain-specific logic
- [ ] Function names: Generic, not business-specific
- [ ] Parameters: Technical, not domain terms

### Validation Phase
- [ ] Blind analysis: ≥3 analysts find data plausible for their domains
- [ ] Example library: ≥3 example schemas in different domains
- [ ] Gap analysis: No analyst says "only works for [domain]"

### Documentation Phase
- [ ] Feature docs: List ≥4 domain use cases
- [ ] Configuration reference: Explains TECHNICAL behavior
- [ ] Examples: Show SAME config for different domains

---

## Failure Modes & Fixes

### Failure Mode 1: Domain-Specific Naming

**Symptom**: Schema has fields like `mrr`, `churn`, `cohort_month`

**Fix**:
```json
// Before
{"name": "mrr", "name": "churn_probability"}

// After
{"name": "recurring_value", "name": "attrition_likelihood"}

// Even better
{"name": "value", "name": "probability"}
```

---

### Failure Mode 2: Business Logic in Code

**Symptom**: Code has conditionals like `if entity_type == "customer"`

**Fix**:
```python
# Before
if entity_type == "customer":
    apply_retention_logic()
elif entity_type == "device":
    apply_uptime_logic()

# After
multipliers = evaluate_curve(entity_ages, config["curve"])
values *= multipliers  # Same logic for all entity types
```

---

### Failure Mode 3: Single-Domain Examples

**Symptom**: All examples are SaaS/e-commerce only

**Fix**: Create examples for:
- Healthcare (patient engagement)
- Manufacturing (equipment maintenance)
- Academic (publication citations)
- Finance (account maturity)
- Government (service usage)

---

## Test Report Template

```markdown
# Domain-Agnostic Testing Report: Feature #N

**Feature**: [Name]
**Date**: YYYY-MM-DD
**Tester**: [Name]

## Step 1: Schema Audit
- [ ] No domain-specific field names
- [ ] Configuration is technical, not business

**Issues Found**: [List or "None"]

## Step 2: Multi-Domain Translation
- [ ] SaaS interpretation: [Description]
- [ ] E-commerce interpretation: [Description]
- [ ] Manufacturing interpretation: [Description]
- [ ] Healthcare interpretation: [Description]
- [ ] Other interpretation: [Description]

**Issues Found**: [List or "None"]

## Step 3: Blind Analysis Cross-Validation
- [ ] Analyst 1 (SaaS): Data plausible for SaaS
- [ ] Analyst 2 (E-comm): Data plausible for E-commerce
- [ ] Analyst 3 (Healthcare): Data plausible for Healthcare

**Issues Found**: [List or "None"]

## Step 4: Implementation Audit
- [ ] No domain-specific function names
- [ ] No business logic conditionals
- [ ] All parameters are generic

**Issues Found**: [List or "None"]

## Step 5: Example Library
- [ ] ≥3 examples in different domains
- [ ] All use same configuration structure

**Examples Created**: [List]

## Overall Result

**PASS** / **FAIL** / **PASS WITH MINOR ISSUES**

**Required Actions**: [List fixes needed]
```

---

## Storing Test Results

**Location**: `docs/validation/domain-agnostic/`

```
docs/validation/domain-agnostic/
├── README.md (this file)
├── feature-1-vintage-effects.md
├── feature-2-segmentation.md
├── feature-7-trends.md
└── ...
```

**Each Feature Gets**:
1. Test report (using template above)
2. Multi-domain translation table
3. Blind analysis results from ≥3 domains
4. Example schemas (≥3 domains)

---

**This checklist is MANDATORY for all Phase 4+ features. Domain-agnostic design is a core principle and must be validated before features are considered complete.**
