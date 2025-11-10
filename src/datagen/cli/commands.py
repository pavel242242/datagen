"""Datagen CLI commands."""

import click
from pathlib import Path
import json
import logging

from datagen import __version__


@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Datagen - Universal synthetic dataset generator."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.option('--description', '-d', required=True, help='Natural language description')
@click.option('--output', '-o', type=click.Path(), help='Output file path (default: stdout)')
@click.option('--model', default='claude-sonnet-4-20250514', help='Claude model to use')
@click.option('--max-retries', default=3, type=int, help='Max auto-repair attempts')
def create(description, output, model, max_retries):
    """Create a schema from natural language description using Claude."""
    from rich.console import Console
    import os

    console = Console()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[bold red]❌ Error:[/bold red] ANTHROPIC_API_KEY environment variable not set")
        console.print("[yellow]Set it with:[/yellow] export ANTHROPIC_API_KEY=your-key-here")
        raise SystemExit(1)

    console.print(f"\n[bold blue]🤖 Generating schema with {model}...[/bold blue]")
    console.print(f"[dim]Description:[/dim] {description}")

    try:
        from datagen.llm import generate_schema_from_description

        # Generate schema
        schema_dict, dataset = generate_schema_from_description(
            description=description,
            model=model,
            max_retries=max_retries,
        )

        console.print(f"[bold green]✓[/bold green] Schema generated: {dataset.metadata.name}")
        console.print(f"[dim]Tables:[/dim] {len(dataset.nodes)}")

        # Format JSON nicely
        schema_json = json.dumps(schema_dict, indent=2)

        # Output to file or stdout
        if output:
            with open(output, 'w') as f:
                f.write(schema_json)
            console.print(f"[bold green]✓[/bold green] Written to: {output}")
        else:
            click.echo(schema_json)

    except ValueError as e:
        console.print(f"[bold red]❌ Schema generation failed:[/bold red]")
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Unexpected error:[/bold red]")
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


@cli.command()
@click.argument('schema_path', type=click.Path(exists=True))
@click.option('--seed', type=int, default=42, help='Master seed for reproducibility')
@click.option('--output-dir', '-o', type=click.Path(), default='./output', help='Output directory')
@click.option('--dry-run-sample', type=int, help='Generate only N sample rows for testing')
def generate(schema_path, seed, output_dir, dry_run_sample):
    """Generate synthetic data from a schema file."""
    from rich.console import Console
    from rich.progress import track
    from datagen.core.schema import validate_schema
    from datagen.core.executor import generate_dataset

    console = Console()

    console.print(f"\n[bold blue]📋 Loading schema:[/bold blue] {schema_path}")

    try:
        with open(schema_path) as f:
            schema_dict = json.load(f)

        # Validate schema
        dataset = validate_schema(schema_dict)
        console.print(f"[bold green]✓[/bold green] Schema valid: {dataset.metadata.name}")

    except Exception as e:
        console.print(f"[bold red]❌ Schema validation failed:[/bold red]")
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    console.print(f"[bold blue]🌱 Seed:[/bold blue] {seed}")
    console.print(f"[bold blue]📁 Output:[/bold blue] {output_dir}")

    if dry_run_sample:
        console.print(f"[yellow]🧪 Dry-run mode: {dry_run_sample} sample rows (not yet implemented)[/yellow]")

    # Generate dataset
    try:
        console.print(f"\n[bold cyan]🔧 Generating dataset...[/bold cyan]")

        result = generate_dataset(dataset, master_seed=seed, output_dir=Path(output_dir))

        console.print(f"\n[bold green]✅ Generation complete![/bold green]")

        # Summary
        console.print("\n[bold cyan]Generated Tables:[/bold cyan]")
        for table_id, df in result.items():
            console.print(f"  • {table_id}: {len(df):,} rows, {len(df.columns)} columns")

        console.print(f"\n[bold green]Output written to:[/bold green] {output_dir}")

    except Exception as e:
        console.print(f"\n[bold red]❌ Generation failed:[/bold red]")
        console.print(f"[red]{e}[/red]")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


