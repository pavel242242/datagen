# Technical Analysis Appendix
## Data Science & Methodological Details

---

## 1. Data Source & Structure

### Tables Analyzed

#### marketing_user (n=1,200)
- **user_id**: Unique user identifier (5000-6199)
- **email**: User email address
- **acquisition_channel**: How user was acquired (5 categories)
- **first_touch_date**: First marketing impression timestamp
- **country**: Geographic location (5 countries)
- **utm_campaign**: Marketing campaign identifier

#### campaign_journey (n=1,855)
- **event_id**: Sequential event identifier
- **user_id**: Reference to user
- **stage_name**: Funnel stage (7 stages)
- **stage_index**: Numeric ordering of stages (0-6)
- **event_timestamp**: When stage occurred
- **device_type**: Mobile/Desktop/Tablet
- **ad_spend_usd**: Advertising cost for that event

#### attribution_event (n=7,857)
- **attribution_id**: Unique attribution record ID
- **user_id**: Reference to user
- **touchpoint_timestamp**: When touchpoint occurred
- **touchpoint_type**: Content type (6 types)
- **revenue_attributed_usd**: Revenue attributed to this touchpoint

### Data Quality Metrics

| Dimension | Status | Evidence |
|-----------|--------|----------|
| **Completeness** | ✅ 100% | 0 null values across all tables |
| **User Coverage** | ✅ 99.9% | 1,199/1,200 users across tables |
| **Temporal Consistency** | ✅ 100% | No events before first_touch_date |
| **Referential Integrity** | ✅ 100% | All user_ids in journey/events exist in marketing_user |
| **Numeric Validity** | ✅ 100% | No negative revenue; realistic ranges |
| **Uniqueness** | ✅ 100% | No duplicate records in any table |

---

## 2. Funnel Analysis Methodology

### Definition of Funnel Stages

The 7-stage funnel was inferred from `campaign_journey.stage_index`:

```
0 → ad_impression       (baseline: all users who saw ads)
1 → ad_click           (engaged with ad)
2 → landing_page_view  (arrived at destination)
3 → signup_started     (initiated account creation)
4 → signup_completed   (finished account creation)
5 → product_activated  (first meaningful product interaction)
6 → first_purchase     (revenue conversion)
```

### Conversion Rate Calculations

**Step-stage conversion:**
```
Conv(i → i+1) = Count[stage i+1] / Count[stage i] × 100%
```

**Top-level conversion:**
```
Conv(i) = Count[stage i] / Count[stage 0] × 100%
```

### Example Calculation
```
Impression → Click:
- Impressions: 1,200 (stage_index=0)
- Clicks: 179 (stage_index=1)
- Conversion: 179/1,200 × 100% = 14.92%
```

### Funnel Integrity Check

Verified that all users with stage_index > N also have stage_index <= N-1 (no skipping stages).

Result: 100% of users follow proper sequence. No orphaned clicks or purchases without preceding stages.

---

## 3. Channel Performance Analysis

### Channel Definitions

From `marketing_user.acquisition_channel`:
- **direct**: User came directly (brand awareness)
- **referral**: User referred by another customer (word-of-mouth)
- **paid_search**: Paid search campaigns (Google Ads, etc.)
- **content_marketing**: Organic traffic from content (blogs, guides)
- **social_media**: Organic/paid social (Facebook, LinkedIn, etc.)

### Conversion Rate by Channel

```
For each channel C:
  users_in_channel = count(user_id where acquisition_channel = C)
  purchasers_in_channel = count(user_id where acquisition_channel = C AND first_purchase = true)
  conv_rate = purchasers_in_channel / users_in_channel × 100%
```

### Revenue Attribution Method

Revenue from `attribution_event` is matched to channels via user_id join:

```
For each channel C:
  channel_users = set of user_id where acquisition_channel = C
  channel_events = rows in attribution_event where user_id ∈ channel_users
  total_revenue = sum(revenue_attributed_usd for channel_events)
  avg_revenue = mean(revenue_attributed_usd for channel_events)
```

### Statistical Significance

Channels with small sample sizes noted:
- Direct (47 users): High variance, statistically less stable
- Content Marketing (235 users): Reasonable sample
- Social Media (446 users): Good statistical power
- Paid Search (295 users): Good sample
- Referral (177 users): Moderate sample

Confidence intervals not calculated but should be considered for sub-50 segments.

---

## 4. Device Analysis

### Device Categorization

From `campaign_journey.device_type`:
- **mobile**: Smartphones (iOS/Android)
- **desktop**: Desktop/laptop computers
- **tablet**: iPad and Android tablets

### Device Performance Metrics

```
For each device D:
  users_on_device = count distinct(user_id where device_type = D)
  purchasers_on_device = count distinct(user_id where device_type = D AND first_purchase = true)

  conversion_rate = purchasers / users × 100%
  cost_per_acquisition = sum(ad_spend_usd) / purchasers_on_device
```

### Key Finding: Tablet Outperformance

Tablet shows 13.9% conversion vs. 8.7% desktop and 7.4% mobile.

