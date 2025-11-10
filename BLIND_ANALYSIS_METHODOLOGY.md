# Blind Analysis Methodology - Feature Validation Protocol

> **Purpose**: Validate that generated synthetic data supports real-world analysis WITHOUT revealing the schema to analysts. This ensures features are visible, realistic, and domain-agnostic.

---

## Overview

**Blind analysis** is our primary validation method for advanced analytics features (Phase 4+). AI agents play the role of domain analysts (VP of Growth, Head of Data, etc.) and analyze generated datasets **without access to the schema**. This validates:

1. **Feature Visibility**: Can analysts detect the feature (e.g., cohort retention, trends, segments)?
2. **Realism**: Do patterns look realistic and actionable?
3. **Domain-Agnostic Design**: Does the schema use generic patterns, not domain-specific logic?
4. **Gap Identification**: What analysis can analysts NOT do? What's missing?

---

## Methodology: 5-Phase Process

### Phase 1: Data Generation (Pre-Analysis)

**Goal**: Generate synthetic data from schema with the new feature

**Steps**:
1. Create or update schema with new feature (e.g., `vintage_effects_demo.json`)
2. Generate dataset:
   ```bash
   datagen generate examples/vintage_effects_demo.json --seed 42 -o output_validation
   ```
3. Export to CSV for analysis:
   ```bash
   datagen export examples/vintage_effects_demo.json --data-dir output_validation -o analysis_data --format csv
   ```
4. Verify data generated successfully (check row counts, file sizes)

**Outputs**:
- `analysis_data/*.csv` - Raw data for analysts
- `analysis_data/*.csv.manifest` - Metadata (schema-free)
- `output_validation/` - Parquet files (keep for reference)

---

### Phase 2: Parallel Agent Setup (Multi-Domain, Multi-Subdomain)

**Goal**: Launch **parallel haiku agents per domain**, each starting from different subdomains and expanding

**Architecture**: `N domains × M subdomains × P personas = Total agents`

**Example for Customer/Purchase Domain**:
- Domain: Customer Analytics
  - Agent 1 (VP Growth): Start with purchases → expand to customers → time analysis
  - Agent 2 (Head of Data): Start with customers → expand to purchases → behavioral patterns
  - Agent 3 (Data Scientist): Start with time series → expand to cohorts → segments

**Agent Subdomain Matrix**:

| Domain | Starting Subdomain | Expansion Path | Persona | Key Questions |
|--------|-------------------|----------------|---------|---------------|
| **Customer** | `customer.csv` | → purchases → time | Head of Data | User behavior, activity decay |
| **Customer** | `purchase.csv` | → customers → cohorts | VP Growth | Revenue, retention, LTV |
| **Customer** | Time-based view | → customers → purchases | Data Scientist | Cohort analysis, trends |
| **Product** | `product.csv` | → purchases → customers | Product Manager | Adoption, popularity |
| **Product** | `purchase.csv` | → products → inventory | CFO | Unit economics, margins |
| **Campaign** | `campaign.csv` | → clicks → conversions | CMO | Attribution, ROI |

**Key Principle**: Each agent starts from a **different subdomain** within the same domain, then expands to related subdomains. This validates:
1. **Data completeness**: Can you get to all insights from any starting point?
2. **Join integrity**: Do FK relationships work correctly?
3. **Feature visibility**: Is the feature visible from multiple entry points?
4. **Domain coverage**: Are all aspects of the domain analyzable?

**Agent Instructions Template**:
```markdown
You are a [PERSONA] analyzing a dataset for [COMPANY_TYPE]. You have CSV files but NO schema documentation.

**Your Task**:
1. Explore the data using DuckDB queries
2. Build analysis answering key business questions
3. Identify patterns, trends, and insights
4. Document what you CAN and CANNOT analyze
5. Recommend improvements to data collection

**Key Questions**:
[PERSONA-SPECIFIC QUESTIONS - see below]

**Tools Available**:
- DuckDB for SQL queries
- pandas for data manipulation
- matplotlib/seaborn for visualization

**Constraints**:
- NO access to schema definition
- NO access to generation logic
- Work only from CSV files and metadata

**Output Format**:
- Analysis report (markdown)
- Key findings (bullet points)
- Gaps/limitations (what you couldn't analyze)
- Recommendations (what data is missing)
```

**Persona-Specific Questions**:

**VP of Growth**:
1. What is our revenue trend over time? Can we forecast growth?
2. How do customer cohorts perform over time (retention)?
3. What is customer lifetime value (LTV)? Does it vary by cohort?
4. What is our churn rate? When do customers churn?
5. Which customer segments are most valuable?
6. What drives repeat purchases or engagement?

