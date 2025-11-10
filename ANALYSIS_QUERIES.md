# DuckDB Analysis Queries - Retention Analysis

This document contains all DuckDB queries used for the cohort retention analysis. These can be run directly against the parquet files in `/home/user/datagen/output_onboarding/`.

**Files analyzed:**
- `account.parquet` - 500 accounts with signup_date, tier, company_name, industry
- `usage_session.parquet` - 5,807 sessions with session_start, duration_minutes, actions_count
- `onboarding_event.parquet` - 1,949 onboarding events (not used in retention analysis)

---

## Query 1: Tier Performance Comparison

Shows engagement metrics aggregated across all accounts by tier.

```sql
WITH account_sessions AS (
  SELECT 
    a.account_id,
    a.tier,
    COUNT(DISTINCT us.session_id) as session_count,
    SUM(COALESCE(us.duration_minutes, 0)) as total_duration,
    SUM(COALESCE(us.actions_count, 0)) as total_actions
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier
)
SELECT 
  tier,
  COUNT(*) as total_accounts,
  ROUND(AVG(session_count), 1) as avg_sessions_per_account,
  ROUND(AVG(total_duration), 1) as avg_total_duration_min,
  ROUND(AVG(total_actions), 1) as avg_total_actions,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY session_count) as median_sessions,
  COUNT(DISTINCT CASE WHEN session_count >= 5 THEN account_id END) as accounts_5plus_sessions,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN session_count >= 5 THEN account_id END) / COUNT(*), 1) as pct_5plus_sessions
FROM account_sessions
GROUP BY tier
ORDER BY avg_sessions_per_account DESC;
```

**Key metrics returned:**
- `total_accounts`: Number of accounts in tier
- `avg_sessions_per_account`: Mean engagement
- `median_sessions`: 50th percentile (robust average)
- `pct_5plus_sessions`: % of accounts that reach 5+ sessions (engagement rate)

---

## Query 2: Day 7, 30, 90 Retention by Cohort

Calculates retention at key milestones (7, 30, 90 days after signup).

```sql
WITH account_cohorts AS (
  SELECT 
    account_id,
    tier,
    DATE_TRUNC('month', signup_date)::DATE as cohort_month,
    signup_date::DATE as signup_date
  FROM 'output_onboarding/account.parquet'
),
session_days AS (
  SELECT 
    account_id,
    MIN(session_start)::DATE as first_session_date
  FROM 'output_onboarding/usage_session.parquet'
  GROUP BY account_id
),
retention_data AS (
  SELECT 
    ac.cohort_month,
    ac.tier,
    COUNT(DISTINCT ac.account_id) as cohort_size,
    COUNT(DISTINCT CASE 
      WHEN sd.first_session_date IS NOT NULL AND 
           (sd.first_session_date - ac.signup_date) <= 7
      THEN ac.account_id 
    END) as day7_active,
    COUNT(DISTINCT CASE 
      WHEN sd.first_session_date IS NOT NULL AND 
           (sd.first_session_date - ac.signup_date) <= 30
      THEN ac.account_id 
    END) as day30_active,
    COUNT(DISTINCT CASE 
      WHEN sd.first_session_date IS NOT NULL AND 
           (sd.first_session_date - ac.signup_date) <= 90
      THEN ac.account_id 
    END) as day90_active
  FROM account_cohorts ac
  LEFT JOIN session_days sd ON ac.account_id = sd.account_id
  GROUP BY ac.cohort_month, ac.tier
)
SELECT 
  cohort_month,
  tier,
  cohort_size,
  day7_active,
  ROUND(100.0 * day7_active / cohort_size, 1) as day7_retention_pct,
  day30_active,
  ROUND(100.0 * day30_active / cohort_size, 1) as day30_retention_pct,
  day90_active,
  ROUND(100.0 * day90_active / cohort_size, 1) as day90_retention_pct
FROM retention_data
ORDER BY cohort_month DESC, tier;
```

**Key metrics returned:**
- `cohort_month`: Signup month (Jan 2023 - Jun 2024)
- `day7_retention_pct`: % of cohort with session within 7 days of signup
- `day30_retention_pct`: % of cohort with session within 30 days
- `day90_retention_pct`: % of cohort with session within 90 days

---

## Query 3: Churn Status Classification

Classifies all accounts into engagement buckets based on last activity date.

