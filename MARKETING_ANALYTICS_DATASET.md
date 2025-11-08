# Marketing & Growth Analytics Synthetic Dataset

## Overview

This is a comprehensive synthetic dataset designed for **marketing and growth tracking** in modern SaaS companies. It covers all major data sources mentioned in your requirements and provides realistic, interconnected data for analytics and testing.

## Data Sources Covered

### ✅ Core Requirements from Your List:

1. **Ahrefs (SEO)**: Daily organic traffic, keyword rankings, backlinks, domain ratings
2. **Posthog/Hotjar**: User sessions with duration, page views, device info, and detailed event tracking (clicks, scrolls, form submissions)
3. **Hackathon Metrics**: Submissions, quality scores, product usage, attendee-to-submission ratios
4. **Campaign Attribution**: "Important people" (hires, customers, influencers) mentioning campaigns with reach estimates
5. **Email Campaign Data**: Template-based sends with open/click/conversion tracking
6. **Social Engagement**: Multi-platform posts (Twitter, LinkedIn, YouTube, etc.) with detailed engagement metrics
7. **Product Metrics**: Telemetry from CLI, Platform, MCP with campaign attribution for growth spikes
8. **User Surveys**: NPS scores, satisfaction ratings, source attribution across all touchpoints
9. **Hotjar**: Captured in user_sessions with heatmap-friendly event tracking
10. **Zendesk**: Support tickets by priority, category, resolution times
11. **Stripe**: Transactions, subscriptions, upgrades, renewals with campaign attribution
12. **Newsletter Data**: Sends, opens, clicks by newsletter type

## Schema Structure

### Entity Tables (Reference Data)

| Table | Rows | Description |
|-------|------|-------------|
| **campaigns** | 50 | Marketing campaigns across channels (SEO, paid, content, events, social) |
| **companies** | 200 | Organizations with industry, size, customer status, MRR |
| **people** | 1,000 | Important people (customers, hires, influencers, partners) |
| **content** | 150 | Blog posts, docs, landing pages, case studies |
| **products** | 20 | CLI, Platform, MCP, API, integrations (free/pro/enterprise tiers) |
| **email_templates** | 30 | Newsletter, announcement, onboarding templates |
| **social_accounts** | 8 | Social media platforms with follower baselines |
| **hackathons** | 12 | Hackathon events with locations and expected attendees |
| **survey_templates** | 15 | NPS, feedback, feature request surveys |

### Fact Tables (Event/Metric Data)

| Table | Rows | Description |
|-------|------|-------------|
| **user_sessions** | 14,964 | Posthog/Hotjar sessions with source, device, campaign attribution |
| **session_events** | 179,725 | Clicks, scrolls, form submissions, video plays within sessions |
| **seo_daily_metrics** | 49,408 | Daily Ahrefs data: traffic, rankings, backlinks per content piece |
| **product_events** | 993 | CLI commands, API calls, MCP requests with success tracking |
| **email_sends** | 251 | Email template sends with open/click/conversion funnel |
| **newsletter_sends** | 12,074 | Weekly/monthly newsletter engagement |
| **social_posts** | 386 | Organic and promoted posts across platforms |
| **social_engagement** | 9,787 | Likes, comments, shares, clicks on social posts |
| **campaign_mentions** | 3,040 | Important people mentioning campaigns (tweets, blogs, talks) |
| **hackathon_submissions** | 384 | Team submissions with quality scores and product usage |
| **survey_responses** | 74 | NPS and satisfaction scores with source attribution |
| **support_tickets** | 2,938 | Zendesk tickets by priority and category |
| **transactions** | 1,534 | Stripe payments, subscriptions, upgrades |

**Total: 277,043 rows across 22 tables**

## Key Features

### 1. Campaign Attribution Throughout
- Every touchpoint (sessions, transactions, tickets, product events) can be attributed to campaigns
- Tracks the full customer journey from awareness to conversion

