-- ============================================================================
-- PRODUCT ADOPTION ANALYSIS - DuckDB SQL QUERIES REFERENCE
-- ============================================================================
-- This file contains all SQL queries used in the adoption analysis
-- Use with DuckDB against the parquet files in /home/user/datagen/output_adoption/

-- Query 1: Feature Adoption Rate Analysis
-- ============================================================================
-- Shows adoption rate for each feature, sorted by popularity

WITH feature_counts AS (
    SELECT 
        feature_name,
        COUNT(DISTINCT user_id) as adopters,
        (SELECT COUNT(DISTINCT user_id) FROM read_parquet('/home/user/datagen/output_adoption/user.parquet')) as total_users
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
    GROUP BY feature_name
)
SELECT 
    feature_name,
    adopters,
    total_users,
    ROUND(100.0 * adopters / total_users, 2) as adoption_rate_pct
FROM feature_counts
ORDER BY adopters DESC;

-- Query 2: Time-to-First-Feature Adoption Distribution
-- ============================================================================
-- Calculate days from signup to first feature adoption by user

WITH first_adoption AS (
    SELECT 
        u.user_id,
        u.joined_at,
        MIN(f.adopted_at) as first_feature_adoption,
        EXTRACT(DAY FROM (MIN(f.adopted_at) - u.joined_at)) as days_to_first_feature
    FROM read_parquet('/home/user/datagen/output_adoption/user.parquet') u
    LEFT JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f ON u.user_id = f.user_id
    GROUP BY u.user_id, u.joined_at
)
SELECT 
    COUNT(DISTINCT user_id) as users_with_adoption,
    ROUND(AVG(days_to_first_feature), 2) as avg_days_to_first_feature,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_first_feature), 2) as median_days,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY days_to_first_feature), 2) as q1_days,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY days_to_first_feature), 2) as q3_days,
    MIN(days_to_first_feature) as min_days,
    MAX(days_to_first_feature) as max_days
FROM first_adoption
WHERE first_feature_adoption IS NOT NULL;

-- Query 3: Time-to-First-Feature by Adoption Speed Segment
-- ============================================================================
-- Segment users by how quickly they adopt their first feature

WITH first_adoption AS (
    SELECT 
        u.user_id,
        u.joined_at,
        MIN(f.adopted_at) as first_feature_adoption,
        EXTRACT(DAY FROM (MIN(f.adopted_at) - u.joined_at)) as days_to_first_feature
    FROM read_parquet('/home/user/datagen/output_adoption/user.parquet') u
    LEFT JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f ON u.user_id = f.user_id
    GROUP BY u.user_id, u.joined_at
),
segments AS (
    SELECT 
        CASE 
            WHEN days_to_first_feature <= 1 THEN 'Immediate (0-1 day)'
            WHEN days_to_first_feature <= 7 THEN 'Quick (2-7 days)'
            WHEN days_to_first_feature <= 30 THEN 'Medium (8-30 days)'
            ELSE 'Delayed (>30 days)'
        END as time_segment,
        COUNT(*) as user_count
    FROM first_adoption
    WHERE first_feature_adoption IS NOT NULL
    GROUP BY time_segment
)
SELECT 
    time_segment,
    user_count,
    ROUND(100.0 * user_count / (SELECT COUNT(*) FROM segments), 2) as pct
FROM segments
ORDER BY CASE time_segment 
    WHEN 'Immediate (0-1 day)' THEN 1
    WHEN 'Quick (2-7 days)' THEN 2
    WHEN 'Medium (8-30 days)' THEN 3
    WHEN 'Delayed (>30 days)' THEN 4
END;

-- Query 4: Diffusion Curve - Adopter Segments (Rogers Model)
-- ============================================================================
-- Segment users as Innovators, Early Adopters, Early Majority, Late Majority, Laggards

WITH user_percentiles AS (
    SELECT 
        user_id,
        joined_at,
        PERCENT_RANK() OVER (ORDER BY joined_at) * 100 as adoption_percentile
    FROM read_parquet('/home/user/datagen/output_adoption/user.parquet')
),
segments AS (
    SELECT 
        up.user_id,
        up.joined_at,
        CASE 
            WHEN adoption_percentile <= 2.5 THEN 'Innovators'
            WHEN adoption_percentile <= 16 THEN 'Early Adopters'
            WHEN adoption_percentile <= 50 THEN 'Early Majority'
            WHEN adoption_percentile <= 84 THEN 'Late Majority'
            ELSE 'Laggards'
        END as segment
    FROM user_percentiles up
)
SELECT 
    s.segment,
    COUNT(*) as user_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM segments), 2) as pct_of_users,
    ROUND(AVG(EXTRACT(DAY FROM (u.joined_at - (SELECT MIN(joined_at) FROM read_parquet('/home/user/datagen/output_adoption/user.parquet'))))), 0) as avg_days_from_start