**Head of Data**:
1. What does user engagement look like over time?
2. Are there distinct user behavior patterns (segments)?
3. How does activity change as users age on the platform?
4. What is data quality like (missing values, outliers)?
5. Can we build predictive models for user behavior?
6. What metrics should we track for product analytics?

---

### Phase 3: Parallel Execution (Multi-Agent, Multi-Subdomain)

**Goal**: Run multiple agents per domain in parallel, each starting from different subdomains

**Execution Pattern for Feature #1 (Vintage Effects)**:

```python
# Domain: Customer Analytics
# Launch 3 parallel agents, each starting from different subdomain

# Agent 1: Start with CUSTOMERS
Task(
    description="Head of Data - Customer subdomain entry",
    model="haiku",
    prompt="""
    You are Head of Data. Start by exploring CUSTOMER data.
    Files available: customer.csv, purchase.csv

    **Starting Point**: customer.csv
    **Expansion Path**: customer → join purchases → time analysis

    Key Questions:
    1. Who are our customers? When did they join?
    2. Do customer cohorts behave differently over time?
    3. Is there activity decay as customers age?
    4. Expand: How do purchases relate to customer age?

    Use DuckDB. Document subdomain expansion path.
    """,
    subagent_type="Explore"
)

# Agent 2: Start with PURCHASES
Task(
    description="VP Growth - Purchase subdomain entry",
    model="haiku",
    prompt="""
    You are VP of Growth. Start by exploring PURCHASE data.
    Files available: customer.csv, purchase.csv

    **Starting Point**: purchase.csv
    **Expansion Path**: purchases → join customers → cohort retention

    Key Questions:
    1. What is our revenue over time? Trends?
    2. Which purchases are most valuable?
    3. Expand: Who are the customers behind these purchases?
    4. Expand: Do early customers have different purchase patterns?

    Use DuckDB. Document subdomain expansion path.
    """,
    subagent_type="Explore"
)

# Agent 3: Start with TIME SERIES
Task(
    description="Data Scientist - Time subdomain entry",
    model="haiku",
    prompt="""
    You are Data Scientist. Start with TIME-BASED analysis.
    Files available: customer.csv, purchase.csv

    **Starting Point**: Temporal patterns
    **Expansion Path**: time trends → cohorts → customer segments

    Key Questions:
    1. What time-based patterns exist in the data?
    2. Are there cohort effects (signup date matters)?
    3. Expand: Do customer attributes explain temporal patterns?
    4. Expand: Can we predict future behavior?

    Use DuckDB. Document subdomain expansion path.
    """,
    subagent_type="Explore"
)
```

**Two-Phase Analysis Approach**:

**Phase 3A: Light Analysis (Discovery)**
- **Goal**: Quick scan of ALL tables to understand structure
- **Data**: First 100-1000 rows per table
- **Duration**: 5-10 minutes per agent
- **Output**: Table summaries, column types, FK relationships discovered

```python
# Light analysis agent for discovery
Task(
    description="Light analysis - table discovery",
    model="haiku",
    prompt="""
    Quick scan of ALL tables (first 1000 rows each).

    For EACH table:
    1. Row count estimate
    2. Column names and types
    3. Potential primary keys
    4. Potential foreign keys (by column name patterns)
    5. Time range (if datetime columns exist)
    6. Sample values

    Use: SELECT * FROM table LIMIT 1000

    Output: Table structure summary for planning full analysis
    """,
    subagent_type="Explore"
)
```

**Phase 3B: Full Analysis (Deep Dive)**
- **Goal**: Complete analysis from specific subdomain entry points
- **Data**: Full tables
- **Duration**: 15-30 minutes per agent
- **Output**: Detailed analysis reports with findings + gaps

```python
# Full analysis agents (run in parallel after light analysis)
# One agent per subdomain entry point as shown above
```

**Agent Count Formula**:
```
Total Agents = (# tables × # personas) + 1 light analysis agent

Example for vintage_effects_demo.json:
- 2 tables (customer, purchase)
- 3 personas (Head of Data, VP Growth, Data Scientist)
- Total: 2×3 + 1 = 7 agents (1 light + 6 deep)
```

**Parallel Execution Rules**:
- ✅ Start with **1 light analysis agent** scanning all tables
- ✅ Then launch **N deep analysis agents** in parallel
- ✅ Each deep agent **starts from different subdomain**
- ✅ Agents **expand to related subdomains** autonomously
- ✅ Agents **document expansion path** (which joins/explorations)
- ❌ Agents do **NOT communicate** with each other
- ❌ Agents do **NOT see** the schema or feature spec
- ✅ Agents have **different time horizons** (VP: long-term, Data: short-term)
- ✅ Agents use **DuckDB** for efficient analysis
- ❌ Agents do **NOT** see the schema JSON
- ❌ Agents do **NOT** know what feature is being tested

