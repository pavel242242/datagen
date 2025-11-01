"""CLI tests for Phase 1 - schema validation and DAG display."""

import json
import sys
from pathlib import Path


def test_schema_validation_and_dag():
    """
    Manual test to verify Phase 1 CLI integration.

    Run with:
        python tests/test_phase1_cli.py
    """
    from datagen.core.schema import validate_schema
    from datagen.core.dag import build_dag
    from rich.console import Console
    from rich.tree import Tree
    from rich.table import Table

    console = Console()

    # Load schema
    schema_path = Path("examples/simple_users_events.json")
    console.print(f"\n[bold blue]📋 Loading schema:[/bold blue] {schema_path}")

    with open(schema_path) as f:
        schema_dict = json.load(f)

    # Validate
    console.print("[bold green]✓[/bold green] Parsing and validating schema...")
    try:
        dataset = validate_schema(schema_dict)
        console.print(f"[bold green]✓[/bold green] Schema valid: {dataset.metadata.name}")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Validation failed: {e}")
        return 1

    # Build DAG
    console.print("\n[bold blue]🔗 Building DAG...[/bold blue]")
    try:
        dag = build_dag(dataset)
        console.print(f"[bold green]✓[/bold green] DAG built: {len(dag)} levels")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] DAG build failed: {e}")
        return 1

    # Display DAG
    console.print("\n[bold cyan]Generation Order:[/bold cyan]")
    for i, level in enumerate(dag):
        console.print(f"  Level {i}: {', '.join(level)}")

    # Display node summary
    console.print("\n[bold cyan]Nodes:[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Kind")
    table.add_column("PK")
    table.add_column("Parents")
    table.add_column("Columns")

    for node in dataset.nodes:
        table.add_row(
            node.id,
            node.kind,
            node.pk,
            ", ".join(node.parents) if node.parents else "-",
            str(len(node.columns))
        )

    console.print(table)

    # Display constraints summary
    console.print("\n[bold cyan]Constraints:[/bold cyan]")
    if dataset.constraints.unique:
        console.print(f"  Unique: {len(dataset.constraints.unique)} columns")
    if dataset.constraints.foreign_keys:
        console.print(f"  Foreign Keys: {len(dataset.constraints.foreign_keys)} relations")
    if dataset.constraints.ranges:
        console.print(f"  Ranges: {len(dataset.constraints.ranges)} checks")

    console.print("\n[bold green]✓ Phase 1 Complete![/bold green] Schema validation and DAG building working.\n")
    return 0


if __name__ == "__main__":
    sys.exit(test_schema_validation_and_dag())
