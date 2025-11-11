"""Main datapolisher orchestrator - resolves datacruncher findings."""

import json
from pathlib import Path
from typing import Dict, Optional, Literal
from dataclasses import dataclass

from .schema_improver import SchemaImprover
from .postprocessor import PostprocessorGenerator
from .approver import DatasetApprover


ResolutionPath = Literal["schema", "postprocess", "approve", "auto"]


@dataclass
class PolishConfig:
    """Configuration for datapolisher."""
    crunch_report_path: Path
    output_dir: Path = None
    path: ResolutionPath = "auto"
    force: bool = False
    postprocess_format: str = "duckdb"  # "duckdb" or "polars"


class DataPolisher:
    """Main orchestrator for resolving datacruncher findings."""

    def __init__(self, config: PolishConfig):
        self.config = config
        self.crunch_report: Optional[Dict] = None
        self.original_schema: Optional[Dict] = None
        self.data_dir: Optional[Path] = None

    def polish(self) -> Dict:
        """Run polishing pipeline.

        Returns:
            Dictionary with results:
            - path_taken: Which resolution path was used
            - files_generated: List of generated files
            - summary: Human-readable summary
        """
        # Step 1: Load crunch report
        self._load_crunch_report()

        # Step 2: Load original schema if available
        self._load_original_schema()

        # Step 3: Determine resolution path
        path = self._determine_path()

        # Step 4: Execute path
        if path == "schema":
            return self._execute_schema_path()
        elif path == "postprocess":
            return self._execute_postprocess_path()
        elif path == "approve":
            return self._execute_approve_path()
        else:
            raise ValueError(f"Unknown path: {path}")

    def _load_crunch_report(self):
        """Load and validate crunch report."""
        if not self.config.crunch_report_path.exists():
            raise FileNotFoundError(
                f"Crunch report not found: {self.config.crunch_report_path}"
            )

        with open(self.config.crunch_report_path) as f:
            self.crunch_report = json.load(f)

        # Extract data directory from report
        dataset_path = self.crunch_report.get("dataset", "")
        self.data_dir = Path(dataset_path)

        if not self.data_dir.exists():
            raise FileNotFoundError(
                f"Data directory from report not found: {self.data_dir}"
            )

    def _load_original_schema(self):
        """Try to load original JSON schema."""
        # Look for schema in data directory metadata
        metadata_file = self.data_dir / ".metadata.json"

        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                schema_path = metadata.get("schema_path")

                if schema_path and Path(schema_path).exists():
                    with open(schema_path) as f:
                        self.original_schema = json.load(f)

        # Fallback: look for schema file with same name
        if self.original_schema is None:
            dataset_name = self.data_dir.stem
            possible_schema = self.data_dir.parent / f"{dataset_name}.json"

            if possible_schema.exists():
                with open(possible_schema) as f:
                    self.original_schema = json.load(f)

    def _determine_path(self) -> str:
        """Determine which resolution path to take."""
        if self.config.path != "auto":
            return self.config.path

        # Auto-determine based on issues
        summary = self.crunch_report.get("summary", {})
        severity_counts = summary.get("by_severity", {})

        critical_count = severity_counts.get("critical", 0)
        high_count = severity_counts.get("high", 0)
        total_issues = summary.get("total_issues", 0)

        # If no critical/high issues, approve
        if critical_count == 0 and high_count == 0:
            return "approve"

        # If schema-fixable issues and schema available, improve schema
        if self.original_schema:
            improver = SchemaImprover(self.crunch_report, self.original_schema)
            can_improve, _ = improver.can_improve()

            if can_improve:
                return "schema"

        # If postprocess-fixable issues, generate postprocessing script
        postprocessor = PostprocessorGenerator(
            self.crunch_report,
            self.data_dir,
            format=self.config.postprocess_format,
        )
        can_postprocess, _ = postprocessor.can_postprocess()

        if can_postprocess:
            return "postprocess"

        # Default: approve if not too many issues
        if critical_count == 0 and high_count <= 3:
            return "approve"

        raise ValueError(
            f"Cannot auto-determine path: {critical_count} critical, {high_count} high issues. "
            f"Specify --path explicitly (schema/postprocess/approve)"
        )

    def _execute_schema_path(self) -> Dict:
        """Execute Path 1: Improve schema and regenerate."""
        if not self.original_schema:
            raise ValueError("Path 1 requires original schema - not found")

        improver = SchemaImprover(self.crunch_report, self.original_schema)
        can_improve, reason = improver.can_improve()

        if not can_improve and not self.config.force:
            raise ValueError(reason)

        # Improve schema
        improved_schema, changes = improver.improve()

        # Save improved schema
        output_dir = self.config.output_dir or self.data_dir.parent / "polished"
        output_dir.mkdir(parents=True, exist_ok=True)

        schema_output = output_dir / "schema_improved.json"
        improver.save_improved_schema(schema_output)

        return {
            "path_taken": "schema",
            "files_generated": [str(schema_output)],
            "changes_made": changes,
            "summary": (
                f"Schema improved with {len(changes)} changes. "
                f"Regenerate with: datagen generate {schema_output}"
            ),
        }

    def _execute_postprocess_path(self) -> Dict:
        """Execute Path 2: Generate postprocessing script."""
        postprocessor = PostprocessorGenerator(
            self.crunch_report,
            self.data_dir,
            format=self.config.postprocess_format,
        )

        can_postprocess, reason = postprocessor.can_postprocess()

        if not can_postprocess and not self.config.force:
            raise ValueError(reason)

        # Generate script
        script = postprocessor.generate_script()

        # Save script
        output_dir = self.config.output_dir or self.data_dir.parent / "polished"
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.postprocess_format == "duckdb":
            script_output = output_dir / "postprocess.sql"
        else:
            script_output = output_dir / "postprocess.py"

        postprocessor.save_script(script_output)

        return {
            "path_taken": "postprocess",
            "files_generated": [str(script_output)],
            "summary": (
                f"Postprocessing script generated: {script_output}\n"
                f"Run with: {'duckdb < ' if self.config.postprocess_format == 'duckdb' else 'python '}{script_output}"
            ),
        }

    def _execute_approve_path(self) -> Dict:
        """Execute Path 3: Approve dataset and generate manifest."""
        # Find schema path if available
        schema_path = None
        metadata_file = self.data_dir / ".metadata.json"

        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                schema_path_str = metadata.get("schema_path")
                if schema_path_str:
                    schema_path = Path(schema_path_str)

        approver = DatasetApprover(
            self.crunch_report,
            self.data_dir,
            schema_path=schema_path,
        )

        can_approve, reason = approver.can_approve()

        if not can_approve and not self.config.force:
            raise ValueError(reason)

        # Approve and generate manifest
        output_dir = self.config.output_dir or self.data_dir
        manifest_output = output_dir / ".manifest.yaml"

        approver.approve(output_path=manifest_output, force=self.config.force)

        return {
            "path_taken": "approve",
            "files_generated": [str(manifest_output)],
            "summary": (
                f"Dataset approved! Manifest: {manifest_output}\n"
                f"{reason}"
            ),
        }