@cli.command()
@click.argument('schema_path', type=click.Path(exists=True))
@click.option('--data-dir', '-d', type=click.Path(exists=True), required=True, help='Directory with generated Parquet files')
@click.option('--output', '-o', type=click.Path(), help='Validation report output path (JSON)')
def validate(schema_path, data_dir, output):
    """Validate generated data against schema constraints."""
    from rich.console import Console
    from datagen.core.schema import validate_schema
    from datagen.validation.report import ValidationReport

    console = Console()

    console.print(f"\n[bold blue]📋 Loading schema:[/bold blue] {schema_path}")

    try:
        with open(schema_path) as f:
            schema_dict = json.load(f)

        # Validate schema
        dataset = validate_schema(schema_dict)
        console.print(f"[bold green]✓[/bold green] Schema valid: {dataset.metadata.name}")

    except Exception as e:
        console.print(f"[bold red]❌ Schema validation failed:[/bold red]")
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    console.print(f"[bold blue]📁 Data directory:[/bold blue] {data_dir}")

    # Run validation
    try:
        console.print(f"\n[bold cyan]🔍 Running validations...[/bold cyan]")

        report = ValidationReport(dataset, Path(data_dir))
        report.run_all_validations()

        # Print summary
        console.print(f"\n{report.print_summary()}")

        # Save JSON report if requested
        if output:
            output_path = Path(output)
            report.to_json(output_path)
            console.print(f"\n[bold green]📄 Report saved to:[/bold green] {output}")

    except Exception as e:
        console.print(f"\n[bold red]❌ Validation failed:[/bold red]")
        console.print(f"[red]{e}[/red]")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


@cli.command()
@click.argument('schema_path', type=click.Path(exists=True))
@click.option('--data-dir', type=click.Path(exists=True), required=True, help='Directory with Parquet files')
@click.option('--output-dir', '-o', type=click.Path(), required=True, help='Output directory for CSV + metadata')
@click.option('--format', type=click.Choice(['csv', 'parquet']), default='csv', help='Output format')
def export(schema_path, data_dir, output_dir, format):
    """Export generated data to CSV with Keboola-compatible metadata."""
    from rich.console import Console
    from pathlib import Path
    import pandas as pd
    from datagen.core.schema import validate_schema
    from datagen.core.output import write_csv, write_table_metadata, write_enhanced_metadata

    console = Console()

    console.print(f"\n[bold blue]📋 Loading schema:[/bold blue] {schema_path}")

    try:
        with open(schema_path) as f:
            schema_dict = json.load(f)

        dataset = validate_schema(schema_dict)
        console.print(f"[bold green]✓[/bold green] Schema valid: {dataset.metadata.name}")

    except Exception as e:
        console.print(f"[bold red]❌ Schema validation failed:[/bold red]")
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold blue]📁 Input directory:[/bold blue] {data_dir}")
    console.print(f"[bold blue]📁 Output directory:[/bold blue] {output_dir}")
    console.print(f"[bold blue]📦 Output format:[/bold blue] {format.upper()}")

    # Read existing metadata
    metadata_file = data_path / ".metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            existing_metadata = json.load(f)
    else:
        existing_metadata = {}

    console.print(f"\n[bold cyan]🔄 Exporting tables...[/bold cyan]")

    tables_metadata = {}
    exported_count = 0

    # Process each node/table
    for node in dataset.nodes:
        table_name = node.id
        parquet_file = data_path / f"{table_name}.parquet"

        if not parquet_file.exists():
            console.print(f"  [yellow]⚠[/yellow] {table_name}: file not found, skipping")
            continue

        # Read data
        df = pd.read_parquet(parquet_file)

        # Export based on format
        if format == 'csv':
            output_file = output_path / f"{table_name}.csv"
            write_csv(df, output_file)

            # Write table manifest (Keboola metadata)
            manifest_file = output_path / f"{table_name}.csv.manifest"
            schema_info = {
                "primary_key": [node.pk] if node.pk else [],
                "delimiter": ",",
                "enclosure": '"'
            }
            write_table_metadata(df, table_name, manifest_file, schema_info)

            console.print(f"  [green]✓[/green] {table_name}: {len(df)} rows → {output_file.name}")
        else:
            # Copy parquet
            output_file = output_path / f"{table_name}.parquet"
            import shutil
            shutil.copy(parquet_file, output_file)
            console.print(f"  [green]✓[/green] {table_name}: {len(df)} rows → {output_file.name}")

        # Collect metadata
        tables_metadata[table_name] = {
            "rows": len(df),
            "columns": len(df.columns),
            "primary_key": node.pk,
            "kind": node.kind,
            "column_names": list(df.columns)
        }

        exported_count += 1

    # Write enhanced metadata
    enhanced_metadata_path = output_path / "dataset.json"
    write_enhanced_metadata(
        dataset_name=dataset.metadata.name,
        dataset_version=dataset.version,
        master_seed=existing_metadata.get("master_seed", 0),
        tables=tables_metadata,
        schema_path=Path(schema_path),
        output_path=enhanced_metadata_path,
        generation_stats={
            "exported_format": format,
            "total_tables": exported_count,
            "total_rows": sum(t["rows"] for t in tables_metadata.values())
        }
    )

    console.print(f"\n[bold green]✅ Export complete![/bold green]")
    console.print(f"  • Exported {exported_count} tables")
    console.print(f"  • Format: {format.upper()}")
    console.print(f"  • Output: {output_dir}")
    if format == 'csv':
        console.print(f"  • Manifest files: *.csv.manifest (Keboola compatible)")
    console.print(f"  • Metadata: dataset.json")


if __name__ == '__main__':
    cli()