**Expected Duration**: 15-30 minutes per agent (parallel)

---

### Phase 4: Gap Analysis (Compare Findings)

**Goal**: Compare what analysts COULD vs COULDN'T do

**Comparison Matrix**:

| Analysis Type | VP of Growth | Head of Data | Feature Validated |
|---------------|--------------|--------------|-------------------|
| Revenue trends | ✅ Can analyze | ⚠️ Partial | Trend modifier (#7) |
| Cohort retention | ❌ All users at once | ❌ No cohorts | Vintage effects (#1) |
| Behavioral segments | ⚠️ By frequency only | ⚠️ By frequency only | Segmentation (#2) |
| Churn patterns | ❌ No churn visible | ❌ No churn visible | State transitions (#4) |
| Conversion funnels | ❌ No event types | ❌ No event types | Multi-stage (#3) |

**Document**:
1. **What Analysts COULD Do**: Successful analyses with examples
2. **What Analysts COULDN'T Do**: Blocked analyses (critical gaps)
3. **Partial Success**: Analyses possible but limited
4. **Unexpected Insights**: Findings we didn't anticipate
5. **Common Patterns**: What both analysts struggled with

**Output File**: `BLIND_ANALYSIS_FINDINGS_[FEATURE].md`

---

### Phase 5: Schema Consultation (Post-Analysis)

**Goal**: ONLY AFTER analysis complete, compare findings to schema to validate feature design

**Validation Checklist**:

**✅ Feature Visibility**:
- [ ] Analysts detected the feature without being told
- [ ] Feature impact is measurable (quantitative)
- [ ] Feature patterns look realistic (not artificial)
- [ ] Feature enables new analysis types

**✅ Domain-Agnostic Design**:
- [ ] Schema uses generic field names (not "MRR", "cohort")
- [ ] Configuration is technical, not business logic
- [ ] Feature works across multiple domains (tested)
- [ ] Analysts describe feature in domain terms (not schema terms)

**✅ Gap Identification**:
- [ ] Known limitations match analyst gaps
- [ ] Unexpected gaps documented
- [ ] Recommendations actionable

**Failure Modes** (require iteration):
- ❌ **Feature Invisible**: Analysts don't detect feature impact
- ❌ **Domain-Specific**: Analysts say "this only works for e-commerce"
- ❌ **Unrealistic**: Analysts say "this data doesn't look real"
- ❌ **Insufficient**: Analysts can't answer key business questions

**Output**: Update schema or feature implementation based on gaps

---

## Example: Feature #1 Validation (Vintage Effects)

### Pre-Analysis Setup

**Schema**: `examples/vintage_effects_demo.json`
```json
{
  "nodes": [{
    "id": "customer",
    "vintage_behavior": {
      "created_at_column": "created_at",
      "age_based_multipliers": {
        "activity_decay": {
          "curve": [1.0, 0.75, 0.60, 0.50, 0.45, 0.40],
          "time_unit": "month",
          "applies_to": "fanout"
        }
      }
    }
  }]
}
```

**Expected Analyst Findings**:
- ✅ VP of Growth: "Early customers have higher retention than recent ones"
- ✅ Head of Data: "User activity decays over time - retention curve visible"
- ✅ Both: "Cohort retention analysis possible - cohorts behave differently"

**Key Validation Questions**:
1. Can analysts measure cohort retention without being told about vintage_behavior?
2. Can analysts say "retention drops 30% after 6 months" from the data?
3. Do retention curves look realistic (not perfectly linear)?
4. Can analysts recommend cohort-based strategies?

---

## Tools & Best Practices

### DuckDB Query Patterns

**Cohort Analysis**:
```sql
-- Cohort retention by signup month
SELECT
  DATE_TRUNC('month', created_at) AS cohort_month,
  DATE_DIFF('month', created_at, purchase_time) AS months_since_signup,
  COUNT(DISTINCT customer_id) AS active_customers,
  COUNT(*) AS purchases
FROM customer
JOIN purchase USING (customer_id)
GROUP BY cohort_month, months_since_signup
ORDER BY cohort_month, months_since_signup;
```

**Trend Detection**:
```sql
-- Revenue trend with linear regression
SELECT
  DATE_TRUNC('month', purchase_time) AS month,
  SUM(amount) AS revenue,
  REGR_SLOPE(SUM(amount), EXTRACT(EPOCH FROM month)) AS growth_rate
FROM purchase
GROUP BY month
ORDER BY month;
```

**Segment Discovery**:
```sql
-- K-means style segment discovery
WITH customer_stats AS (
  SELECT
    customer_id,
    COUNT(*) AS purchase_count,
    AVG(amount) AS avg_amount,
    DATE_DIFF('day', MIN(purchase_time), MAX(purchase_time)) AS lifetime_days
  FROM purchase
  GROUP BY customer_id
)
SELECT
  NTILE(3) OVER (ORDER BY purchase_count) AS activity_segment,
  NTILE(3) OVER (ORDER BY avg_amount) AS value_segment,
  COUNT(*) AS customers
FROM customer_stats
GROUP BY activity_segment, value_segment;
```

### Validation Report Template

```markdown
# Blind Analysis Report: [PERSONA] - [FEATURE]

**Analyst**: [VP of Growth / Head of Data / etc.]
**Dataset**: [Schema name]
**Analysis Date**: YYYY-MM-DD
**Duration**: XX minutes

## Executive Summary

[2-3 sentences: key findings]

## Data Overview

- Tables analyzed: [list]
- Row counts: [table: rows]
- Time range: [start - end]
- Data quality: [assessment]

## Analysis Results

### 1. [Question 1]
[Findings with SQL queries and results]

### 2. [Question 2]
[Findings]

...

## What I COULD Analyze

- ✅ [Analysis type]: [brief description]
- ✅ [Analysis type]: [brief description]

## What I COULDN'T Analyze (Gaps)

- ❌ [Blocked analysis]: [why blocked, what data missing]
- ❌ [Blocked analysis]: [why blocked]

## Recommendations

1. [Data improvement]
2. [Feature request]
3. [Schema change]

## Validation Summary

**Feature Visibility**: [Visible / Partial / Not Detected]
**Realism**: [Realistic / Somewhat / Unrealistic]
**Actionability**: [High / Medium / Low]
```

---

## Success Metrics

**Feature Passes Validation If**:
1. **≥80% of expected analyses succeed** (both analysts)
2. **Feature is detected without hints** (analysts mention it unprompted)
3. **Patterns look realistic** (analysts don't flag as "artificial")
4. **Enables new insights** (analysts can answer questions previously blocked)
5. **Domain-agnostic confirmed** (schema uses generic patterns, not domain terms)

**Feature Fails Validation If**:
1. **<50% of expected analyses succeed**
2. **Feature is invisible** (analysts don't detect impact)
3. **Patterns look artificial** (analysts flag as "generated data")
4. **No new insights** (same analyses as before)
5. **Domain-specific** (only works for one industry)

---

## Iteration Process

**If validation fails**:

1. **Analyze gaps** - What specific analyses failed?
2. **Root cause** - Is it schema config, feature implementation, or data volume?
3. **Iterate schema** - Adjust parameters (e.g., decay curve steepness)
4. **Regenerate data** - New seed, verify changes visible
5. **Re-run blind analysis** - Same agents, new data
6. **Compare** - Did gaps close? New gaps emerge?

**Maximum 3 iterations** - If still failing, may need feature redesign

---

## Archive & Documentation

**After Validation**:

1. **Save analysis reports**:
   - `ANALYSIS_REPORT_[FEATURE]_[PERSONA].md`
   - `BLIND_ANALYSIS_FINDINGS_[FEATURE].md`

2. **Update feature status**:
   - PRD.md: Mark feature as validated
   - GOAL.md: Update metrics
   - DATAGEN_FEATURE_REQUESTS.md: Add validation results

3. **Create reference example**:
   - Example schema in `examples/`
   - Document expected analyst findings
   - Include in test suite for regression

---

## Checklist: Running Blind Analysis

**Pre-Analysis**:
- [ ] Feature implemented and tested (unit tests pass)
- [ ] Example schema created with feature enabled
- [ ] Data generated and exported to CSV
- [ ] Agent personas defined (VP Growth + Head Data minimum)
- [ ] Key validation questions documented

**During Analysis**:
- [ ] Launch agents in parallel (independent)
- [ ] Agents start from different tables
- [ ] Agents use DuckDB for efficient queries
- [ ] Agents document findings and gaps
- [ ] NO schema access for agents

**Post-Analysis**:
- [ ] Compare findings across agents
- [ ] Document gaps and successes
- [ ] Consult schema to validate feature design
- [ ] Check domain-agnostic principle
- [ ] Decide: pass validation or iterate

**Documentation**:
- [ ] Analysis reports saved
- [ ] Findings document created
- [ ] PRD/GOAL updated
- [ ] Example schema added to repo

---

**This methodology is the gold standard for validating Phase 4+ features. Every advanced analytics feature MUST pass blind analysis before being considered complete.**
