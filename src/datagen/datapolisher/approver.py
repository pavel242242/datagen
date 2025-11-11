"""Dataset approval logic (Path 3)."""

from pathlib import Path
from typing import Dict
from .manifest import generate_manifest, write_manifest


class DatasetApprover:
    """Approves datasets and generates .manifest.yaml files."""

    def __init__(
        self,
        crunch_report: Dict,
        data_dir: Path,
        schema_path: Path = None,
    ):
        self.crunch_report = crunch_report
        self.data_dir = data_dir
        self.schema_path = schema_path

    def can_approve(self) -> tuple[bool, str]:
        """Check if dataset can be approved.

        Returns:
            (can_approve, reason) tuple
        """
        summary = self.crunch_report.get("summary", {})
        severity_counts = summary.get("by_severity", {})

        critical_count = severity_counts.get("critical", 0)
        high_count = severity_counts.get("high", 0)
        quality_score = summary.get("quality_score", 0)

        if critical_count > 0:
            return False, f"Cannot approve: {critical_count} critical issues found"

        if high_count > 5:
            return False, f"Cannot approve: {high_count} high-severity issues found (max 5)"

        if quality_score < 50:
            return False, f"Cannot approve: quality score too low ({quality_score}/100, minimum 50)"

        return True, f"Dataset approved (quality score: {quality_score}/100)"

    def approve(self, output_path: Path = None, force: bool = False) -> Path:
        """Approve dataset and generate manifest.

        Args:
            output_path: Path to write .manifest.yaml (default: data_dir/.manifest.yaml)
            force: Force approval even if quality checks fail

        Returns:
            Path to generated manifest file

        Raises:
            ValueError: If dataset cannot be approved and force=False
        """
        # Check if can approve
        can_approve, reason = self.can_approve()

        if not can_approve and not force:
            raise ValueError(reason + "\nUse --force to approve anyway")

        # Generate manifest
        dataset_name = self.crunch_report.get("dataset", "Unknown Dataset")

        manifest = generate_manifest(
            dataset_name=dataset_name,
            data_dir=self.data_dir,
            crunch_report=self.crunch_report,
            schema_path=self.schema_path,
        )

        # Write to file
        if output_path is None:
            output_path = self.data_dir / ".manifest.yaml"

        write_manifest(manifest, output_path)

        return output_path