Possible explanations:
1. **Self-selection bias**: People researching on tablets may have higher purchase intent (relaxed, dedicated time)
2. **UX advantage**: Larger screen real estate vs. mobile; more natural than desktop
3. **Use case**: People using tablets are often doing recreational research (not at work)
4. **Survivor bias**: Only serious buyers have tablets as secondary device

### Limitations

Tablet is smaller sample (187 users vs. 659 mobile). Confidence interval width is larger.

---

## 5. Channel × Device Cross-Tabulation

### Methodology

```
For each (channel, device) combination:
  subset = rows where acquisition_channel = C AND device_type = D
  users_in_combo = count distinct(user_id in subset)
  purchasers = count distinct(user_id in subset where first_purchase = true)

  conversion = purchasers / users × 100%
  cost_per_acquisition = sum(ad_spend) / purchasers
```

### Data Sparsity

Some combinations have very small sample sizes:
- Direct + Tablet: 5 users (high variance)
- Direct + Mobile: 7 users
- Direct + Desktop: 35 users

These combinations are noted in findings but not heavily weighted for decision-making.

---

## 6. Temporal Analysis

### Monthly Aggregation

```
For each month M in [2024-01 to 2024-12]:
  users_acquired = count distinct(user_id where month(first_touch_date) = M)
  revenue_generated = sum(revenue_attributed_usd where month(touchpoint_timestamp) = M)

  month_revenue_trend = [revenue_M, revenue_M+1, ...]
```

### Seasonality Detection

Trend is monotonically increasing without seasonal drop-offs.

Growth rate: 38x from January ($2,260) to December ($86,076).

### Time-to-Purchase Calculation

```
For each purchaser P:
  first_touch = first_touch_date from marketing_user
  purchase_date = event_timestamp where stage_name = 'first_purchase'

  days_to_purchase = (purchase_date - first_touch).days

  distribution_stats = {
    mean: 5.7 days,
    median: 6.0 days,
    min: 1 day,
    max: 12 days
  }
```

---

## 7. Touchpoint Analysis

### Touchpoint Types

From `attribution_event.touchpoint_type`:
- **display_ad**: Banner/programmatic ads
- **email**: Email campaigns
- **social_post**: Social media posts
- **blog_article**: Long-form content
- **demo_video**: Product demo videos
- **webinar**: Live/recorded webinars

### Revenue Attribution Logic

Attribution event table provides direct revenue attribution for each touchpoint.

Each touchpoint has an associated `revenue_attributed_usd` value that represents value driven by that specific interaction.

### Multi-Touch Attribution Assumption

The analysis assumes that:
1. Each touchpoint independently contributed to revenue
2. No cross-interaction discounting or weight allocation is needed
3. Revenue column accurately reflects attribution model used upstream

**Note:** Without knowing the underlying attribution model, we cannot determine if this is:
- First-touch attribution (credit first interaction)
- Last-touch attribution (credit final interaction)
- Linear attribution (equal credit to all)
- Time-decay attribution (more credit to recent interactions)

---

## 8. Geographic Analysis

### Country Distribution

From `marketing_user.country`:
- **US**: 565 users (47.1%)
- **UK**: 253 users (21.1%)
- **CA**: 156 users (13.0%)
- **AU**: 125 users (10.4%)
- **DE**: 101 users (8.4%)

### Country Performance Metrics

```
For each country Cty:
  users_in_country = count(user_id where country = Cty)
  purchasers_in_country = count(user_id where country = Cty AND first_purchase = true)

  conversion_rate = purchasers / users × 100%
  total_revenue = sum(revenue_attributed_usd where user in country)
```

### Interesting Pattern: Australia

Despite being 8.4% of users, Australia shows 5.6% conversion (highest) and punches above weight in revenue.

Possible factors:
- Product is better-fit for Australian market
- Campaign messaging resonates in APAC
- Self-selection: only serious buyers converting
- Small sample size (125 users) showing statistical noise

---

## 9. Economic Calculations

### Key Metrics

#### Customer Acquisition Cost (CAC)
```
CAC = Total Ad Spend / Total Purchasers
    = $11,843.65 / 50
    = $236.87
```

#### Lifetime Value (LTV)
```
LTV = Total Revenue / Total Purchasers
    = $537,171.03 / 50
    = $10,743.42
```

#### LTV:CAC Ratio
```
LTV:CAC = $10,743.42 / $236.87
        = 45.36:1
```

**Interpretation:** For every $1 spent on acquisition, we get $45.36 in lifetime value. Industry benchmark is typically 3:1, so this is exceptional.

#### Return on Ad Spend (ROAS)
```
ROAS = Revenue / Ad Spend
     = $537,171.03 / $11,843.65
     = 45.36x
```

#### Return on Investment (ROI)
```
ROI = (Revenue - Cost) / Cost × 100%
    = ($537,171.03 - $11,843.65) / $11,843.65 × 100%
    = 4,435.5%
```

### Revenue per $ Spent
```
$537,171.03 / $11,843.65 = $45.36 per dollar spent
```

---

## 10. Limitations & Caveats

### 1. Attribution Model Unknown

