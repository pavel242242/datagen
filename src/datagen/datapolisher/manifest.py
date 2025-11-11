"""YAML manifest generation for approved datasets."""

import yaml
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import pandas as pd


def generate_manifest(
    dataset_name: str,
    data_dir: Path,
    crunch_report: Dict,
    generator_version: str = "1.0.0",
    schema_path: Path = None,
    seed: int = None,
) -> Dict:
    """Generate .manifest.yaml for approved dataset.

    Args:
        dataset_name: Name of the dataset
        data_dir: Directory with parquet files
        crunch_report: Datacruncher report dict
        generator_version: Datagen version
        schema_path: Path to original schema JSON
        seed: Master seed used for generation

    Returns:
        Dictionary ready to be written as YAML
    """
    # Load metadata if available
    metadata_file = data_dir / ".metadata.json"
    if metadata_file.exists():
        import json
        with open(metadata_file) as f:
            metadata = json.load(f)
            generated_at = metadata.get("generated_at")
            seed = seed or metadata.get("master_seed")
    else:
        generated_at = datetime.utcnow().isoformat() + "Z"

    # Build table schemas
    tables = []
    for parquet_file in sorted(data_dir.glob("*.parquet")):
        table_name = parquet_file.stem
        df = pd.read_parquet(parquet_file)

        # Infer columns with types
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            nullable = df[col].isna().any()

            # Map pandas dtype to simplified type
            if "int" in dtype:
                col_type = "int64"
            elif "float" in dtype:
                col_type = "float64"
            elif "datetime" in dtype:
                col_type = "timestamp[ns]"
            elif "bool" in dtype:
                col_type = "bool"
            else:
                col_type = "string"

            columns.append({
                "name": col,
                "type": col_type,
                "nullable": bool(nullable),
            })

        tables.append({
            "name": table_name,
            "rows": len(df),
            "columns": columns,
        })

    # Extract validation info from crunch report
    metrics = crunch_report.get("metrics", {})
    summary = crunch_report.get("summary", {})

    manifest = {
        "dataset_name": dataset_name,
        "generated_at": generated_at,
        "generator_version": generator_version,
        "quality_score": f"{summary.get('quality_score', 0)}/100",
        "schema": {
            "source": str(schema_path) if schema_path else "unknown",
            "seed": seed,
            "tables": tables,
        },
        "validation": {
            "datacruncher_version": generator_version,
            "analyzed_by": crunch_report.get("personas", []),
            "findings": summary.get("by_severity", {}),
            "metrics": {
                "fk_integrity": f"{metrics.get('fk_integrity', 0)}%",
                "temporal_violations": f"{metrics.get('temporal_violations', 0)}%",
                "null_rate": f"{metrics.get('null_rate', 0)}%",
            },
        },
        "approval": {
            "approved": True,
            "approved_by": "datacruncher",
            "approved_at": datetime.utcnow().isoformat() + "Z",
            "notes": _generate_approval_notes(summary),
        },
    }

    return manifest


def write_manifest(manifest: Dict, output_path: Path):
    """Write manifest to YAML file."""
    with open(output_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)


def _generate_approval_notes(summary: Dict) -> str:
    """Generate approval notes based on summary."""
    quality_score = summary.get("quality_score", 0)
    severity_counts = summary.get("by_severity", {})

    if quality_score >= 95 and severity_counts.get("critical", 0) == 0:
        return "Dataset meets quality standards for production use"
    elif quality_score >= 80 and severity_counts.get("critical", 0) == 0:
        return "Dataset approved with minor issues documented"
    elif severity_counts.get("critical", 0) == 0:
        return "Dataset approved - review medium/high issues as needed"
    else:
        return "Dataset approved - critical issues resolved or accepted"
