"""Tests for output module (Parquet, CSV, metadata writing)."""

import pytest
import tempfile
import pandas as pd
import json
from pathlib import Path

from datagen.core.output import (
    write_parquet,
    read_parquet,
    write_metadata,
    read_metadata,
    write_csv,
    write_table_metadata,
    write_enhanced_metadata
)


class TestParquetIO:
    """Tests for Parquet read/write operations."""

    def test_write_and_read_parquet(self):
        """Test writing and reading Parquet files."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [25, 30, 35, 40, 45],
            "score": [85.5, 92.3, 78.9, 88.1, 95.7]
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"

            # Write Parquet
            write_parquet(df, path)

            # Verify file exists
            assert path.exists()

            # Read back
            df_read = read_parquet(path)

            # Verify data
            assert len(df_read) == 5
            assert list(df_read.columns) == ["id", "name", "age", "score"]
            assert df_read["name"].tolist() == ["Alice", "Bob", "Charlie", "David", "Eve"]

    def test_write_parquet_creates_directory(self):
        """Test that write_parquet creates parent directories."""
        df = pd.DataFrame({"col": [1, 2, 3]})

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir1" / "subdir2" / "test.parquet"

            # Directory doesn't exist yet
            assert not path.parent.exists()

            # Write should create directory
            write_parquet(df, path)

            # Verify directory and file exist
            assert path.parent.exists()
            assert path.exists()


class TestMetadataIO:
    """Tests for metadata JSON read/write operations."""

    def test_write_and_read_metadata(self):
        """Test writing and reading metadata JSON."""
        metadata = {
            "dataset_name": "TestDataset",
            "master_seed": 42,
            "tables": {
                "user": {"rows": 100, "columns": 5},
                "order": {"rows": 500, "columns": 8}
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metadata.json"

            # Write metadata
            write_metadata(metadata, path)

            # Verify file exists
            assert path.exists()

            # Read back
            metadata_read = read_metadata(path)

            # Verify data
            assert metadata_read["dataset_name"] == "TestDataset"
            assert metadata_read["master_seed"] == 42
            assert metadata_read["tables"]["user"]["rows"] == 100

    def test_write_metadata_creates_directory(self):
        """Test that write_metadata creates parent directories."""
        metadata = {"test": "data"}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "metadata.json"

            # Directory doesn't exist yet
            assert not path.parent.exists()

            # Write should create directory
            write_metadata(metadata, path)

            # Verify directory and file exist
            assert path.parent.exists()
            assert path.exists()


class TestCSVIO:
    """Tests for CSV write operations."""

    def test_write_csv_without_index(self):
        """Test writing CSV without index."""
        df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35]
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.csv"

            # Write CSV without index
            write_csv(df, path, include_index=False)

            # Verify file exists
            assert path.exists()

            # Read back and verify
            df_read = pd.read_csv(path)
            assert len(df_read) == 3
            assert list(df_read.columns) == ["name", "age"]
            assert "Unnamed: 0" not in df_read.columns  # No index column

    def test_write_csv_with_index(self):
        """Test writing CSV with index."""
        df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [25, 30]
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.csv"

            # Write CSV with index
            write_csv(df, path, include_index=True)

            # Verify file exists
            assert path.exists()

            # Read back and verify index is present
            df_read = pd.read_csv(path, index_col=0)
            assert len(df_read) == 2

    def test_write_csv_creates_directory(self):
        """Test that write_csv creates parent directories."""
        df = pd.DataFrame({"col": [1, 2, 3]})

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output" / "test.csv"

            # Directory doesn't exist yet
            assert not path.parent.exists()

            # Write should create directory
            write_csv(df, path)

            # Verify directory and file exist
            assert path.parent.exists()
            assert path.exists()


class TestTableMetadata:
    """Tests for table metadata (manifest) generation."""

    def test_write_table_metadata_basic(self):
        """Test writing basic table metadata."""
        df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35]
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "user.csv.manifest"

            # Write metadata
            write_table_metadata(df, "user", path)

            # Verify file exists
            assert path.exists()

            # Read and verify
            with open(path) as f:
                metadata = json.load(f)

            assert metadata["name"] == "user"
            assert len(metadata["columns"]) == 3
            assert metadata["columns"][0]["name"] == "user_id"
            assert metadata["columns"][1]["name"] == "name"
            assert metadata["columns"][2]["name"] == "age"

    def test_write_table_metadata_with_schema_info(self):
        """Test writing table metadata with schema information."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30]
        })

        schema_info = {
            "primary_key": ["id"],
            "incremental": True,
            "delimiter": ",",
            "enclosure": "\""
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "table.manifest"

            # Write metadata with schema info
            write_table_metadata(df, "table", path, schema_info=schema_info)

            # Read and verify
            with open(path) as f:
                metadata = json.load(f)

            assert metadata["name"] == "table"
            assert metadata["primary_key"] == ["id"]
            assert metadata["incremental"] is True
            assert metadata["delimiter"] == ","
            assert metadata["enclosure"] == "\""


class TestEnhancedMetadata:
    """Tests for enhanced metadata generation."""

    def test_write_enhanced_metadata_basic(self):
        """Test writing enhanced metadata."""
        tables = {
            "user": {
                "rows": 100,
                "columns": ["user_id", "name", "email"],
                "primary_key": "user_id"
            },
            "order": {
                "rows": 500,
                "columns": ["order_id", "user_id", "amount"],
                "primary_key": "order_id"
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "enhanced_metadata.json"

            # Write enhanced metadata
            write_enhanced_metadata(
                dataset_name="EcommerceTest",
                dataset_version="1.0",
                master_seed=42,
                tables=tables,
                schema_path=Path("schema.json"),
                output_path=path
            )

            # Verify file exists
            assert path.exists()

            # Read and verify
            with open(path) as f:
                metadata = json.load(f)

            assert metadata["dataset_name"] == "EcommerceTest"
            assert metadata["version"] == "1.0"
            assert metadata["master_seed"] == 42
            assert metadata["schema_file"] == "schema.json"
            assert len(metadata["tables"]) == 2
            assert metadata["tables"]["user"]["rows"] == 100

    def test_write_enhanced_metadata_with_stats(self):
        """Test writing enhanced metadata with generation statistics."""
        tables = {"table1": {"rows": 50}}

        generation_stats = {
            "duration_seconds": 5.2,
            "total_rows": 1500,
            "tables_generated": 3
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metadata_with_stats.json"

            # Write enhanced metadata with stats
            write_enhanced_metadata(
                dataset_name="StatsTest",
                dataset_version="1.0",
                master_seed=123,
                tables=tables,
                schema_path=None,
                output_path=path,
                generation_stats=generation_stats
            )

            # Read and verify
            with open(path) as f:
                metadata = json.load(f)

            assert "generation_stats" in metadata
            assert metadata["generation_stats"]["duration_seconds"] == 5.2
            assert metadata["generation_stats"]["total_rows"] == 1500
            assert metadata["schema_file"] is None  # None was passed