The upstream attribution model is not specified. This could be:
- First-touch (channel gets full credit)
- Last-touch (conversion touchpoint gets credit)
- Linear/multi-touch (distributed credit)

Without knowing this, we cannot determine if channels are truly as different as they appear.

### 2. Revenue Per Event vs. Revenue Per User

The analysis uses revenue-per-event, not revenue-per-user. Since users have multiple events:
- A user might generate revenue through multiple touchpoints
- Revenue could be double-counted if attribution is multi-touch
- We can see "total revenue" but not "revenue per converted user"

### 3. Causation vs. Correlation

The analysis shows:
- Direct channel shows 10.6% conversion
- Referral shows 9.0% conversion

But this could be due to:
- Better targeting (direct = users already considering purchase)
- Selection bias (people willing to be referred are serious)
- Product quality (not channel quality)

### 4. Sample Size Constraints

Some subgroups have small sample sizes:
- Direct + Tablet: 5 users (95% CI width could be ±30%)
- Content Marketing + Tablet: ~20 users (95% CI width could be ±15%)

These should not drive major budget allocation decisions alone.

### 5. No Control Group

Without a hold-out control group or incrementality study, we cannot determine:
- What percentage of purchases would have happened without ads?
- Which channels drive incremental (new) vs. accelerated (would happen anyway) conversions?

### 6. Retention Not Measured

The 50 purchasers are first-time buyers. We don't know:
- How many are still customers 3 months later?
- Repeat purchase rate by channel?
- True customer lifetime value (not just first purchase)

### 7. Geographic Representation

5 countries is a reasonable sample but:
- Primarily English-speaking markets (US, UK, CA, AU)
- Only one non-English market (Germany)
- Results may not generalize to other regions

---

## 11. Recommendations for Data Improvement

### 1. Implement Incrementality Testing
```
Design:
- Run hold-out test for 4 weeks
- 20% of audience in control group (no ads)
- 80% in test group (current campaigns)
- Measure: what % would convert without ads?

Benefit: Separate true incremental lift from baseline
```

### 2. Add Cohort Analysis
```
Needed columns:
- cohort_month (when user was acquired)
- repeat_purchase (binary)
- churn_date (when customer stops being active)

Benefit: Understand LTV by cohort and channel; true retention metrics
```

### 3. Attribution Model Transparency
```
Document:
- Current attribution model (first/last/linear/decay)
- Why that model was chosen
- Alternative models considered

Benefit: Understand if high-performing channels are truly better or just positioned well in customer journey
```

### 4. Incremental Revenue per User
```
Add:
- total_revenue_per_user (sum of all attributions)
- attributable_events_per_user (count of touchpoints)

Benefit: Distinguish high-frequency users from high-value users
```

### 5. Expand Geographic Coverage
```
Add markets:
- Japan, India, Brazil (major economies)
- Canada French markets (existing but different language)
- Additional EMEA countries

Benefit: Understand global patterns vs. English-speaking bias
```

---

## 12. Reproducibility

### Data Sources
All analysis uses:
- `/home/user/datagen/output/growth_marketing/marketing_user.parquet`
- `/home/user/datagen/output/growth_marketing/campaign_journey.parquet`
- `/home/user/datagen/output/growth_marketing/attribution_event.parquet`

### Tools Used
- Python 3.9+
- pandas (data manipulation)
- numpy (numerical operations)
- No external APIs or proprietary tools

### Code Availability
Analysis scripts can be found in: `/home/user/datagen/` (marketing analysis scripts)

### Reproducibility
To reproduce findings:
1. Load the three parquet files using pandas
2. Merge on `user_id`
3. Filter campaign_journey to stage_name='first_purchase' for purchaser list
4. Apply groupby operations by channel/device/country
5. Calculate conversion rates as: (purchasers / total_users) × 100%

All calculations are deterministic and reproducible.

---

## 13. Statistical Significance Notes

### Channels with Adequate Sample Size (>200 users)
- Paid Search (295 users): ✅ Strong statistical power
- Social Media (446 users): ✅ Strong statistical power
- Content Marketing (235 users): ✅ Strong statistical power

### Channels with Moderate Sample Size (100-200 users)
- Referral (177 users): ⚠️ Moderate statistical power (use with caution)

### Channels with Small Sample Size (<100 users)
- Direct (47 users): ⚠️ High variance; not recommended for major decisions

### Devices with Adequate Sample Size
- Mobile (659 users): ✅ Strong statistical power
- Desktop (563 users): ✅ Strong statistical power
- Tablet (187 users): ⚠️ Moderate statistical power

### Combined Dimensions (High-Risk Groups)
Any channel × device combination <50 users should be interpreted cautiously.

Example high-risk groups:
- Direct × Tablet: 5 users
- Direct × Mobile: 7 users

---

## Conclusion

The analysis is based on clean, complete data with minimal quality issues. However, several limitations (unknown attribution model, no control group, no retention data) should be considered when making strategic decisions.

The findings are directionally sound and actionable, but should be validated through incremental testing before making large budget shifts.

**Overall Confidence Level: HIGH** for identification of opportunities, **MODERATE** for precise magnitude of opportunity.

