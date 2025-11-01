"""
Validation report generator.

Orchestrates all validators and produces:
- Comprehensive validation report
- Quality score (0-100)
- Summary statistics
- Detailed findings
"""

from typing import Dict, List
import json
from pathlib import Path
from datetime import datetime

from ..core.schema import Dataset
from .structural import StructuralValidator, ValidationResult
from .value import ValueValidator
from .behavioral import BehavioralValidator


class ValidationReport:
    """Complete validation report with quality score."""

    def __init__(self, dataset: Dataset, data_dir: Path):
        self.dataset = dataset
        self.data_dir = data_dir
        self.results: List[ValidationResult] = []
        self.quality_score: float = 0.0

    def run_all_validations(self) -> None:
        """Run all validation types."""
        # Structural validation
        structural = StructuralValidator(self.dataset, self.data_dir)
        self.results.extend(structural.validate_all())

        # Value validation
        value = ValueValidator(self.dataset, self.data_dir)
        self.results.extend(value.validate_all())

        # Behavioral validation
        behavioral = BehavioralValidator(self.dataset, self.data_dir)
        self.results.extend(behavioral.validate_all())

        # Compute quality score
        self._compute_quality_score()

    def _compute_quality_score(self) -> None:
        """Compute overall quality score (0-100)."""
        if not self.results:
            self.quality_score = 0.0
            return

        # Weight by validation type
        weights = {
            "structural": 0.5,  # Structural integrity is critical
            "value": 0.3,       # Value constraints are important
            "behavioral": 0.2   # Behavioral patterns are nice-to-have
        }

        # Categorize results
        categories = {
            "structural": [],
            "value": [],
            "behavioral": []
        }

        for result in self.results:
            if any(key in result.name for key in ["pk_", "fk_", ".exists"]):
                categories["structural"].append(result)
            elif any(key in result.name for key in ["range", "inequality", "pattern", "enum"]):
                categories["value"].append(result)
            elif any(key in result.name for key in ["metric_", "seasonality"]):
                categories["behavioral"].append(result)
            else:
                # Default to structural
                categories["structural"].append(result)

        # Compute weighted score
        total_score = 0.0
        for category, results in categories.items():
            if not results:
                # If no tests in category, assume perfect score
                category_score = 100.0
            else:
                passed = sum(1 for r in results if r.passed)
                category_score = (passed / len(results)) * 100

            total_score += category_score * weights[category]

        self.quality_score = total_score

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        # Group by table
        tables = {}
        for result in self.results:
            table_name = result.name.split(".")[0]
            if table_name not in tables:
                tables[table_name] = {"total": 0, "passed": 0, "failed": 0}
            tables[table_name]["total"] += 1
            if result.passed:
                tables[table_name]["passed"] += 1
            else:
                tables[table_name]["failed"] += 1

        # Group by validation type
        types = {
            "structural": {"total": 0, "passed": 0},
            "value": {"total": 0, "passed": 0},
            "behavioral": {"total": 0, "passed": 0}
        }

        for result in self.results:
            if any(key in result.name for key in ["pk_", "fk_", ".exists"]):
                category = "structural"
            elif any(key in result.name for key in ["range", "inequality", "pattern", "enum"]):
                category = "value"
            elif any(key in result.name for key in ["metric_", "seasonality"]):
                category = "behavioral"
            else:
                category = "structural"

            types[category]["total"] += 1
            if result.passed:
                types[category]["passed"] += 1

        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "quality_score": round(self.quality_score, 2),
            "by_table": tables,
            "by_type": types
        }

    def get_failures(self) -> List[Dict]:
        """Get all failed validations."""
        return [r.to_dict() for r in self.results if not r.passed]

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "metadata": {
                "dataset_name": self.dataset.metadata.name,
                "version": self.dataset.version,
                "timestamp": datetime.now().isoformat(),
                "data_directory": str(self.data_dir)
            },
            "summary": self.get_summary(),
            "failures": self.get_failures(),
            "all_results": [r.to_dict() for r in self.results]
        }

    def to_json(self, path: Path) -> None:
        """Write report to JSON file."""
        report_dict = self.to_dict()
        with open(path, "w") as f:
            json.dump(report_dict, f, indent=2)

    def print_summary(self) -> str:
        """Get human-readable summary."""
        summary = self.get_summary()

        lines = []
        lines.append("=" * 60)
        lines.append("VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Dataset: {self.dataset.metadata.name}")
        lines.append(f"Quality Score: {summary['quality_score']:.1f}/100")
        lines.append("")
        lines.append(f"Total Validations: {summary['total_validations']}")
        lines.append(f"  ✓ Passed: {summary['passed']}")
        lines.append(f"  ✗ Failed: {summary['failed']}")
        lines.append("")

        # By type
        lines.append("By Validation Type:")
        for vtype, stats in summary['by_type'].items():
            if stats['total'] > 0:
                pct = (stats['passed'] / stats['total']) * 100
                lines.append(f"  {vtype.capitalize()}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
        lines.append("")

        # By table
        lines.append("By Table:")
        for table, stats in summary['by_table'].items():
            pct = (stats['passed'] / stats['total']) * 100
            status = "✓" if stats['failed'] == 0 else "✗"
            lines.append(f"  {status} {table}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
        lines.append("")

        # Failed validations
        failures = self.get_failures()
        if failures:
            lines.append("Failed Validations:")
            for failure in failures[:10]:  # Show first 10
                lines.append(f"  ✗ {failure['name']}: {failure['message']}")
            if len(failures) > 10:
                lines.append(f"  ... and {len(failures) - 10} more failures")
        else:
            lines.append("✓ All validations passed!")

        lines.append("=" * 60)

        return "\n".join(lines)