### 2. Important People Tracking
- Tracks hires, customers, influencers, partners
- Importance levels (high/medium/low) for prioritization
- Sentiment tracking on mentions (positive/neutral/negative)
- Reach estimates for each mention

### 3. Multi-Channel Marketing
- Organic search, paid ads, content, events, email, social, partnerships
- Source attribution: organic, paid, referral, direct, social, email
- Zipf and head-tail distributions for realistic channel performance

### 4. Product-Led Growth Metrics
- CLI, Platform, MCP, API usage events
- Success/failure tracking
- Campaign attribution for growth spikes
- Free/pro/enterprise tier tracking

### 5. Comprehensive Funnel Data
- **Awareness**: SEO metrics, social impressions, campaign mentions
- **Engagement**: Sessions, events, email opens, social engagement
- **Conversion**: Newsletter signups, product events, transactions
- **Retention**: Support tickets, survey responses, repeat transactions

### 6. Hackathon ROI Tracking
- Submissions per hackathon (10-50 range)
- Quality scores (1-10 scale)
- Product usage rate (70%)
- Prize winners (15%)
- Can calculate: good solutions / attendees ratio

### 7. Realistic Data Distributions
- **Zipf**: Popular channels dominate (organic search, Twitter)
- **Head-Tail**: Campaign types (80/20 rule)
- **Lognormal**: Budgets, transaction amounts, traffic
- **Poisson**: Event fanouts (sessions per person, emails per template)

## Usage Examples

### Generate the Dataset

```bash
# Install dependencies (if not already installed)
pip install -e .

# Generate with seed for reproducibility
python -m datagen.cli.commands generate \
    schemas/marketing_growth_analytics.json \
    --seed 42 \
    -o output/marketing_growth
```

### Sample Queries for Analytics

#### 1. **Campaign ROI by Channel**
```sql
SELECT
    c.channel,
    c.campaign_type,
    COUNT(DISTINCT t.transaction_id) as conversions,
    SUM(t.amount_usd) as revenue,
    SUM(c.budget_usd) as spend,
    (SUM(t.amount_usd) / NULLIF(SUM(c.budget_usd), 0)) as roi
FROM campaigns c
LEFT JOIN transactions t ON t.campaign_id = c.campaign_id
GROUP BY c.channel, c.campaign_type
ORDER BY roi DESC;
```

#### 2. **Important People Impact**
```sql
SELECT
    p.name,
    p.importance_level,
    COUNT(cm.mention_id) as mentions,
    AVG(cm.reach_estimate) as avg_reach,
    COUNT(DISTINCT cm.campaign_id) as campaigns_mentioned,
    SUM(CASE WHEN cm.sentiment = 'positive' THEN 1 ELSE 0 END) as positive_mentions
FROM people p
JOIN campaign_mentions cm ON cm.person_id = p.person_id
WHERE p.source_type IN ('influencer', 'hire', 'customer')
GROUP BY p.person_id, p.name, p.importance_level
ORDER BY avg_reach DESC;
```

#### 3. **Hackathon Performance**
```sql
SELECT
    h.name,
    h.location,
    h.expected_attendees,
    COUNT(hs.submission_id) as submissions,
    ROUND(COUNT(hs.submission_id)::float / h.expected_attendees, 3) as submission_rate,
    ROUND(AVG(hs.quality_score), 2) as avg_quality,
    SUM(CASE WHEN hs.used_product THEN 1 ELSE 0 END) as used_product,
    SUM(CASE WHEN hs.prize_won THEN 1 ELSE 0 END) as winners
FROM hackathons h
LEFT JOIN hackathon_submissions hs ON hs.hackathon_id = h.hackathon_id
GROUP BY h.hackathon_id, h.name, h.location, h.expected_attendees
ORDER BY submission_rate DESC;
```