```sql
WITH account_data AS (
  SELECT 
    a.account_id,
    a.tier,
    a.signup_date,
    MAX(us.session_start)::DATE as last_session_date,
    COUNT(DISTINCT us.session_id) as session_count
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier, a.signup_date
),
ref_date AS (
  SELECT MAX(session_start)::DATE as ref_date FROM 'output_onboarding/usage_session.parquet'
),
churn_classification AS (
  SELECT 
    a.*,
    r.ref_date,
    CASE 
      WHEN session_count = 0 THEN 'Never Activated'
      WHEN session_count = 1 THEN 'One-time User'
      WHEN (r.ref_date - last_session_date) > 60 THEN 'Churned (60+ days)'
      WHEN (r.ref_date - last_session_date) > 30 THEN 'At Risk (30-60 days)'
      WHEN (r.ref_date - last_session_date) > 7 THEN 'Disengaging (7-30 days)'
      ELSE 'Active (0-7 days)'
    END as engagement_status
  FROM account_data a
  CROSS JOIN ref_date r
)
SELECT 
  tier,
  engagement_status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY tier), 1) as pct_of_tier
FROM churn_classification
GROUP BY tier, engagement_status
ORDER BY tier, 
  CASE engagement_status 
    WHEN 'Active (0-7 days)' THEN 1
    WHEN 'Disengaging (7-30 days)' THEN 2
    WHEN 'At Risk (30-60 days)' THEN 3
    WHEN 'Churned (60+ days)' THEN 4
    WHEN 'Never Activated' THEN 5
    WHEN 'One-time User' THEN 6
  END;
```

**Key metrics returned:**
- `engagement_status`: Current status of account based on last session
- `pct_of_tier`: % of accounts in this status (within each tier)

---

## Query 4: Cohort Activation & Engagement Rates

Shows activation and engagement success rates by cohort and tier.

```sql
WITH account_cohorts AS (
  SELECT 
    DATE_TRUNC('month', signup_date)::DATE as cohort_month,
    account_id,
    tier,
    signup_date::DATE as signup_date
  FROM 'output_onboarding/account.parquet'
),
session_metrics AS (
  SELECT 
    account_id,
    COUNT(DISTINCT session_id) as session_count,
    MIN(session_start)::DATE as first_session_date,
    MAX(session_start)::DATE as last_session_date
  FROM 'output_onboarding/usage_session.parquet'
  GROUP BY account_id
),
cohort_metrics AS (
  SELECT 
    ac.cohort_month,
    ac.tier,
    COUNT(DISTINCT ac.account_id) as cohort_size,
    COUNT(DISTINCT CASE WHEN sm.account_id IS NOT NULL THEN ac.account_id END) as activated,
    COUNT(DISTINCT CASE WHEN sm.session_count >= 5 THEN ac.account_id END) as engaged_5_plus,
    COUNT(DISTINCT CASE WHEN sm.session_count >= 10 THEN ac.account_id END) as engaged_10_plus,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN sm.account_id IS NOT NULL THEN ac.account_id END) / 
          COUNT(DISTINCT ac.account_id), 1) as activation_rate,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN sm.session_count >= 5 THEN ac.account_id END) / 
          COUNT(DISTINCT ac.account_id), 1) as engagement_rate_5plus
  FROM account_cohorts ac
  LEFT JOIN session_metrics sm ON ac.account_id = sm.account_id
  GROUP BY ac.cohort_month, ac.tier
)
SELECT * FROM cohort_metrics
ORDER BY cohort_month DESC, tier;
```

**Key metrics returned:**
- `activation_rate`: % of cohort with at least 1 session
- `engagement_rate_5plus`: % of cohort with 5+ sessions

---

## Query 5: Newer vs Older Cohorts Comparison

Compares 2024 cohorts (newer) against 2023 cohorts (older) to detect improvement trends.