FROM segments s
JOIN read_parquet('/home/user/datagen/output_adoption/user.parquet') u ON s.user_id = u.user_id
GROUP BY s.segment
ORDER BY CASE s.segment
    WHEN 'Innovators' THEN 1
    WHEN 'Early Adopters' THEN 2
    WHEN 'Early Majority' THEN 3
    WHEN 'Late Majority' THEN 4
    WHEN 'Laggards' THEN 5
END;

-- Query 5: Feature Adoption by User Segment
-- ============================================================================
-- How many features each adopter segment adopts on average

WITH user_percentiles AS (
    SELECT 
        user_id,
        PERCENT_RANK() OVER (ORDER BY joined_at) * 100 as adoption_percentile
    FROM read_parquet('/home/user/datagen/output_adoption/user.parquet')
),
segments AS (
    SELECT 
        up.user_id,
        CASE 
            WHEN adoption_percentile <= 2.5 THEN 'Innovators'
            WHEN adoption_percentile <= 16 THEN 'Early Adopters'
            WHEN adoption_percentile <= 50 THEN 'Early Majority'
            WHEN adoption_percentile <= 84 THEN 'Late Majority'
            ELSE 'Laggards'
        END as segment
    FROM user_percentiles up
)
SELECT 
    s.segment,
    COUNT(DISTINCT f.user_id) as adopting_users,
    ROUND(AVG(feature_count), 1) as avg_features_per_user,
    ROUND(MAX(feature_count), 0) as max_features,
    ROUND(MIN(feature_count), 0) as min_features
FROM segments s
LEFT JOIN (
    SELECT user_id, COUNT(*) as feature_count
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
    GROUP BY user_id
) f ON s.user_id = f.user_id
GROUP BY s.segment
ORDER BY CASE s.segment
    WHEN 'Innovators' THEN 1
    WHEN 'Early Adopters' THEN 2
    WHEN 'Early Majority' THEN 3
    WHEN 'Late Majority' THEN 4
    WHEN 'Laggards' THEN 5
END;

-- Query 6: Feature Adoption Sequence (First → Second Feature)
-- ============================================================================
-- What feature do users adopt second after their first feature?

WITH user_feature_timeline AS (
    SELECT 
        user_id,
        feature_name,
        adopted_at,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY adopted_at) as adoption_order,
        LAG(feature_name) OVER (PARTITION BY user_id ORDER BY adopted_at) as prev_feature
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
)
SELECT 
    prev_feature,
    feature_name,
    COUNT(*) as sequence_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM user_feature_timeline WHERE adoption_order = 2), 2) as pct_of_second_adoptions
FROM user_feature_timeline
WHERE adoption_order = 2 AND prev_feature IS NOT NULL
GROUP BY prev_feature, feature_name
ORDER BY sequence_count DESC;

-- Query 7: Most Common First Feature Adopted
-- ============================================================================
-- Which feature do most users adopt first?

WITH first_features AS (
    SELECT 
        user_id,
        feature_name,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY adopted_at) as adoption_order
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
)
SELECT 
    feature_name,
    COUNT(*) as first_feature_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM first_features WHERE adoption_order = 1), 2) as pct
FROM first_features
WHERE adoption_order = 1
GROUP BY feature_name
ORDER BY first_feature_count DESC;

-- Query 8: Feature Synergies (Co-Adoption)
-- ============================================================================
-- Which features are adopted together most frequently?

WITH user_feature_pairs AS (
    SELECT 
        f1.user_id,
        f1.feature_name as feature_a,
        f2.feature_name as feature_b
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f1
    JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f2 
        ON f1.user_id = f2.user_id AND f1.feature_name < f2.feature_name
)
SELECT 
    feature_a,
    feature_b,
    COUNT(*) as co_adoption_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT user_id) FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')), 2) as pct_users
FROM user_feature_pairs
GROUP BY feature_a, feature_b
ORDER BY co_adoption_count DESC;

-- Query 9: Feature Penetration Timeline (S-Curve Analysis)
-- ============================================================================
-- How has each feature been adopted over time? (S-curve analysis)