#### 4. **Content Marketing Performance (Ahrefs)**
```sql
SELECT
    c.title,
    c.content_type,
    c.primary_keyword,
    COUNT(DISTINCT sdm.metric_id) as days_tracked,
    ROUND(AVG(sdm.organic_traffic)) as avg_daily_traffic,
    ROUND(AVG(sdm.keyword_rank)) as avg_rank,
    ROUND(AVG(sdm.domain_rating)) as avg_domain_rating,
    SUM(sdm.backlinks) as total_backlinks
FROM content c
JOIN seo_daily_metrics sdm ON sdm.content_id = c.content_id
GROUP BY c.content_id, c.title, c.content_type, c.primary_keyword
ORDER BY avg_daily_traffic DESC;
```

#### 5. **User Behavior Funnel (Posthog/Hotjar)**
```sql
SELECT
    us.source,
    COUNT(DISTINCT us.session_id) as sessions,
    ROUND(AVG(us.duration_seconds)) as avg_session_duration,
    ROUND(AVG(us.page_views)) as avg_page_views,
    COUNT(DISTINCT CASE WHEN se.event_type = 'signup' THEN us.session_id END) as signups,
    COUNT(DISTINCT CASE WHEN se.event_type = 'purchase' THEN us.session_id END) as purchases,
    ROUND(COUNT(DISTINCT CASE WHEN se.event_type = 'signup' THEN us.session_id END)::float /
          NULLIF(COUNT(DISTINCT us.session_id), 0) * 100, 2) as signup_rate,
    ROUND(COUNT(DISTINCT CASE WHEN se.event_type = 'purchase' THEN us.session_id END)::float /
          NULLIF(COUNT(DISTINCT us.session_id), 0) * 100, 2) as purchase_rate
FROM user_sessions us
LEFT JOIN session_events se ON se.session_id = us.session_id
GROUP BY us.source
ORDER BY sessions DESC;
```

#### 6. **Product Telemetry Analysis**
```sql
SELECT
    pr.product_name,
    pr.product_type,
    pr.tier,
    COUNT(pe.event_id) as total_events,
    COUNT(DISTINCT pe.person_id) as unique_users,
    pe.event_type,
    ROUND(AVG(CASE WHEN pe.success THEN 1 ELSE 0 END) * 100, 2) as success_rate,
    COUNT(CASE WHEN pe.campaign_id IS NOT NULL THEN 1 END) as attributed_events
FROM products pr
JOIN product_events pe ON pe.product_id = pr.product_id
GROUP BY pr.product_id, pr.product_name, pr.product_type, pr.tier, pe.event_type
ORDER BY total_events DESC;
```

#### 7. **Survey Insights by Source**
```sql
SELECT
    sr.source_attribution,
    st.survey_type,
    COUNT(sr.response_id) as responses,
    ROUND(AVG(sr.nps_score), 2) as avg_nps,
    ROUND(AVG(sr.satisfaction_score), 2) as avg_satisfaction,
    -- NPS categories
    SUM(CASE WHEN sr.nps_score >= 9 THEN 1 ELSE 0 END) as promoters,
    SUM(CASE WHEN sr.nps_score BETWEEN 7 AND 8 THEN 1 ELSE 0 END) as passives,
    SUM(CASE WHEN sr.nps_score <= 6 THEN 1 ELSE 0 END) as detractors
FROM survey_responses sr
JOIN survey_templates st ON st.survey_id = sr.survey_id
GROUP BY sr.source_attribution, st.survey_type
ORDER BY responses DESC;
```

#### 8. **Support & Product Quality Correlation**
```sql
SELECT
    DATE_TRUNC('month', st.created_at) as month,
    COUNT(st.ticket_id) as tickets,
    st.category,
    st.priority,
    ROUND(AVG(EXTRACT(EPOCH FROM (st.resolved_at - st.created_at)) / 3600), 2) as avg_resolution_hours,
    -- Correlate with product events
    COUNT(DISTINCT pe.person_id) as active_users_in_month
FROM support_tickets st
LEFT JOIN product_events pe ON pe.person_id = st.person_id
    AND DATE_TRUNC('month', pe.timestamp) = DATE_TRUNC('month', st.created_at)
GROUP BY month, st.category, st.priority
ORDER BY month DESC, tickets DESC;
```

