"""Analyst personas with SQL query patterns for data quality analysis."""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class AnalysisQuery:
    """A single analysis query with expected behavior."""
    name: str
    description: str
    sql_template: str
    severity: str  # critical, high, medium, low
    category: str  # data_quality, business_logic, temporal, fk_integrity


class Persona:
    """Analyst persona with specific focus areas and queries."""

    def __init__(self, name: str, focus: str):
        self.name = name
        self.focus = focus
        self.queries: List[AnalysisQuery] = []

    def add_query(self, query: AnalysisQuery):
        """Add an analysis query to this persona."""
        self.queries.append(query)


# ============================================================================
# VP of Growth Persona
# ============================================================================

VP_GROWTH = Persona(
    name="VP of Growth",
    focus="Cohort retention, activation rates, funnel conversion"
)

VP_GROWTH.add_query(AnalysisQuery(
    name="temporal_violations",
    description="Check for events occurring before entity creation",
    sql_template="""
        SELECT
            '{table}' as table_name,
            COUNT(*) as violations,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table}), 2) as violation_pct
        FROM {table} t
        JOIN {parent_table} p ON t.{fk_col} = p.{pk_col}
        WHERE t.{timestamp_col} < p.{parent_timestamp_col}
    """,
    severity="critical",
    category="temporal"
))

VP_GROWTH.add_query(AnalysisQuery(
    name="activation_rate",
    description="Calculate activation rate (users with at least one key action)",
    sql_template="""
        WITH active_users AS (
            SELECT DISTINCT {parent_id_col}
            FROM {fact_table}
        )
        SELECT
            COUNT(DISTINCT a.{parent_id_col}) as activated,
            COUNT(DISTINCT p.{parent_id_col}) as total,
            ROUND(COUNT(DISTINCT a.{parent_id_col}) * 100.0 / COUNT(DISTINCT p.{parent_id_col}), 2) as activation_rate
        FROM {parent_table} p
        LEFT JOIN active_users a ON p.{parent_id_col} = a.{parent_id_col}
    """,
    severity="high",
    category="business_logic"
))

# ============================================================================
# Data Engineer Persona
# ============================================================================

DATA_ENGINEER = Persona(
    name="Data Engineer",
    focus="FK integrity, null rates, temporal ordering, duplicates"
)

DATA_ENGINEER.add_query(AnalysisQuery(
    name="fk_integrity",
    description="Verify foreign key references are valid",
    sql_template="""
        SELECT
            '{child_table}' as child_table,
            '{fk_col}' as fk_column,
            '{parent_table}' as parent_table,
            COUNT(*) as orphaned_rows,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {child_table}), 2) as orphaned_pct
        FROM {child_table} c
        LEFT JOIN {parent_table} p ON c.{fk_col} = p.{pk_col}
        WHERE p.{pk_col} IS NULL
    """,
    severity="critical",
    category="fk_integrity"
))

DATA_ENGINEER.add_query(AnalysisQuery(
    name="duplicate_pks",
    description="Check for duplicate primary keys",
    sql_template="""
        SELECT
            '{table}' as table_name,
            '{pk_col}' as pk_column,
            COUNT(*) as duplicate_count
        FROM {table}
        GROUP BY {pk_col}
        HAVING COUNT(*) > 1
    """,
    severity="critical",
    category="data_quality"
))

DATA_ENGINEER.add_query(AnalysisQuery(
    name="null_rate",
    description="Calculate null rates for non-nullable columns",
    sql_template="""
        SELECT
            '{table}' as table_name,
            '{column}' as column_name,
            COUNT(*) - COUNT({column}) as null_count,
            ROUND((COUNT(*) - COUNT({column})) * 100.0 / COUNT(*), 2) as null_pct
        FROM {table}
    """,
    severity="high",
    category="data_quality"
))

# ============================================================================
# Finance VP Persona
# ============================================================================

FINANCE_VP = Persona(
    name="Finance VP",
    focus="Revenue trends, pricing consistency, payment integrity"
)

FINANCE_VP.add_query(AnalysisQuery(
    name="pricing_consistency",
    description="Check if pricing varies correctly by tier/segment",
    sql_template="""
        WITH tier_pricing AS (
            SELECT
                {segment_col} as segment,
                AVG({price_col}) as avg_price,
                STDDEV({price_col}) as stddev_price,
                COUNT(*) as count
            FROM {table}
            GROUP BY {segment_col}
        )
        SELECT
            segment,
            ROUND(avg_price, 2) as avg_price,
            ROUND(stddev_price, 2) as stddev_price,
            count,
            ROUND(avg_price / (SELECT AVG(avg_price) FROM tier_pricing), 2) as price_ratio
        FROM tier_pricing
        ORDER BY avg_price
    """,
    severity="high",
    category="business_logic"
))

FINANCE_VP.add_query(AnalysisQuery(
    name="payment_anomalies",
    description="Detect anomalous payment amounts (outliers)",
    sql_template="""
        WITH stats AS (
            SELECT
                AVG({amount_col}) as mean,
                STDDEV({amount_col}) as stddev
            FROM {table}
        )
        SELECT
            COUNT(*) as outlier_count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table}), 2) as outlier_pct,
            MIN({amount_col}) as min_outlier,
            MAX({amount_col}) as max_outlier
        FROM {table}, stats
        WHERE {amount_col} > mean + 3 * stddev
           OR {amount_col} < mean - 3 * stddev
    """,
    severity="medium",
    category="data_quality"
))

# ============================================================================
# Customer Success VP Persona
# ============================================================================

CUSTOMER_SUCCESS_VP = Persona(
    name="Customer Success VP",
    focus="Churn patterns, engagement metrics, lifecycle health"
)

CUSTOMER_SUCCESS_VP.add_query(AnalysisQuery(
    name="churn_rate",
    description="Calculate churn rate based on last activity",
    sql_template="""
        WITH last_activity AS (
            SELECT
                {parent_id_col},
                MAX({timestamp_col}) as last_seen
            FROM {fact_table}
            GROUP BY {parent_id_col}
        ),
        churned AS (
            SELECT COUNT(*) as churned_count
            FROM last_activity
            WHERE last_seen < CURRENT_DATE - INTERVAL '{churn_days} days'
        )
        SELECT
            churned_count,
            (SELECT COUNT(*) FROM {parent_table}) as total,
            ROUND(churned_count * 100.0 / (SELECT COUNT(*) FROM {parent_table}), 2) as churn_rate
        FROM churned
    """,
    severity="high",
    category="business_logic"
))

# ============================================================================
# Persona Registry
# ============================================================================

PERSONA_REGISTRY: Dict[str, Persona] = {
    "vp_growth": VP_GROWTH,
    "data_engineer": DATA_ENGINEER,
    "finance_vp": FINANCE_VP,
    "customer_success_vp": CUSTOMER_SUCCESS_VP,
}


def get_persona(name: str) -> Persona:
    """Get persona by name."""
    normalized = name.lower().replace(" ", "_")
    if normalized not in PERSONA_REGISTRY:
        available = ", ".join(PERSONA_REGISTRY.keys())
        raise ValueError(
            f"Persona '{name}' not found. Available: {available}"
        )
    return PERSONA_REGISTRY[normalized]


def list_personas() -> List[str]:
    """List all available personas."""
    return list(PERSONA_REGISTRY.keys())