```sql
WITH account_data AS (
  SELECT 
    a.account_id,
    a.tier,
    a.signup_date,
    CASE 
      WHEN a.signup_date >= '2024-01-01' THEN 'Newer (2024)'
      ELSE 'Older (2023)'
    END as cohort_age,
    COUNT(DISTINCT us.session_id) as session_count,
    SUM(COALESCE(us.duration_minutes, 0)) as total_duration,
    SUM(COALESCE(us.actions_count, 0)) as total_actions
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier, a.signup_date
)
SELECT 
  cohort_age,
  tier,
  COUNT(*) as accounts,
  ROUND(AVG(session_count), 1) as avg_sessions,
  ROUND(AVG(total_duration), 1) as avg_duration_min,
  ROUND(AVG(total_actions), 1) as avg_actions,
  COUNT(DISTINCT CASE WHEN session_count >= 5 THEN account_id END) as engaged_5plus,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN session_count >= 5 THEN account_id END) / COUNT(*), 1) as engagement_rate
FROM account_data
GROUP BY cohort_age, tier
ORDER BY cohort_age DESC, tier;
```

**Key metrics returned:**
- Compare avg_sessions between 'Newer (2024)' and 'Older (2023)' to detect YoY improvement
- YoY % improvement = ((2024 value - 2023 value) / 2023 value) * 100

---

## Query 6: Time to First Session (Activation Speed)

Measures how quickly activated accounts first engage with the product.

```sql
WITH activation_data AS (
  SELECT 
    a.account_id,
    a.tier,
    a.signup_date,
    DATE_TRUNC('month', a.signup_date)::DATE as cohort_month,
    MIN(us.session_start)::DATE as first_session_date,
    (MIN(us.session_start)::DATE - a.signup_date::DATE) as days_to_first_session
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  WHERE us.session_id IS NOT NULL
  GROUP BY a.account_id, a.tier, a.signup_date
)
SELECT 
  cohort_month,
  tier,
  COUNT(*) as activated_accounts,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_first_session) as median_days_to_activation,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY days_to_first_session) as p25_days,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY days_to_first_session) as p75_days
FROM activation_data
GROUP BY cohort_month, tier
ORDER BY cohort_month DESC, tier;
```

**Key metrics returned:**
- `median_days_to_activation`: Typical activation lag (7-day, 14-day, 30-day activators?)
- P25/P75: Interquartile range shows activation speed variance

---

## Query 7: Engagement Depth by Cohort

Shows session count, duration, and actions by cohort (comprehensive engagement view).

```sql
WITH cohort_engagement AS (
  SELECT 
    DATE_TRUNC('month', a.signup_date)::DATE as cohort_month,
    a.tier,
    COUNT(DISTINCT a.account_id) as cohort_size,
    ROUND(AVG(COALESCE(us.duration_minutes, 0)), 1) as avg_session_duration_min,
    ROUND(AVG(COALESCE(us.actions_count, 0)), 1) as avg_actions_per_session,
    COUNT(DISTINCT us.session_id) as total_sessions,
    COUNT(DISTINCT a.account_id) as accounts_with_sessions,
    ROUND(COUNT(DISTINCT us.session_id)::NUMERIC / NULLIF(COUNT(DISTINCT a.account_id), 0), 1) as avg_sessions_per_account,
    ROUND(SUM(COALESCE(us.duration_minutes, 0))::NUMERIC / NULLIF(COUNT(DISTINCT a.account_id), 0), 1) as total_duration_per_account
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY cohort_month, a.tier
  ORDER BY cohort_month DESC, a.tier
)
SELECT * FROM cohort_engagement;
```

**Key metrics returned:**
- `avg_session_duration_min`: Session depth (minutes per session)
- `avg_actions_per_session`: Feature usage per session
- `avg_sessions_per_account`: Engagement multiplier (sessions per account)
- `total_duration_per_account`: Lifetime engagement (total minutes per account)

---

## How to Run These Queries

```bash
# Install duckdb (if needed)
pip install duckdb

# Run a query interactively
python3 << 'EOF'
import duckdb
conn = duckdb.connect(':memory:')

# Query 1 - Tier Performance
result = conn.execute("""
WITH account_sessions AS (
  SELECT 
    a.account_id,
    a.tier,
    COUNT(DISTINCT us.session_id) as session_count,
    SUM(COALESCE(us.duration_minutes, 0)) as total_duration,
    SUM(COALESCE(us.actions_count, 0)) as total_actions
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier
)
SELECT 
  tier,
  COUNT(*) as total_accounts,
  ROUND(AVG(session_count), 1) as avg_sessions_per_account
FROM account_sessions
GROUP BY tier
ORDER BY avg_sessions_per_account DESC
""").df()

print(result)