WITH daily_adoption AS (
    SELECT 
        DATE(adopted_at) as adoption_date,
        feature_name,
        COUNT(DISTINCT user_id) as new_adopters
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
    GROUP BY DATE(adopted_at), feature_name
),
daily_stats AS (
    SELECT 
        adoption_date,
        feature_name,
        new_adopters,
        SUM(new_adopters) OVER (PARTITION BY feature_name ORDER BY adoption_date) as cumulative_adopters
    FROM daily_adoption
)
SELECT 
    feature_name,
    MIN(adoption_date) as first_adoption_date,
    MAX(adoption_date) as last_adoption_date,
    COUNT(*) as days_with_adoption,
    MAX(cumulative_adopters) as total_adopters,
    ROUND(AVG(new_adopters), 2) as avg_daily_adoption
FROM daily_stats
GROUP BY feature_name
ORDER BY total_adopters DESC;

-- Query 10: Multi-Feature Adoption Distribution (Activation Velocity)
-- ============================================================================
-- How many features does each user adopt?

WITH user_adoption_stats AS (
    SELECT 
        user_id,
        COUNT(DISTINCT feature_name) as total_features,
        MIN(adopted_at) as first_feature_date,
        MAX(adopted_at) as last_feature_date,
        EXTRACT(DAY FROM (MAX(adopted_at) - MIN(adopted_at))) as days_span
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
    GROUP BY user_id
)
SELECT 
    CASE 
        WHEN total_features = 1 THEN '1 Feature'
        WHEN total_features = 2 THEN '2 Features'
        WHEN total_features = 3 THEN '3 Features'
        WHEN total_features = 4 THEN '4 Features'
        ELSE '5 Features'
    END as feature_count,
    COUNT(*) as user_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM user_adoption_stats), 2) as pct_users,
    ROUND(AVG(days_span), 1) as avg_days_to_multi_feature
FROM user_adoption_stats
GROUP BY total_features
ORDER BY total_features;

-- Query 11: User Value Segmentation (Power Users vs Casual)
-- ============================================================================
-- Segment users by their feature adoption and engagement level

WITH user_value AS (
    SELECT 
        f.user_id,
        COUNT(DISTINCT f.feature_name) as features_adopted,
        COUNT(*) as total_adoptions,
        COUNT(CASE WHEN usage_frequency = 'daily' THEN 1 END) as daily_features,
        COUNT(CASE WHEN usage_frequency = 'weekly' THEN 1 END) as weekly_features,
        COUNT(CASE WHEN usage_frequency = 'monthly' THEN 1 END) as monthly_features,
        COUNT(CASE WHEN usage_frequency = 'rarely' THEN 1 END) as rarely_features
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f
    GROUP BY f.user_id
)
SELECT 
    CASE 
        WHEN features_adopted >= 4 AND daily_features >= 2 THEN 'Power Users (4+ features, 2+ daily)'
        WHEN features_adopted >= 3 AND (daily_features + weekly_features) >= 2 THEN 'Active Users (3+ features, frequent use)'
        WHEN features_adopted >= 2 THEN 'Engaged Users (2+ features)'
        WHEN features_adopted = 1 AND (daily_features + weekly_features) > 0 THEN 'Single-Feature Active'
        ELSE 'Casual Users (1 feature, low frequency)'
    END as user_segment,
    COUNT(*) as user_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM user_value), 2) as pct_users,
    ROUND(AVG(features_adopted), 2) as avg_features,
    ROUND(AVG(total_adoptions), 2) as avg_adoptions
FROM user_value
GROUP BY user_segment
ORDER BY user_count DESC;

-- Query 12: Early Adopter vs Laggard Behavior
-- ============================================================================
-- Compare feature adoption patterns between early adopters and laggards

WITH user_percentiles AS (
    SELECT 
        user_id,
        PERCENT_RANK() OVER (ORDER BY joined_at) * 100 as adoption_percentile
    FROM read_parquet('/home/user/datagen/output_adoption/user.parquet')
),
early_adopters AS (
    SELECT user_id
    FROM user_percentiles
    WHERE adoption_percentile <= 16
),
laggards AS (
    SELECT user_id
    FROM user_percentiles
    WHERE adoption_percentile > 84
),
ea_stats AS (
    SELECT 
        'Early Adopters' as segment,
        COUNT(DISTINCT f.user_id) as active_users,
        COUNT(*) as total_feature_adoptions,
        COUNT(DISTINCT f.feature_name) as unique_features_adopted,
        ROUND(COUNT(*) / COUNT(DISTINCT f.user_id), 2) as avg_adoptions_per_user
    FROM early_adopters ea
    LEFT JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f ON ea.user_id = f.user_id
),
lag_stats AS (
    SELECT 
        'Laggards' as segment,
        COUNT(DISTINCT f.user_id) as active_users,
        COUNT(*) as total_feature_adoptions,
        COUNT(DISTINCT f.feature_name) as unique_features_adopted,
        ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT f.user_id), 0), 2) as avg_adoptions_per_user
    FROM laggards l
    LEFT JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f ON l.user_id = f.user_id
)
SELECT * FROM ea_stats
UNION ALL
SELECT * FROM lag_stats;

