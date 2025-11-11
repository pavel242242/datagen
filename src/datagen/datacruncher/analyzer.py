"""DuckDB-based data quality analyzer with multi-persona analysis."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

import duckdb
import pandas as pd

from .personas import Persona, get_persona, list_personas
from .report import CrunchReport, Issue, Metrics


@dataclass
class AnalysisConfig:
    """Configuration for datacruncher analysis."""
    data_dir: Path
    schema_path: Optional[Path] = None
    personas: List[str] = None
    verbose: bool = False

    def __post_init__(self):
        if self.personas is None:
            # Default personas
            self.personas = ["data_engineer", "vp_growth"]


class DataCruncher:
    """Orchestrates multi-persona data quality analysis using DuckDB."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self.tables: Dict[str, pd.DataFrame] = {}
        self.schema: Optional[Dict] = None

    def analyze(self) -> CrunchReport:
        """Run full analysis pipeline."""
        # Step 1: Load data into DuckDB
        self._load_data()

        # Step 2: Load schema if provided
        if self.config.schema_path:
            self._load_schema()

        # Step 3: Run persona analyses
        issues = []
        for persona_name in self.config.personas:
            persona = get_persona(persona_name)
            persona_issues = self._run_persona_analysis(persona)
            issues.extend(persona_issues)

        # Step 4: Compute metrics
        metrics = self._compute_metrics()

        # Step 5: Generate report
        report = CrunchReport(
            dataset=str(self.config.data_dir),
            personas=self.config.personas,
            issues=issues,
            metrics=metrics,
        )

        # Close connection
        if self.conn:
            self.conn.close()

        return report

    def _load_data(self):
        """Load parquet files into DuckDB."""
        data_dir = Path(self.config.data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        # Find all parquet files
        parquet_files = list(data_dir.glob("*.parquet"))
        if not parquet_files:
            raise ValueError(f"No parquet files found in {data_dir}")

        if self.config.verbose:
            print(f"Loading {len(parquet_files)} parquet files...")

        # Create DuckDB connection
        self.conn = duckdb.connect(":memory:")

        # Load each parquet file as a table
        for parquet_file in parquet_files:
            table_name = parquet_file.stem  # filename without extension

            # Load into DuckDB
            self.conn.execute(
                f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{parquet_file}')"
            )

            # Also load into pandas for easier inspection
            self.tables[table_name] = self.conn.execute(
                f"SELECT * FROM {table_name}"
            ).df()

            if self.config.verbose:
                row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                print(f"  → {table_name}: {row_count} rows")

    def _load_schema(self):
        """Load original JSON schema for reference."""
        if not self.config.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.config.schema_path}")

        with open(self.config.schema_path) as f:
            self.schema = json.load(f)

    def _run_persona_analysis(self, persona: Persona) -> List[Issue]:
        """Run all queries for a given persona."""
        if self.config.verbose:
            print(f"\nRunning {persona.name} analysis ({persona.focus})...")

        issues = []

        for query_spec in persona.queries:
            # Try to fill SQL template with schema info
            try:
                filled_queries = self._fill_query_template(query_spec.sql_template, query_spec)

                for table_context, filled_sql in filled_queries:
                    try:
                        result = self.conn.execute(filled_sql).df()

                        # Check if query found issues
                        if len(result) > 0:
                            # Extract issue details from result
                            issue = self._parse_query_result(
                                persona=persona,
                                query_spec=query_spec,
                                result=result,
                                context=table_context,
                            )
                            if issue:
                                issues.append(issue)

                                if self.config.verbose:
                                    print(f"  ⚠️  {query_spec.name}: {issue.finding}")

                    except Exception as e:
                        if self.config.verbose:
                            print(f"  ⚠️  {query_spec.name} query failed: {e}")

            except Exception as e:
                if self.config.verbose:
                    print(f"  ⚠️  Could not fill template for {query_spec.name}: {e}")

        return issues

    def _fill_query_template(self, template: str, query_spec) -> List[tuple]:
        """Fill SQL template with table/column names from loaded data.

        Returns list of (context_dict, filled_sql) tuples.
        """
        filled_queries = []

        # For FK integrity checks
        if "fk_integrity" in query_spec.name:
            # Find all FK relationships from schema
            if self.schema:
                fks = self.schema.get("constraints", {}).get("foreign_keys", [])
                for fk in fks:
                    # Parse FK: "child.col" -> "parent.col"
                    from_parts = fk["from"].split(".")
                    to_parts = fk["to"].split(".")

                    if len(from_parts) == 2 and len(to_parts) == 2:
                        child_table, fk_col = from_parts
                        parent_table, pk_col = to_parts

                        # Check if tables exist
                        if child_table in self.tables and parent_table in self.tables:
                            context = {
                                "child_table": child_table,
                                "fk_col": fk_col,
                                "parent_table": parent_table,
                                "pk_col": pk_col,
                            }
                            filled_sql = template.format(**context)
                            filled_queries.append((context, filled_sql))

        # For temporal violations
        elif "temporal" in query_spec.name:
            if self.schema:
                # Find tables with temporal columns
                nodes = self.schema.get("nodes", [])
                for node in nodes:
                    if node.get("kind") == "fact" and node.get("parents"):
                        fact_table = node["id"]
                        parent_table = node["parents"][0]  # Use first parent

                        if fact_table in self.tables and parent_table in self.tables:
                            # Find timestamp columns
                            fact_ts = self._find_timestamp_column(fact_table)
                            parent_ts = self._find_timestamp_column(parent_table)

                            # Find FK column
                            fk_col = self._find_fk_column(fact_table, parent_table)
                            pk_col = self._find_pk_column(parent_table)

                            if fact_ts and parent_ts and fk_col and pk_col:
                                context = {
                                    "table": fact_table,
                                    "parent_table": parent_table,
                                    "fk_col": fk_col,
                                    "pk_col": pk_col,
                                    "timestamp_col": fact_ts,
                                    "parent_timestamp_col": parent_ts,
                                }
                                filled_sql = template.format(**context)
                                filled_queries.append((context, filled_sql))

        # For activation rate
        elif "activation" in query_spec.name:
            if self.schema:
                nodes = self.schema.get("nodes", [])
                for node in nodes:
                    if node.get("kind") == "fact" and node.get("parents"):
                        fact_table = node["id"]
                        parent_table = node["parents"][0]

                        if fact_table in self.tables and parent_table in self.tables:
                            parent_id_col = self._find_pk_column(parent_table)

                            if parent_id_col:
                                context = {
                                    "fact_table": fact_table,
                                    "parent_table": parent_table,
                                    "parent_id_col": parent_id_col,
                                }
                                filled_sql = template.format(**context)
                                filled_queries.append((context, filled_sql))

        # For duplicate PKs
        elif "duplicate" in query_spec.name:
            for table_name in self.tables.keys():
                pk_col = self._find_pk_column(table_name)
                if pk_col:
                    context = {
                        "table": table_name,
                        "pk_col": pk_col,
                    }
                    filled_sql = template.format(**context)
                    filled_queries.append((context, filled_sql))

        # For null rate
        elif "null" in query_spec.name:
            for table_name, df in self.tables.items():
                for col in df.columns:
                    context = {
                        "table": table_name,
                        "column": col,
                    }
                    filled_sql = template.format(**context)
                    filled_queries.append((context, filled_sql))

        return filled_queries

    def _parse_query_result(
        self, persona: Persona, query_spec, result: pd.DataFrame, context: dict
    ) -> Optional[Issue]:
        """Parse query result and create Issue if problems found."""

        # Check if result indicates a problem
        if len(result) == 0:
            return None

        # For FK integrity
        if "fk_integrity" in query_spec.name:
            row = result.iloc[0]
            orphaned = row.get("orphaned_rows", 0)
            orphaned_pct = row.get("orphaned_pct", 0)

            if orphaned > 0:
                return Issue(
                    severity=query_spec.severity,
                    category=query_spec.category,
                    persona=persona.name,
                    finding=f"FK integrity violation: {orphaned} orphaned rows ({orphaned_pct}%) in {context['child_table']}.{context['fk_col']} → {context['parent_table']}.{context['pk_col']}",
                    recommendation=f"Check data generation for {context['child_table']} - FK references invalid parent IDs",
                    sql_query=query_spec.sql_template,
                )

        # For temporal violations
        elif "temporal" in query_spec.name:
            row = result.iloc[0]
            violations = row.get("violations", 0)
            violation_pct = row.get("violation_pct", 0)

            if violations > 0:
                return Issue(
                    severity=query_spec.severity,
                    category=query_spec.category,
                    persona=persona.name,
                    finding=f"Temporal violations: {violations} events ({violation_pct}%) in {context['table']} occur before parent creation",
                    recommendation=f"Add created_at_column to vintage_behavior in schema for {context['table']}",
                    sql_query=query_spec.sql_template,
                )

        # For duplicate PKs
        elif "duplicate" in query_spec.name:
            if len(result) > 0:
                return Issue(
                    severity=query_spec.severity,
                    category=query_spec.category,
                    persona=persona.name,
                    finding=f"Duplicate primary keys found in {context['table']}.{context['pk_col']}: {len(result)} duplicates",
                    recommendation=f"Check sequence generator for {context['table']}.{context['pk_col']}",
                    sql_query=query_spec.sql_template,
                )

        # For null rate
        elif "null" in query_spec.name:
            row = result.iloc[0]
            null_count = row.get("null_count", 0)
            null_pct = row.get("null_pct", 0)

            # Only flag if significant nulls and column shouldn't be nullable
            if null_pct > 5.0:
                return Issue(
                    severity=query_spec.severity,
                    category=query_spec.category,
                    persona=persona.name,
                    finding=f"High null rate in {context['table']}.{context['column']}: {null_pct}% ({null_count} nulls)",
                    recommendation=f"Review generator for {context['table']}.{context['column']} or mark as nullable",
                    sql_query=query_spec.sql_template,
                )

        # For activation rate
        elif "activation" in query_spec.name:
            row = result.iloc[0]
            activation_rate = row.get("activation_rate", 0)

            # Flag if activation rate is unusually low
            if activation_rate < 30.0:
                return Issue(
                    severity=query_spec.severity,
                    category=query_spec.category,
                    persona=persona.name,
                    finding=f"Low activation rate: {activation_rate}% (industry avg 40-60%)",
                    recommendation=f"Review fanout distribution for {context['fact_table']} - increase lambda or adjust distribution",
                    sql_query=query_spec.sql_template,
                )

        return None

    def _compute_metrics(self) -> Metrics:
        """Compute overall dataset metrics."""
        total_rows = sum(len(df) for df in self.tables.values())

        # FK integrity check
        fk_integrity = 100.0
        if self.schema:
            fks = self.schema.get("constraints", {}).get("foreign_keys", [])
            for fk in fks:
                from_parts = fk["from"].split(".")
                to_parts = fk["to"].split(".")

                if len(from_parts) == 2 and len(to_parts) == 2:
                    child_table, fk_col = from_parts
                    parent_table, pk_col = to_parts

                    if child_table in self.tables and parent_table in self.tables:
                        child_df = self.tables[child_table]
                        parent_df = self.tables[parent_table]

                        valid = child_df[fk_col].isin(parent_df[pk_col]).sum()
                        pct = (valid / len(child_df)) * 100 if len(child_df) > 0 else 100.0
                        fk_integrity = min(fk_integrity, pct)

        # Null rate
        null_counts = []
        for df in self.tables.values():
            for col in df.columns:
                null_count = df[col].isna().sum()
                null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
                null_counts.append(null_pct)

        avg_null_rate = sum(null_counts) / len(null_counts) if null_counts else 0

        return Metrics(
            tables_analyzed=len(self.tables),
            total_rows=total_rows,
            fk_integrity=round(fk_integrity, 2),
            null_rate=round(avg_null_rate, 2),
            temporal_violations=0.0,  # TODO: compute from issues
        )

    def _find_timestamp_column(self, table_name: str) -> Optional[str]:
        """Find timestamp/datetime column in table."""
        if table_name not in self.tables:
            return None

        df = self.tables[table_name]
        for col in df.columns:
            if df[col].dtype == "datetime64[ns]" or "timestamp" in col.lower() or "date" in col.lower() or "_at" in col.lower():
                return col
        return None

    def _find_fk_column(self, child_table: str, parent_table: str) -> Optional[str]:
        """Find FK column referencing parent table."""
        if self.schema:
            fks = self.schema.get("constraints", {}).get("foreign_keys", [])
            for fk in fks:
                from_parts = fk["from"].split(".")
                to_parts = fk["to"].split(".")

                if len(from_parts) == 2 and len(to_parts) == 2:
                    if from_parts[0] == child_table and to_parts[0] == parent_table:
                        return from_parts[1]

        # Fallback: look for column named like parent_id
        if child_table in self.tables:
            df = self.tables[child_table]
            expected_col = f"{parent_table}_id"
            if expected_col in df.columns:
                return expected_col

        return None

    def _find_pk_column(self, table_name: str) -> Optional[str]:
        """Find primary key column for table."""
        if self.schema:
            nodes = self.schema.get("nodes", [])
            for node in nodes:
                if node["id"] == table_name:
                    return node.get("pk")

        # Fallback: look for column named table_id
        if table_name in self.tables:
            df = self.tables[table_name]
            expected_col = f"{table_name}_id"
            if expected_col in df.columns:
                return expected_col

        return None
