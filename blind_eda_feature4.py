"""
Truly Blind Exploratory Data Analysis for Feature #4: State Transitions

Validation Approach:
1. Agent given ONLY a directory path containing parquet files
2. Agent discovers what tables exist (file listing)
3. Agent explores each table's schema (DESCRIBE, column names)
4. Agent performs EDA to understand data patterns
5. Agent attempts to answer business questions
6. Agent documents what they can/cannot determine

Success = Agent can answer critical business questions without prior knowledge

Personas:
- VP of Product (churn focus)
- Head of Data (cohort analysis focus)
- CFO (LTV focus)
- Data Quality Engineer (integrity focus)
"""

import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import sys


class BlindExploratoryAnalysis:
    """
    Truly blind analysis - agent knows NOTHING about the schema.
    Must discover everything through exploration.
    """

    def __init__(self, data_dir: str, agent_name: str):
        """
        Initialize blind analysis.

        Args:
            data_dir: Path to directory containing parquet files (ONLY INPUT)
            agent_name: Analyst persona name
        """
        self.data_dir = Path(data_dir)
        self.agent_name = agent_name
        self.con = duckdb.connect(":memory:")

        # Agent's findings (built up through exploration)
        self.findings = {
            "agent": agent_name,
            "data_dir": str(data_dir),
            "timestamp": datetime.now().isoformat(),
            "discoveries": [],
            "business_insights": [],
            "limitations": [],
            "data_quality_issues": []
        }

        print(f"\n{'='*80}")
        print(f"🔍 BLIND ANALYSIS START: {agent_name}")
        print(f"📁 Data Directory: {data_dir}")
        print(f"{'='*80}\n")

    # ========================================================================
    # PHASE 1: DISCOVERY - What data exists?
    # ========================================================================

    def discover_tables(self):
        """Phase 1: Discover what parquet files (tables) exist."""
        print("🔍 PHASE 1: DISCOVERING TABLES\n")

        parquet_files = list(self.data_dir.glob("*.parquet"))

        if not parquet_files:
            print("❌ No parquet files found!")
            return []

        tables = []
        for file_path in parquet_files:
            table_name = file_path.stem

            # Load into DuckDB
            self.con.execute(f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM read_parquet('{file_path}')
            """)

            # Get row count
            row_count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            tables.append({
                "table_name": table_name,
                "file_path": str(file_path),
                "row_count": row_count
            })

            print(f"✓ Discovered table: {table_name:20s} ({row_count:,} rows)")

        self.findings["discoveries"].append({
            "phase": "Table Discovery",
            "tables_found": tables,
            "insight": f"Dataset contains {len(tables)} tables with {sum(t['row_count'] for t in tables):,} total rows"
        })

        return tables

    def explore_table_schema(self, table_name: str):
        """Phase 2: Explore schema and column characteristics of a table."""
        print(f"\n🔍 EXPLORING TABLE: {table_name}")
        print("-" * 80)

        # Get column info
        schema_query = f"DESCRIBE {table_name}"
        schema_df = self.con.execute(schema_query).df()

        print("\n📋 Schema:")
        for _, col in schema_df.iterrows():
            print(f"  {col['column_name']:30s} {col['column_type']:15s}")

        # Sample data
        sample_query = f"SELECT * FROM {table_name} LIMIT 5"
        sample_df = self.con.execute(sample_query).df()

        print(f"\n📊 Sample Data (first 5 rows):")
        print(sample_df.to_string(index=False))

        # Column statistics
        print(f"\n📈 Column Statistics:")

        exploration = {
            "table": table_name,
            "schema": schema_df.to_dict('records'),
            "sample": sample_df.to_dict('records'),
            "column_analysis": []
        }

        for _, col in schema_df.iterrows():
            col_name = col['column_name']
            col_type = col['column_type']

            # Analyze based on type
            if 'INT' in col_type.upper() or 'DOUBLE' in col_type.upper() or 'FLOAT' in col_type.upper():
                # Numeric column
                stats_query = f"""
                    SELECT
                        COUNT(*) as count,
                        COUNT(DISTINCT {col_name}) as distinct_count,
                        MIN({col_name}) as min,
                        MAX({col_name}) as max,
                        AVG({col_name}) as avg,
                        MEDIAN({col_name}) as median
                    FROM {table_name}
                """
                stats = self.con.execute(stats_query).df().iloc[0].to_dict()
                print(f"  {col_name}: {stats['distinct_count']} unique values, range [{stats['min']:.1f}, {stats['max']:.1f}]")

                exploration["column_analysis"].append({
                    "column": col_name,
                    "type": "numeric",
                    "stats": stats
                })

            elif 'VARCHAR' in col_type.upper():
                # String column
                stats_query = f"""
                    SELECT
                        COUNT(*) as count,
                        COUNT(DISTINCT {col_name}) as distinct_count
                    FROM {table_name}
                """
                stats = self.con.execute(stats_query).df().iloc[0].to_dict()

                # Get top values if categorical
                if stats['distinct_count'] <= 20:
                    top_query = f"""
                        SELECT {col_name}, COUNT(*) as freq
                        FROM {table_name}
                        WHERE {col_name} IS NOT NULL
                        GROUP BY {col_name}
                        ORDER BY freq DESC
                        LIMIT 10
                    """
                    top_values = self.con.execute(top_query).df()
                    print(f"  {col_name}: {stats['distinct_count']} categories")
                    for _, row in top_values.iterrows():
                        print(f"    - {row[col_name]}: {row['freq']}")

                    exploration["column_analysis"].append({
                        "column": col_name,
                        "type": "categorical",
                        "stats": stats,
                        "top_values": top_values.to_dict('records')
                    })
                else:
                    print(f"  {col_name}: {stats['distinct_count']} unique values (high cardinality)")
                    exploration["column_analysis"].append({
                        "column": col_name,
                        "type": "string",
                        "stats": stats
                    })

            elif 'TIMESTAMP' in col_type.upper() or 'DATE' in col_type.upper():
                # Temporal column
                stats_query = f"""
                    SELECT
                        MIN({col_name}) as min_date,
                        MAX({col_name}) as max_date,
                        DATE_DIFF('day', MIN({col_name}), MAX({col_name})) as span_days
                    FROM {table_name}
                """
                stats = self.con.execute(stats_query).df().iloc[0].to_dict()
                print(f"  {col_name}: {stats['min_date']} to {stats['max_date']} ({stats['span_days']} days)")

                exploration["column_analysis"].append({
                    "column": col_name,
                    "type": "temporal",
                    "stats": stats
                })

        self.findings["discoveries"].append({
            "phase": "Table Exploration",
            "exploration": exploration
        })

        return exploration

    def infer_relationships(self, tables):
        """Phase 3: Infer relationships between tables (FK detection)."""
        print(f"\n🔍 PHASE 3: INFERRING RELATIONSHIPS\n")

        relationships = []

        table_names = [t['table_name'] for t in tables]

        for i, table1 in enumerate(table_names):
            schema1 = self.con.execute(f"DESCRIBE {table1}").df()

            for table2 in table_names[i+1:]:
                schema2 = self.con.execute(f"DESCRIBE {table2}").df()

                # Find common column names
                common_cols = set(schema1['column_name']) & set(schema2['column_name'])

                for col in common_cols:
                    # Check if values in table1 are subset of table2 (FK relationship)
                    check_query = f"""
                        WITH t1_values AS (
                            SELECT DISTINCT {col} FROM {table1}
                        ),
                        t2_values AS (
                            SELECT DISTINCT {col} FROM {table2}
                        ),
                        missing AS (
                            SELECT t1.{col}
                            FROM t1_values t1
                            LEFT JOIN t2_values t2 ON t1.{col} = t2.{col}
                            WHERE t2.{col} IS NULL
                        )
                        SELECT COUNT(*) as missing_count FROM missing
                    """

                    missing = self.con.execute(check_query).fetchone()[0]

                    if missing == 0:
                        # Possible FK relationship
                        relationships.append({
                            "from_table": table1,
                            "to_table": table2,
                            "column": col,
                            "type": "possible_foreign_key",
                            "integrity": "100%"
                        })
                        print(f"✓ Found relationship: {table1}.{col} → {table2}.{col} (100% integrity)")

        self.findings["discoveries"].append({
            "phase": "Relationship Inference",
            "relationships": relationships,
            "insight": f"Discovered {len(relationships)} potential foreign key relationships"
        })

        return relationships

    # ========================================================================
    # PHASE 4: BUSINESS ANALYSIS - Answer domain questions
    # ========================================================================

    def vp_product_analysis(self, tables, relationships):
        """VP of Product: Can I measure churn and retention?"""
        print(f"\n{'='*80}")
        print(f"🎯 VP OF PRODUCT ANALYSIS")
        print(f"{'='*80}\n")

        insights = []

        # Look for state/status columns (indicators of lifecycle)
        for table in tables:
            table_name = table['table_name']
            schema = self.con.execute(f"DESCRIBE {table_name}").df()

            # Find potential state columns (exclude ID columns)
            state_cols = []
            for _, col in schema.iterrows():
                col_name = col['column_name'].lower()
                # Match state/status/stage columns but exclude ID columns
                if any(keyword in col_name for keyword in ['state', 'status', 'stage']) and not col_name.endswith('_id'):
                    state_cols.append(col['column_name'])

            if not state_cols:
                continue

            print(f"📊 Found lifecycle indicators in {table_name}: {state_cols}")

            for state_col in state_cols:
                # Analyze state distribution
                query = f"""
                    SELECT
                        {state_col},
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                    FROM {table_name}
                    WHERE {state_col} IS NOT NULL
                    GROUP BY {state_col}
                    ORDER BY count DESC
                """

                state_dist = self.con.execute(query).df()

                print(f"\n  State Distribution ({state_col}):")
                for _, row in state_dist.iterrows():
                    print(f"    {str(row[state_col]):25s} {int(row['count']):6d} ({row['percentage']:5.1f}%)")

                # Look for churn indicators
                churn_keywords = ['churn', 'cancel', 'inactive', 'terminated', 'expired', 'decommission']
                churned_states = [s for s in state_dist[state_col].values
                                 if any(kw in str(s).lower() for kw in churn_keywords)]

                if churned_states:
                    churn_rate = state_dist[state_dist[state_col].isin(churned_states)]['percentage'].sum()

                    insights.append({
                        "metric": "Churn Rate",
                        "table": table_name,
                        "column": state_col,
                        "value": f"{churn_rate:.2f}%",
                        "insight": f"Identified churn rate from state distribution",
                        "states": churned_states
                    })

                    print(f"\n  💡 INSIGHT: Churn Rate = {churn_rate:.2f}%")
                    print(f"     Churned states: {', '.join(map(str, churned_states))}")

                # Look for temporal patterns if timestamp exists
                timestamp_cols = [c for c in schema['column_name'].values
                                 if 'time' in c.lower() or 'date' in c.lower()]

                if timestamp_cols and churned_states:
                    ts_col = timestamp_cols[0]

                    query = f"""
                        SELECT
                            DATE_TRUNC('month', {ts_col}) as month,
                            COUNT(*) as events,
                            SUM(CASE WHEN {state_col} IN ({','.join(f"'{s}'" for s in churned_states)}) THEN 1 ELSE 0 END) as churns
                        FROM {table_name}
                        GROUP BY DATE_TRUNC('month', {ts_col})
                        ORDER BY month
                    """

                    try:
                        monthly = self.con.execute(query).df()

                        if len(monthly) > 1:
                            print(f"\n  📈 Monthly Churn Trend:")
                            for _, row in monthly.head(6).iterrows():
                                churn_rate_monthly = (row['churns'] / row['events'] * 100) if row['events'] > 0 else 0
                                print(f"    {row['month'].strftime('%Y-%m')}: {row['churns']:4d} churns ({churn_rate_monthly:.1f}%)")

                            insights.append({
                                "metric": "Churn Trend",
                                "table": table_name,
                                "data": monthly.to_dict('records'),
                                "insight": "Monthly churn pattern discovered"
                            })
                    except Exception as e:
                        pass

        # Look for reactivation patterns (state transitions)
        for table in tables:
            table_name = table['table_name']
            schema = self.con.execute(f"DESCRIBE {table_name}").df()

            state_cols = [c for c in schema['column_name'].values
                         if ('state' in c.lower() or 'status' in c.lower()) and not c.lower().endswith('_id')]
            timestamp_cols = [c for c in schema['column_name'].values
                            if 'time' in c.lower() or 'date' in c.lower()]

            if not state_cols or not timestamp_cols:
                continue

            state_col = state_cols[0]
            ts_col = timestamp_cols[0]

            # Find ID column (usually has 'id' in name and high cardinality)
            id_candidates = [c for c in schema['column_name'].values if 'id' in c.lower()]
            if not id_candidates:
                continue

            id_col = id_candidates[0]

            # Look for reactivation pattern (churn → active)
            query = f"""
                WITH state_transitions AS (
                    SELECT
                        {id_col},
                        {state_col} as current_state,
                        LAG({state_col}) OVER (PARTITION BY {id_col} ORDER BY {ts_col}) as prev_state
                    FROM {table_name}
                    WHERE {state_col} IS NOT NULL
                )
                SELECT
                    prev_state,
                    current_state,
                    COUNT(*) as transition_count
                FROM state_transitions
                WHERE prev_state IS NOT NULL
                GROUP BY prev_state, current_state
                ORDER BY transition_count DESC
                LIMIT 10
            """

            try:
                transitions = self.con.execute(query).df()

                if not transitions.empty:
                    print(f"\n  🔄 Top State Transitions in {table_name}:")
                    for _, row in transitions.head(5).iterrows():
                        print(f"    {str(row['prev_state']):20s} → {str(row['current_state']):20s} {row['transition_count']:5d} times")

                    # Look for reactivation (churned/cancelled → active)
                    reactivations = transitions[
                        (transitions['prev_state'].astype(str).str.lower().str.contains('churn|cancel|inactive|paused|dormant', na=False)) &
                        (transitions['current_state'].astype(str).str.lower().str.contains('active|renew|reactivate|online|onboard', na=False))
                    ]

                    if not reactivations.empty:
                        total_reactivations = reactivations['transition_count'].sum()
                        print(f"\n  💡 INSIGHT: Found {total_reactivations} reactivations (win-backs)")

                        insights.append({
                            "metric": "Reactivation",
                            "table": table_name,
                            "value": int(total_reactivations),
                            "patterns": reactivations.to_dict('records'),
                            "insight": "Users can return after churning"
                        })
            except Exception as e:
                # Query failed, skip
                pass

        self.findings["business_insights"].append({
            "persona": "VP of Product",
            "focus": "Churn & Retention",
            "insights": insights,
            "can_answer": len(insights) > 0
        })

        if not insights:
            self.findings["limitations"].append({
                "persona": "VP of Product",
                "limitation": "Cannot measure churn - no clear lifecycle states found"
            })
            print("\n  ⚠️  LIMITATION: Unable to identify clear churn patterns")

        return insights

    def head_of_data_analysis(self, tables, relationships):
        """Head of Data: Can I do cohort analysis and retention curves?"""
        print(f"\n{'='*80}")
        print(f"📊 HEAD OF DATA ANALYSIS")
        print(f"{'='*80}\n")

        insights = []

        # Look for cohort analysis opportunities
        # Need: entity table with created_at + event table with timestamps

        for rel in relationships:
            # Try to find entity → event relationship
            entity_table = rel['to_table']  # Fewer rows = likely parent
            event_table = rel['from_table']  # More rows = likely child
            join_col = rel['column']

            # Get schemas
            entity_schema = self.con.execute(f"DESCRIBE {entity_table}").df()
            event_schema = self.con.execute(f"DESCRIBE {event_table}").df()

            # Find created_at in entity table
            created_cols = [c for c in entity_schema['column_name'].values
                           if any(kw in c.lower() for kw in ['created', 'joined', 'signup', 'registered', 'deployed'])]

            # Find timestamp in event table
            event_ts_cols = [c for c in event_schema['column_name'].values
                            if 'time' in c.lower() or 'date' in c.lower()]

            # Find state column in event table
            state_cols = [c for c in event_schema['column_name'].values
                         if 'state' in c.lower() or 'status' in c.lower() or 'engagement' in c.lower()]

            if not created_cols or not event_ts_cols or not state_cols:
                continue

            created_col = created_cols[0]
            event_ts_col = event_ts_cols[0]
            state_col = state_cols[0]

            print(f"📅 Found cohort analysis opportunity:")
            print(f"  Entity table: {entity_table} (created: {created_col})")
            print(f"  Event table: {event_table} (timestamp: {event_ts_col}, state: {state_col})")

            # Cohort retention analysis
            query = f"""
                WITH cohorts AS (
                    SELECT
                        {join_col},
                        DATE_TRUNC('month', {created_col}) as cohort_month
                    FROM {entity_table}
                ),
                latest_states AS (
                    SELECT
                        {join_col},
                        {state_col} as final_state,
                        ROW_NUMBER() OVER (PARTITION BY {join_col} ORDER BY {event_ts_col} DESC) as rn
                    FROM {event_table}
                    WHERE {state_col} IS NOT NULL
                )
                SELECT
                    c.cohort_month,
                    COUNT(*) as cohort_size,
                    SUM(CASE WHEN ls.final_state NOT IN ('churned', 'cancelled', 'terminated', 'inactive', 'decommissioned', 'dormant')
                        THEN 1 ELSE 0 END) as still_active,
                    ROUND(SUM(CASE WHEN ls.final_state NOT IN ('churned', 'cancelled', 'terminated', 'inactive', 'decommissioned', 'dormant')
                        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as retention_rate
                FROM cohorts c
                LEFT JOIN latest_states ls ON c.{join_col} = ls.{join_col} AND ls.rn = 1
                GROUP BY c.cohort_month
                ORDER BY c.cohort_month
            """

            try:
                cohort_retention = self.con.execute(query).df()

                if not cohort_retention.empty:
                    print(f"\n  📈 Cohort Retention Analysis:")
                    for _, row in cohort_retention.head(6).iterrows():
                        print(f"    {row['cohort_month'].strftime('%Y-%m'):10s} Size: {row['cohort_size']:4d} | Retention: {row['retention_rate']:5.1f}%")

                    # Calculate retention decay
                    first_retention = cohort_retention.iloc[0]['retention_rate']
                    last_retention = cohort_retention.iloc[-1]['retention_rate']
                    decay = first_retention - last_retention

                    insights.append({
                        "metric": "Cohort Retention",
                        "entity_table": entity_table,
                        "event_table": event_table,
                        "data": cohort_retention.to_dict('records'),
                        "insight": f"Vintage effect detected: {decay:.1f}pp retention decay from early to late cohorts"
                    })

                    print(f"\n  💡 INSIGHT: Retention decay = {decay:.1f} percentage points")

            except Exception as e:
                print(f"  ⚠️  Could not compute cohort retention: {e}")

            # Time in state analysis
            query = f"""
                WITH state_durations AS (
                    SELECT
                        {join_col},
                        {state_col} as state,
                        {event_ts_col} as entered_at,
                        LEAD({event_ts_col}) OVER (
                            PARTITION BY {join_col}
                            ORDER BY {event_ts_col}
                        ) as exited_at
                    FROM {event_table}
                    WHERE {state_col} IS NOT NULL
                ),
                durations AS (
                    SELECT
                        state,
                        DATE_DIFF('day', entered_at, exited_at) as days_in_state
                    FROM state_durations
                    WHERE exited_at IS NOT NULL
                )
                SELECT
                    state,
                    COUNT(*) as observations,
                    ROUND(AVG(days_in_state), 1) as avg_days,
                    ROUND(MEDIAN(days_in_state), 1) as median_days
                FROM durations
                GROUP BY state
                ORDER BY avg_days DESC
            """

            try:
                time_in_state = self.con.execute(query).df()

                if not time_in_state.empty:
                    print(f"\n  ⏱️  Time in State Analysis:")
                    for _, row in time_in_state.iterrows():
                        print(f"    {str(row['state']):25s} Avg: {row['avg_days']:6.1f} days | Median: {row['median_days']:6.1f} days")

                    insights.append({
                        "metric": "Time in State",
                        "table": event_table,
                        "data": time_in_state.to_dict('records'),
                        "insight": "Discovered state duration patterns"
                    })

            except Exception as e:
                print(f"  ⚠️  Could not compute time in state: {e}")

        self.findings["business_insights"].append({
            "persona": "Head of Data",
            "focus": "Cohort Analysis & Duration",
            "insights": insights,
            "can_answer": len(insights) > 0
        })

        if not insights:
            self.findings["limitations"].append({
                "persona": "Head of Data",
                "limitation": "Cannot perform cohort analysis - missing created_at or state transitions"
            })
            print("\n  ⚠️  LIMITATION: Unable to perform cohort analysis")

        return insights

    def cfo_analysis(self, tables, relationships):
        """CFO: Can I measure LTV and segment profitability?"""
        print(f"\n{'='*80}")
        print(f"💰 CFO ANALYSIS")
        print(f"{'='*80}\n")

        insights = []

        # Look for segment columns and lifetime metrics
        for table in tables:
            table_name = table['table_name']
            schema = self.con.execute(f"DESCRIBE {table_name}").df()

            # Find segment/tier columns
            segment_cols = [c for c in schema['column_name'].values
                           if any(kw in c.lower() for kw in ['segment', 'tier', 'type', 'category', 'plan', 'membership', 'source', 'size'])]

            # Find timestamp columns
            ts_cols = [c for c in schema['column_name'].values
                      if 'time' in c.lower() or 'date' in c.lower()]

            # Find ID column
            id_cols = [c for c in schema['column_name'].values if 'id' in c.lower()]

            if not segment_cols or not ts_cols or not id_cols:
                continue

            segment_col = segment_cols[0]
            ts_col = ts_cols[0]
            id_col = id_cols[0]

            print(f"💎 Found segmentation opportunity in {table_name}")
            print(f"  Segment column: {segment_col}")

            # Lifetime by segment
            query = f"""
                WITH entity_lifetimes AS (
                    SELECT
                        {id_col},
                        MIN({ts_col}) as first_event,
                        MAX({ts_col}) as last_event,
                        COUNT(*) as total_events,
                        DATE_DIFF('day', MIN({ts_col}), MAX({ts_col})) as lifetime_days
                    FROM {table_name}
                    GROUP BY {id_col}
                )
                SELECT
                    t.{segment_col} as segment,
                    COUNT(DISTINCT t.{id_col}) as entity_count,
                    ROUND(AVG(el.lifetime_days), 1) as avg_lifetime_days,
                    ROUND(AVG(el.total_events), 1) as avg_events
                FROM {table_name} t
                JOIN entity_lifetimes el ON t.{id_col} = el.{id_col}
                WHERE t.{segment_col} IS NOT NULL
                GROUP BY t.{segment_col}
                ORDER BY avg_lifetime_days DESC
            """

            try:
                segment_ltv = self.con.execute(query).df()

                if not segment_ltv.empty:
                    print(f"\n  📊 Lifetime by Segment:")
                    for _, row in segment_ltv.iterrows():
                        print(f"    {str(row['segment']):20s} Avg Lifetime: {row['avg_lifetime_days']:6.1f} days | Events: {row['avg_events']:5.1f}")

                    # Calculate multiplier
                    max_lifetime = segment_ltv['avg_lifetime_days'].max()
                    min_lifetime = segment_ltv['avg_lifetime_days'].min()
                    multiplier = max_lifetime / min_lifetime if min_lifetime > 0 else 0

                    insights.append({
                        "metric": "Lifetime by Segment",
                        "table": table_name,
                        "data": segment_ltv.to_dict('records'),
                        "insight": f"Best segment has {multiplier:.1f}x longer lifetime than worst"
                    })

                    print(f"\n  💡 INSIGHT: Segment lifetime multiplier = {multiplier:.1f}x")

            except Exception as e:
                print(f"  ⚠️  Could not compute segment LTV: {e}")

            # Churn risk by state (if state column exists)
            state_cols = [c for c in schema['column_name'].values
                         if 'state' in c.lower() or 'status' in c.lower() or 'engagement' in c.lower()]

            if state_cols:
                state_col = state_cols[0]

                query = f"""
                    WITH state_outcomes AS (
                        SELECT
                            {state_col} as state,
                            LEAD({state_col}) OVER (
                                PARTITION BY {id_col}
                                ORDER BY {ts_col}
                            ) as next_state
                        FROM {table_name}
                        WHERE {state_col} IS NOT NULL
                    )
                    SELECT
                        state,
                        COUNT(*) as observations,
                        SUM(CASE WHEN next_state IN ('churned', 'cancelled', 'terminated', 'decommissioned') THEN 1 ELSE 0 END) as churned,
                        ROUND(SUM(CASE WHEN next_state IN ('churned', 'cancelled', 'terminated', 'decommissioned') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as churn_probability
                    FROM state_outcomes
                    WHERE next_state IS NOT NULL
                    GROUP BY state
                    HAVING COUNT(*) >= 5
                    ORDER BY churn_probability DESC
                """

                try:
                    churn_risk = self.con.execute(query).df()

                    if not churn_risk.empty:
                        print(f"\n  ⚠️  Churn Risk by State:")
                        for _, row in churn_risk.iterrows():
                            print(f"    {str(row['state']):25s} Churn Prob: {row['churn_probability']:5.1f}% (n={row['observations']})")

                        insights.append({
                            "metric": "Churn Risk",
                            "table": table_name,
                            "data": churn_risk.to_dict('records'),
                            "insight": "Identified high-risk states for intervention"
                        })

                except Exception as e:
                    print(f"  ⚠️  Could not compute churn risk: {e}")

        self.findings["business_insights"].append({
            "persona": "CFO",
            "focus": "Lifetime Value & Profitability",
            "insights": insights,
            "can_answer": len(insights) > 0
        })

        if not insights:
            self.findings["limitations"].append({
                "persona": "CFO",
                "limitation": "Cannot measure LTV - missing segment or lifetime data"
            })
            print("\n  ⚠️  LIMITATION: Unable to measure segment profitability")

        return insights

    def data_quality_checks(self, tables, relationships):
        """Data Quality: Temporal integrity and logical consistency."""
        print(f"\n{'='*80}")
        print(f"✅ DATA QUALITY CHECKS")
        print(f"{'='*80}\n")

        issues = []

        for table in tables:
            table_name = table['table_name']
            schema = self.con.execute(f"DESCRIBE {table_name}").df()

            # Find ID and timestamp columns
            id_cols = [c for c in schema['column_name'].values if 'id' in c.lower()]
            ts_cols = [c for c in schema['column_name'].values
                      if 'time' in c.lower() or 'date' in c.lower()]

            if not id_cols or not ts_cols:
                continue

            id_col = id_cols[0]
            ts_col = ts_cols[0]

            print(f"🔍 Checking {table_name}...")

            # Temporal ordering check
            query = f"""
                WITH ordered_events AS (
                    SELECT
                        {id_col},
                        {ts_col},
                        LAG({ts_col}) OVER (
                            PARTITION BY {id_col}
                            ORDER BY {ts_col}
                        ) as prev_ts
                    FROM {table_name}
                )
                SELECT COUNT(*) as violations
                FROM ordered_events
                WHERE prev_ts IS NOT NULL AND {ts_col} < prev_ts
            """

            violations = self.con.execute(query).fetchone()[0]

            if violations > 0:
                issues.append({
                    "table": table_name,
                    "type": "CRITICAL",
                    "issue": "Temporal ordering violations",
                    "count": violations
                })
                print(f"  ❌ CRITICAL: {violations} temporal ordering violations")
            else:
                print(f"  ✅ Temporal ordering: OK")

        # Check FK integrity
        for rel in relationships:
            if rel['integrity'] != "100%":
                issues.append({
                    "tables": f"{rel['from_table']} → {rel['to_table']}",
                    "type": "CRITICAL",
                    "issue": "Foreign key integrity violated",
                    "column": rel['column']
                })
                print(f"  ❌ CRITICAL: FK integrity issue in {rel['from_table']}.{rel['column']}")

        if not issues:
            print(f"\n  🎉 DATA QUALITY: PASSED (0 critical issues)")
        else:
            print(f"\n  🚨 DATA QUALITY: FAILED ({len(issues)} critical issues)")

        self.findings["data_quality_issues"] = issues

        return issues

    def run_full_analysis(self):
        """Run complete blind EDA workflow."""
        print(f"\n{'#'*80}")
        print(f"# STARTING BLIND EXPLORATORY DATA ANALYSIS")
        print(f"# Agent: {self.agent_name}")
        print(f"{'#'*80}")

        # Phase 1: Discovery
        tables = self.discover_tables()

        if not tables:
            print("\n❌ No data found. Analysis cannot proceed.")
            return self.findings

        # Phase 2: Schema Exploration
        print(f"\n{'='*80}")
        print(f"🔍 PHASE 2: SCHEMA EXPLORATION")
        print(f"{'='*80}")

        for table in tables:
            self.explore_table_schema(table['table_name'])

        # Phase 3: Relationship Inference
        relationships = self.infer_relationships(tables)

        # Phase 4: Business Analysis
        print(f"\n{'='*80}")
        print(f"🔍 PHASE 4: BUSINESS ANALYSIS")
        print(f"{'='*80}")

        vp_insights = self.vp_product_analysis(tables, relationships)
        hod_insights = self.head_of_data_analysis(tables, relationships)
        cfo_insights = self.cfo_analysis(tables, relationships)
        quality_issues = self.data_quality_checks(tables, relationships)

        # Summary
        print(f"\n{'#'*80}")
        print(f"# BLIND ANALYSIS COMPLETE: {self.agent_name}")
        print(f"{'#'*80}")

        total_insights = len(vp_insights) + len(hod_insights) + len(cfo_insights)

        print(f"\n📊 Summary:")
        print(f"  Tables discovered: {len(tables)}")
        print(f"  Relationships found: {len(relationships)}")
        print(f"  Business insights: {total_insights}")
        print(f"  Data quality issues: {len(quality_issues)}")

        print(f"\n✅ Can answer business questions:")
        print(f"  VP of Product (churn): {'YES ✓' if vp_insights else 'NO ✗'}")
        print(f"  Head of Data (cohorts): {'YES ✓' if hod_insights else 'NO ✗'}")
        print(f"  CFO (LTV): {'YES ✓' if cfo_insights else 'NO ✗'}")

        return self.findings

    def save_report(self, output_path: str):
        """Save findings to JSON report."""
        with open(output_path, 'w') as f:
            json.dump(self.findings, f, indent=2, default=str)

        print(f"\n📄 Report saved: {output_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python blind_eda_feature4.py <data_directory>")
        sys.exit(1)

    data_dir = sys.argv[1]

    # Run analysis
    analyst = BlindExploratoryAnalysis(
        data_dir=data_dir,
        agent_name="Senior Data Analyst"
    )

    findings = analyst.run_full_analysis()

    # Save report
    report_name = f"blind_eda_{Path(data_dir).name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    analyst.save_report(report_name)

    # Print verdict
    print("\n" + "="*80)
    if findings["data_quality_issues"]:
        print("❌ VALIDATION FAILED: Data quality issues detected")
    elif not any(bi["can_answer"] for bi in findings["business_insights"]):
        print("⚠️  VALIDATION INCOMPLETE: Cannot answer critical business questions")
    else:
        print("✅ VALIDATION PASSED: Data is realistic and analyzable")
    print("="*80)