-- Query 13: Feature Engagement by Usage Frequency
-- ============================================================================
-- How frequently are features being used?

SELECT 
    feature_name,
    usage_frequency,
    COUNT(*) as adoption_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')), 2) as pct_of_adoptions
FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
GROUP BY feature_name, usage_frequency
ORDER BY feature_name, CASE usage_frequency 
    WHEN 'daily' THEN 1
    WHEN 'weekly' THEN 2
    WHEN 'monthly' THEN 3
    WHEN 'rarely' THEN 4
END;

-- Query 14: Product Activation Gap (Dormant Users)
-- ============================================================================
-- How many users haven't adopted any features?

SELECT 
    COUNT(DISTINCT u.user_id) as users_without_feature_adoption,
    ROUND(100.0 * COUNT(DISTINCT u.user_id) / (SELECT COUNT(*) FROM read_parquet('/home/user/datagen/output_adoption/user.parquet')), 2) as pct_inactive
FROM read_parquet('/home/user/datagen/output_adoption/user.parquet') u
LEFT JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f ON u.user_id = f.user_id
WHERE f.user_id IS NULL;

-- Query 15: Identify Power Users by User ID
-- ============================================================================
-- Get list of actual power users for direct outreach

WITH user_value AS (
    SELECT 
        f.user_id,
        COUNT(DISTINCT f.feature_name) as features_adopted,
        COUNT(CASE WHEN usage_frequency = 'daily' THEN 1 END) as daily_features
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f
    GROUP BY f.user_id
)
SELECT 
    uv.user_id,
    u.email,
    u.joined_at,
    uv.features_adopted,
    uv.daily_features
FROM user_value uv
JOIN read_parquet('/home/user/datagen/output_adoption/user.parquet') u ON uv.user_id = u.user_id
WHERE uv.features_adopted >= 4 AND uv.daily_features >= 2
ORDER BY uv.features_adopted DESC;

-- Query 16: Single-Feature User Segment (At-Risk)
-- ============================================================================
-- Identify users who adopted only 1 feature and their characteristics

WITH user_adoption AS (
    SELECT 
        f.user_id,
        COUNT(DISTINCT f.feature_name) as feature_count,
        ARRAY_AGG(DISTINCT f.feature_name)[1] as first_feature,
        MAX(CASE WHEN f.usage_frequency = 'daily' THEN 1 ELSE 0 END) as has_daily_use
    FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f
    GROUP BY f.user_id
)
SELECT 
    u.user_id,
    u.email,
    ua.first_feature,
    ua.has_daily_use,
    EXTRACT(DAY FROM (NOW() - u.joined_at)) as days_since_signup
FROM user_adoption ua
JOIN read_parquet('/home/user/datagen/output_adoption/user.parquet') u ON ua.user_id = u.user_id
WHERE ua.feature_count = 1
ORDER BY u.joined_at DESC
LIMIT 50;

-- Query 17: Geographic Adoption Patterns (By Country)
-- ============================================================================
-- Analyze adoption patterns by country

WITH user_adoption_stats AS (
    SELECT 
        u.country,
        COUNT(DISTINCT u.user_id) as total_users,
        COUNT(DISTINCT f.user_id) as adopting_users,
        ROUND(AVG(CASE WHEN f.user_id IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as adoption_rate,
        ROUND(AVG(feature_count), 2) as avg_features_per_user
    FROM read_parquet('/home/user/datagen/output_adoption/user.parquet') u
    LEFT JOIN (
        SELECT user_id, COUNT(*) as feature_count
        FROM read_parquet('/home/user/datagen/output_adoption/user_feature.parquet')
        GROUP BY user_id
    ) fc ON u.user_id = fc.user_id
    LEFT JOIN read_parquet('/home/user/datagen/output_adoption/user_feature.parquet') f ON u.user_id = f.user_id
    GROUP BY u.country
)
SELECT *
FROM user_adoption_stats
ORDER BY adoption_rate DESC;

-- ============================================================================
-- END OF QUERIES
-- ============================================================================
