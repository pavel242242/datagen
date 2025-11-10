-- DuckDB Queries: Cohort Retention Analysis
-- Dataset: SaaS Onboarding (Jan 2023 - Jun 2024, 500 accounts)

-- ============================================
-- QUERY 1: Tier Performance Comparison
-- ============================================
-- Shows engagement metrics by tier across all accounts

WITH account_sessions AS (
  SELECT
    a.account_id,
    a.tier,
    COUNT(DISTINCT us.session_id) as session_count,
    SUM(COALESCE(us.duration_minutes, 0)) as total_duration
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier
)
SELECT
  tier,
  COUNT(*) as total_accounts,
  ROUND(AVG(session_count), 1) as avg_sessions_per_account,
  ROUND(AVG(total_duration), 1) as avg_duration_min,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN session_count >= 5 THEN account_id END) / COUNT(*), 1) as pct_5plus_sessions
FROM account_sessions
GROUP BY tier
ORDER BY avg_sessions_per_account DESC;

-- ============================================
-- QUERY 2: Day 7, 30, 90 Retention by Cohort
-- ============================================
-- Key milestone retention analysis

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
)
SELECT
  cohort_month,
  tier,
  COUNT(DISTINCT ac.account_id) as cohort_size,
  ROUND(100.0 * COUNT(DISTINCT CASE
    WHEN sd.first_session_date IS NOT NULL AND (sd.first_session_date - ac.signup_date) <= 7
    THEN ac.account_id
  END) / COUNT(DISTINCT ac.account_id), 1) as day7_retention_pct,
  ROUND(100.0 * COUNT(DISTINCT CASE
    WHEN sd.first_session_date IS NOT NULL AND (sd.first_session_date - ac.signup_date) <= 30
    THEN ac.account_id
  END) / COUNT(DISTINCT ac.account_id), 1) as day30_retention_pct
FROM account_cohorts ac
LEFT JOIN session_days sd ON ac.account_id = sd.account_id
GROUP BY cohort_month, tier
ORDER BY cohort_month DESC, tier;

-- ============================================
-- QUERY 3: Churn Status Classification
-- ============================================
-- Current engagement status for all accounts

WITH account_data AS (
  SELECT
    a.account_id,
    a.tier,
    MAX(us.session_start)::DATE as last_session_date,
    COUNT(DISTINCT us.session_id) as session_count
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier
),
ref_date AS (
  SELECT MAX(session_start)::DATE as ref_date FROM 'output_onboarding/usage_session.parquet'
)
SELECT
  a.tier,
  CASE
    WHEN session_count = 0 THEN 'Never Activated'
    WHEN (r.ref_date - last_session_date) > 60 THEN 'Churned'
    WHEN (r.ref_date - last_session_date) > 30 THEN 'At Risk'
    WHEN (r.ref_date - last_session_date) > 7 THEN 'Disengaging'
    ELSE 'Active'
  END as status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY a.tier), 1) as pct_of_tier
FROM account_data a
CROSS JOIN ref_date r
GROUP BY a.tier, status
ORDER BY a.tier;

-- ============================================
-- QUERY 4: Newer vs Older Cohorts
-- ============================================
-- Year-over-year engagement comparison

WITH account_data AS (
  SELECT
    a.account_id,
    a.tier,
    CASE WHEN a.signup_date >= '2024-01-01' THEN 'Newer (2024)' ELSE 'Older (2023)' END as cohort_age,
    COUNT(DISTINCT us.session_id) as session_count
  FROM 'output_onboarding/account.parquet' a
  LEFT JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
  GROUP BY a.account_id, a.tier, a.signup_date
)
SELECT
  cohort_age,
  tier,
  COUNT(*) as accounts,
  ROUND(AVG(session_count), 1) as avg_sessions,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN session_count >= 5 THEN account_id END) / COUNT(*), 1) as engagement_5plus_pct
FROM account_data
GROUP BY cohort_age, tier
ORDER BY cohort_age DESC, tier;

-- ============================================
-- QUERY 5: Time to Activation
-- ============================================
-- How quickly accounts activate after signup

WITH activation_data AS (
  SELECT
    a.account_id,
    a.tier,
    DATE_TRUNC('month', a.signup_date)::DATE as cohort_month,
    (MIN(us.session_start)::DATE - a.signup_date::DATE) as days_to_first_session
  FROM 'output_onboarding/account.parquet' a
  JOIN 'output_onboarding/usage_session.parquet' us ON a.account_id = us.account_id
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
