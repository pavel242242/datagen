# Marketing & Growth Analytics - Example Dataset

This folder contains a complete, realistic synthetic dataset for marketing and growth analytics, generated using the Datagen tool.

## 📊 Quick Stats

- **277,043 total rows** across 22 tables
- **9 entity tables** (reference data)
- **13 fact tables** (events and metrics)
- **CSV format** for universal compatibility
- **Deterministic** (seed 42)

## 🗂️ Tables Overview

### Entity Tables (Reference Data)

| File | Rows | Description |
|------|------|-------------|
| `campaigns.csv` | 50 | Marketing campaigns across channels |
| `companies.csv` | 200 | Organizations with industry, size, MRR |
| `people.csv` | 1,000 | Important people (customers, hires, influencers) |
| `content.csv` | 150 | Blog posts, docs, landing pages |
| `products.csv` | 20 | CLI, Platform, MCP, API products |
| `email_templates.csv` | 30 | Email campaign templates |
| `social_accounts.csv` | 8 | Social media platforms |
| `hackathons.csv` | 12 | Hackathon events |
| `survey_templates.csv` | 15 | Survey templates (NPS, feedback) |

### Fact Tables (Events & Metrics)

| File | Rows | Description |
|------|------|-------------|
| `session_events.csv` | 179,725 | User clicks, scrolls, form submissions (Posthog/Hotjar) |
| `seo_daily_metrics.csv` | 49,408 | Daily Ahrefs data per content piece |
| `user_sessions.csv` | 14,964 | Posthog/Hotjar sessions with device, source |
| `newsletter_sends.csv` | 12,074 | Newsletter sends with open/click rates |
| `social_engagement.csv` | 9,787 | Likes, comments, shares on social posts |
| `campaign_mentions.csv` | 3,040 | Important people mentioning campaigns |
| `support_tickets.csv` | 2,938 | Zendesk tickets by priority/category |
| `transactions.csv` | 1,534 | Stripe payments and subscriptions |
| `product_events.csv` | 993 | CLI, API, MCP usage telemetry |
| `social_posts.csv` | 386 | Social media posts across platforms |
| `hackathon_submissions.csv` | 384 | Hackathon project submissions |
| `email_sends.csv` | 251 | Email campaign sends with funnel metrics |
| `survey_responses.csv` | 74 | NPS and satisfaction survey responses |

## 🔍 Sample Queries

### Campaign ROI Analysis
```sql
SELECT
    c.campaign_name,
    c.budget_usd,
    COUNT(t.transaction_id) as conversions,
    SUM(t.amount_usd) as revenue,
    SUM(t.amount_usd) / c.budget_usd as roi
FROM campaigns c
LEFT JOIN transactions t ON t.campaign_id = c.campaign_id
GROUP BY c.campaign_id
ORDER BY roi DESC;
```

### Hackathon Performance
```sql
SELECT
    h.name,
    h.expected_attendees,
    COUNT(hs.submission_id) as submissions,
    ROUND(COUNT(hs.submission_id) * 100.0 / h.expected_attendees, 2) as submission_rate,
    AVG(hs.quality_score) as avg_quality,
    SUM(CASE WHEN hs.used_product THEN 1 ELSE 0 END) as product_adoption
FROM hackathons h
LEFT JOIN hackathon_submissions hs ON hs.hackathon_id = h.hackathon_id
GROUP BY h.hackathon_id;
```

### Content Marketing Performance
```sql
SELECT
    c.title,
    c.content_type,
    AVG(s.organic_traffic) as avg_daily_traffic,
    AVG(s.keyword_rank) as avg_rank,
    SUM(s.backlinks) as total_backlinks
FROM content c
JOIN seo_daily_metrics s ON s.content_id = c.content_id
GROUP BY c.content_id
ORDER BY avg_daily_traffic DESC
LIMIT 10;
```

## 📈 Data Sources Represented

✅ **Ahrefs** - SEO metrics, rankings, backlinks
✅ **Posthog/Hotjar** - User sessions and behavior events
✅ **Email Marketing** - Campaign sends, opens, clicks
✅ **Social Media** - Multi-platform posts and engagement
✅ **Product Telemetry** - CLI, Platform, MCP usage
✅ **Zendesk** - Support tickets and resolution
✅ **Stripe** - Transactions and subscriptions
✅ **Newsletters** - Weekly/monthly sends
✅ **Hackathons** - Submissions and quality scores
✅ **Surveys** - NPS and satisfaction responses

## 🔗 Relationships

All tables are related through foreign keys:

```
campaigns ──┬──> content
            ├──> email_templates
            ├──> hackathons
            ├──> social_posts
            ├──> user_sessions
            ├──> product_events
            ├──> support_tickets
            └──> transactions

people ─────┬──> user_sessions
            ├──> campaign_mentions
            ├──> email_sends
            ├──> newsletter_sends
            ├──> product_events
            ├──> survey_responses
            └──> support_tickets

companies ──┬──> people
            ├──> support_tickets
            └──> transactions

content ────┴──> seo_daily_metrics

social_accounts ──> social_posts ──> social_engagement

hackathons ────> hackathon_submissions

survey_templates ──> survey_responses

user_sessions ──> session_events
```

## 🚀 How to Use

### Load into DuckDB
```sql
-- In DuckDB CLI
.read campaigns.csv
.read people.csv
-- etc...

-- Or import all at once
CREATE TABLE campaigns AS SELECT * FROM read_csv_auto('campaigns.csv');
```

### Load into PostgreSQL
```bash
psql -d mydb -c "COPY campaigns FROM 'campaigns.csv' CSV HEADER;"
```

### Load into Python/Pandas
```python
import pandas as pd

campaigns = pd.read_csv('campaigns.csv')
people = pd.read_csv('people.csv')
sessions = pd.read_csv('user_sessions.csv')
```

## 📝 Metadata

See `metadata.json` for:
- Dataset name and master seed
- Row and column counts per table
- Generation timestamp

## 🔄 Regenerate

To regenerate this exact dataset:

```bash
python -m datagen.cli.commands generate \
    schemas/marketing_growth_analytics.json \
    --seed 42 \
    -o output/marketing_growth
```

Then convert to CSV if needed.

## 📚 Full Documentation

See [MARKETING_ANALYTICS_DATASET.md](../MARKETING_ANALYTICS_DATASET.md) for:
- Complete schema documentation
- Sample SQL queries
- Attribution modeling examples
- Customization guide
