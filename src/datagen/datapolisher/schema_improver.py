"""Schema improvement logic (Path 1)."""

import json
from pathlib import Path
from typing import Dict, List
from copy import deepcopy


class SchemaImprover:
    """Improves JSON schemas based on datacruncher findings."""

    def __init__(
        self,
        crunch_report: Dict,
        original_schema: Dict,
    ):
        self.crunch_report = crunch_report
        self.original_schema = original_schema
        self.improved_schema = deepcopy(original_schema)
        self.changes_made = []

    def can_improve(self) -> tuple[bool, str]:
        """Check if issues can be fixed via schema improvements.

        Returns:
            (can_improve, reason) tuple
        """
        issues = self.crunch_report.get("issues", [])

        # Count schema-fixable issues
        fixable_count = 0
        for issue in issues:
            if self._is_schema_fixable(issue):
                fixable_count += 1

        if fixable_count == 0:
            return False, "No schema-fixable issues found"

        return True, f"{fixable_count} issues can be fixed via schema improvements"

    def improve(self) -> tuple[Dict, List[str]]:
        """Improve schema based on issues.

        Returns:
            (improved_schema, list_of_changes) tuple
        """
        issues = self.crunch_report.get("issues", [])

        for issue in issues:
            if self._is_schema_fixable(issue):
                self._apply_fix(issue)

        return self.improved_schema, self.changes_made

    def save_improved_schema(self, output_path: Path):
        """Save improved schema to file."""
        with open(output_path, "w") as f:
            json.dump(self.improved_schema, f, indent=2)

    def _is_schema_fixable(self, issue: Dict) -> bool:
        """Check if issue can be fixed via schema changes."""
        finding = issue.get("finding", "").lower()
        category = issue.get("category", "")

        # Temporal violations -> add vintage behavior
        if "temporal" in category or "before" in finding:
            return True

        # High null rate -> mark column as nullable
        if "null rate" in finding and "high" in finding:
            return True

        # FK integrity -> check generator
        if "fk integrity" in finding or "orphaned" in finding:
            return True

        return False

    def _apply_fix(self, issue: Dict):
        """Apply fix to schema based on issue."""
        finding = issue.get("finding", "").lower()
        category = issue.get("category", "")

        # Fix 1: Temporal violations -> add vintage behavior
        if "temporal" in category or "before" in finding:
            self._add_vintage_behavior(issue)

        # Fix 2: High null rate -> mark column as nullable
        elif "null rate" in finding and "high" in finding:
            self._mark_nullable(issue)

        # Fix 3: FK integrity -> verify lookup generator
        elif "fk integrity" in finding or "orphaned" in finding:
            self._fix_fk_lookup(issue)

    def _add_vintage_behavior(self, issue: Dict):
        """Add vintage_behavior to fact table."""
        finding = issue.get("finding", "")

        # Extract table name from finding (e.g., "in payment occur before")
        parts = finding.split(" in ")
        if len(parts) < 2:
            return

        table_part = parts[1].split(" ")[0]
        table_name = table_part.strip()

        # Find the node
        for node in self.improved_schema.get("nodes", []):
            if node["id"] == table_name and node.get("kind") == "fact":
                # Find timestamp column
                timestamp_col = None
                for col in node.get("columns", []):
                    if col["type"] == "datetime":
                        timestamp_col = col["name"]
                        break

                if timestamp_col:
                    # Add vintage_behavior
                    if "vintage_behavior" not in node:
                        node["vintage_behavior"] = {
                            "created_at_column": timestamp_col,
                            "distribution": {"kind": "uniform", "min": 0, "max": 30},
                        }
                        self.changes_made.append(
                            f"Added vintage_behavior to {table_name} (created_at_column: {timestamp_col})"
                        )

    def _mark_nullable(self, issue: Dict):
        """Mark column as nullable in schema."""
        finding = issue.get("finding", "")

        # Extract table and column (e.g., "in subscription_event.previous_state")
        if " in " in finding:
            parts = finding.split(" in ")
            if len(parts) >= 2:
                table_col = parts[1].split(":")[0].strip()
                if "." in table_col:
                    table_name, col_name = table_col.split(".", 1)

                    # Find node and column
                    for node in self.improved_schema.get("nodes", []):
                        if node["id"] == table_name:
                            for col in node.get("columns", []):
                                if col["name"] == col_name:
                                    if not col.get("nullable", False):
                                        col["nullable"] = True
                                        self.changes_made.append(
                                            f"Marked {table_name}.{col_name} as nullable"
                                        )

    def _fix_fk_lookup(self, issue: Dict):
        """Fix FK lookup generator."""
        finding = issue.get("finding", "")

        # Extract child and parent table
        # Format: "in child_table.fk_col → parent_table.pk_col"
        if "→" in finding:
            parts = finding.split("→")
            if len(parts) >= 2:
                left = parts[0].split(" in ")[-1].strip()
                right = parts[1].split()[0].strip()

                if "." in left and "." in right:
                    child_table, fk_col = left.split(".", 1)
                    parent_table, pk_col = right.split(".", 1)

                    # Check if lookup generator exists and is correct
                    for node in self.improved_schema.get("nodes", []):
                        if node["id"] == child_table:
                            for col in node.get("columns", []):
                                if col["name"] == fk_col:
                                    # Verify lookup generator
                                    generator = col.get("generator", {})
                                    if "lookup" in generator:
                                        lookup_from = generator["lookup"].get("from", "")
                                        expected = f"{parent_table}.{pk_col}"

                                        if lookup_from != expected:
                                            generator["lookup"]["from"] = expected
                                            self.changes_made.append(
                                                f"Fixed FK lookup in {child_table}.{fk_col}: {lookup_from} → {expected}"
                                            )
