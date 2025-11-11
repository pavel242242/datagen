"""Report generation for datacruncher analysis."""

import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path


@dataclass
class Issue:
    """A single data quality issue found during analysis."""
    severity: str  # critical, high, medium, low
    category: str  # data_quality, business_logic, temporal, fk_integrity
    persona: str  # Name of persona that found the issue
    finding: str  # Human-readable description
    recommendation: str  # Suggested fix
    sql_query: str  # SQL query that found the issue


@dataclass
class Metrics:
    """Overall dataset quality metrics."""
    tables_analyzed: int
    total_rows: int
    fk_integrity: float  # Percentage (0-100)
    null_rate: float  # Average null percentage across all columns
    temporal_violations: float  # Percentage of temporal violations


@dataclass
class CrunchReport:
    """Complete datacruncher analysis report."""
    dataset: str
    personas: List[str]
    issues: List[Issue]
    metrics: Metrics
    analysis_date: str = None

    def __post_init__(self):
        if self.analysis_date is None:
            self.analysis_date = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "analysis_date": self.analysis_date,
            "dataset": self.dataset,
            "personas": self.personas,
            "issues": [asdict(issue) for issue in self.issues],
            "metrics": asdict(self.metrics),
            "summary": self._generate_summary(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, output_path: Path):
        """Save report to JSON file."""
        with open(output_path, "w") as f:
            f.write(self.to_json())

    def _generate_summary(self) -> Dict:
        """Generate summary statistics."""
        # Count issues by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in self.issues:
            severity_counts[issue.severity] += 1

        # Count issues by category
        category_counts = {}
        for issue in self.issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        # Compute quality score (0-100)
        quality_score = self._compute_quality_score(severity_counts)

        return {
            "total_issues": len(self.issues),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "quality_score": quality_score,
        }

    def _compute_quality_score(self, severity_counts: Dict[str, int]) -> int:
        """Compute overall quality score (0-100).

        Deduct points based on issue severity:
        - Critical: -20 points each
        - High: -10 points each
        - Medium: -5 points each
        - Low: -2 points each
        """
        score = 100

        score -= severity_counts["critical"] * 20
        score -= severity_counts["high"] * 10
        score -= severity_counts["medium"] * 5
        score -= severity_counts["low"] * 2

        return max(0, score)

    def print_summary(self):
        """Print human-readable summary to console."""
        summary = self._generate_summary()

        print(f"\n{'='*60}")
        print(f"DATACRUNCHER ANALYSIS REPORT")
        print(f"{'='*60}")
        print(f"Dataset: {self.dataset}")
        print(f"Analysis Date: {self.analysis_date}")
        print(f"Personas: {', '.join(self.personas)}")
        print(f"\nQuality Score: {summary['quality_score']}/100")

        print(f"\n{'='*60}")
        print(f"METRICS")
        print(f"{'='*60}")
        print(f"Tables Analyzed: {self.metrics.tables_analyzed}")
        print(f"Total Rows: {self.metrics.total_rows:,}")
        print(f"FK Integrity: {self.metrics.fk_integrity}%")
        print(f"Avg Null Rate: {self.metrics.null_rate}%")

        print(f"\n{'='*60}")
        print(f"ISSUES SUMMARY")
        print(f"{'='*60}")
        print(f"Total Issues: {summary['total_issues']}")
        print(f"  Critical: {summary['by_severity']['critical']}")
        print(f"  High:     {summary['by_severity']['high']}")
        print(f"  Medium:   {summary['by_severity']['medium']}")
        print(f"  Low:      {summary['by_severity']['low']}")

        if self.issues:
            print(f"\n{'='*60}")
            print(f"DETAILED ISSUES")
            print(f"{'='*60}")

            # Group by severity
            for severity in ["critical", "high", "medium", "low"]:
                severity_issues = [i for i in self.issues if i.severity == severity]
                if severity_issues:
                    print(f"\n[{severity.upper()}]")
                    for issue in severity_issues:
                        print(f"  • {issue.finding}")
                        print(f"    → {issue.recommendation}")
                        print(f"    (Found by: {issue.persona})")
                        print()

        print(f"{'='*60}\n")