## Data Quality & Realism

### Deterministic Generation
- Same seed (42) always produces identical dataset
- Reproducible for testing and validation

### Realistic Distributions
- **Zipf Law**: Popular items dominate (80/20 rule)
- **Log-normal**: Revenue, budgets, traffic follow natural distributions
- **Head-Tail**: Hybrid distribution for campaign types
- **Poisson**: Random event counts with realistic variance

### Referential Integrity
- All foreign keys guaranteed valid
- Hierarchical generation (entities → facts → nested facts)
- No orphaned records

### Temporal Consistency
- Year-long timeframe (2024-01-01 to 2025-01-01)
- Appropriate granularity: hourly sessions, daily SEO, weekly newsletters
- Future-proof datetime handling

## Files Generated

```
output/marketing_growth/
├── campaigns.parquet            # 50 rows, 7 columns
├── companies.parquet            # 200 rows, 8 columns
├── people.parquet               # 1,000 rows, 8 columns
├── content.parquet              # 150 rows, 6 columns
├── products.parquet             # 20 rows, 5 columns
├── email_templates.parquet      # 30 rows, 4 columns
├── social_accounts.parquet      # 8 rows, 4 columns
├── hackathons.parquet           # 12 rows, 6 columns
├── survey_templates.parquet     # 15 rows, 4 columns
├── user_sessions.parquet        # 14,964 rows, 9 columns
├── session_events.parquet       # 179,725 rows, 6 columns
├── seo_daily_metrics.parquet    # 49,408 rows, 8 columns
├── product_events.parquet       # 993 rows, 7 columns
├── email_sends.parquet          # 251 rows, 7 columns
├── newsletter_sends.parquet     # 12,074 rows, 6 columns
├── social_posts.parquet         # 386 rows, 6 columns
├── social_engagement.parquet    # 9,787 rows, 5 columns
├── campaign_mentions.parquet    # 3,040 rows, 7 columns
├── hackathon_submissions.parquet # 384 rows, 7 columns
├── survey_responses.parquet     # 74 rows, 7 columns
├── support_tickets.parquet      # 2,938 rows, 8 columns
├── transactions.parquet         # 1,534 rows, 9 columns
└── .metadata.json               # Dataset metadata
```

## Next Steps

1. **Load into Analytics Platform**: Import Parquet files into DuckDB, PostgreSQL, ClickHouse, or BigQuery
2. **Build Dashboards**: Connect to Metabase, Tableau, or Looker for visualization
3. **Test Attribution Models**: Multi-touch attribution with campaign_id across all touchpoints
4. **Run ML Models**: Churn prediction, LTV forecasting, propensity scoring
5. **Validate Queries**: Test marketing analytics queries against realistic data

## Customization

To adjust the schema:

1. Edit `schemas/marketing_growth_analytics.json`
2. Modify:
   - **Row counts**: Change `rows` field in entity nodes
   - **Fanout rates**: Adjust `lambda` in fact nodes
   - **Distributions**: Update `weights_kind` and `weights` in generators
   - **Date ranges**: Modify `timeframe` section
3. Regenerate: `python -m datagen.cli.commands generate schemas/marketing_growth_analytics.json --seed 42 -o output/marketing_growth`

## Summary

This dataset provides **everything you need** to build comprehensive marketing and growth analytics:

✅ **All data sources you mentioned** (Ahrefs, Posthog, Hotjar, Zendesk, Stripe, product telemetry, newsletters)
✅ **Realistic and deterministic** (reproducible with seed 42)
✅ **Fully relational** (proper foreign keys and joins)
✅ **Campaign attribution** (track ROI across all touchpoints)
✅ **277K+ rows** across 22 tables
✅ **Ready to query** (Parquet format, optimized for analytics)

Perfect for testing analytics dashboards, validating attribution models, and demonstrating marketing data pipelines!
