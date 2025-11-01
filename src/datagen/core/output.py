"""Output management for Parquet, CSV, and metadata."""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def write_parquet(df: pd.DataFrame, path: Path):
    """
    Write DataFrame to Parquet file.

    Args:
        df: DataFrame to write
        path: Output file path
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to PyArrow table for better control
    table = pa.Table.from_pandas(df)

    # Write with compression
    pq.write_table(table, path, compression='snappy')

    logger.debug(f"Wrote Parquet: {path} ({len(df)} rows, {len(df.columns)} columns)")


def write_metadata(metadata: dict, path: Path):
    """
    Write metadata JSON file.

    Args:
        metadata: Metadata dictionary
        path: Output file path
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.debug(f"Wrote metadata: {path}")


def read_parquet(path: Path) -> pd.DataFrame:
    """
    Read Parquet file to DataFrame.

    Args:
        path: Parquet file path

    Returns:
        DataFrame
    """
    return pd.read_parquet(path)


def read_metadata(path: Path) -> dict:
    """
    Read metadata JSON file.

    Args:
        path: Metadata file path

    Returns:
        Metadata dictionary
    """
    with open(path) as f:
        return json.load(f)


def write_csv(df: pd.DataFrame, path: Path, include_index: bool = False):
    """
    Write DataFrame to CSV file.

    Args:
        df: DataFrame to write
        path: Output file path
        include_index: Whether to include index in CSV
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV with UTF-8 encoding
    df.to_csv(path, index=include_index, encoding='utf-8')

    logger.debug(f"Wrote CSV: {path} ({len(df)} rows, {len(df.columns)} columns)")


def write_table_metadata(
    df: pd.DataFrame,
    table_name: str,
    path: Path,
    schema_info: Optional[Dict[str, Any]] = None
):
    """
    Write Keboola-compatible table metadata (manifest file).

    Args:
        df: DataFrame with table data
        table_name: Name of the table
        path: Output path for metadata file (e.g., table.csv.manifest)
        schema_info: Optional schema information (primary key, columns, etc.)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build metadata structure
    metadata = {
        "name": table_name,
        "columns": []
    }

    # Add column information
    for col in df.columns:
        col_meta = {
            "name": col,
            "data_type": str(df[col].dtype)
        }
        metadata["columns"].append(col_meta)

    # Add schema info if provided
    if schema_info:
        if "primary_key" in schema_info:
            metadata["primary_key"] = schema_info["primary_key"]
        if "incremental" in schema_info:
            metadata["incremental"] = schema_info["incremental"]
        if "delimiter" in schema_info:
            metadata["delimiter"] = schema_info["delimiter"]
        if "enclosure" in schema_info:
            metadata["enclosure"] = schema_info["enclosure"]

    with open(path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.debug(f"Wrote table metadata: {path}")


def write_enhanced_metadata(
    dataset_name: str,
    dataset_version: str,
    master_seed: int,
    tables: Dict[str, Dict[str, Any]],
    schema_path: Optional[Path],
    output_path: Path,
    generation_stats: Optional[Dict[str, Any]] = None
):
    """
    Write enhanced metadata with full schema information.

    Args:
        dataset_name: Name of the dataset
        dataset_version: Version of the schema
        master_seed: Seed used for generation
        tables: Dictionary of table information
        schema_path: Path to the original schema file
        output_path: Output path for metadata file
        generation_stats: Optional generation statistics
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "dataset_name": dataset_name,
        "version": dataset_version,
        "master_seed": master_seed,
        "schema_file": str(schema_path) if schema_path else None,
        "tables": tables
    }

    if generation_stats:
        metadata["generation_stats"] = generation_stats

    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.debug(f"Wrote enhanced metadata: {output_path}")
