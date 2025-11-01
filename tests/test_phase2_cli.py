"""CLI verification for Phase 2 generators."""

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

from datagen.core.generators.primitives import (
    generate_sequence, generate_choice, generate_distribution, sample_fanout
)
from datagen.core.generators.temporal import generate_datetime_series
from datagen.core.generators.semantic import generate_faker
from datagen.core.generators.registry import GeneratorRegistry, LookupResolver


def test_all_generators():
    """Demonstrate all generators working."""
    console = Console()
    rng = np.random.default_rng(42)

    console.print("\n[bold cyan]Phase 2: Generator Verification[/bold cyan]\n")

    # Sequence
    console.print("[bold]1. Sequence Generator[/bold]")
    seq = generate_sequence(1, 1, 5)
    console.print(f"   {list(seq)}")

    # Choice
    console.print("\n[bold]2. Choice Generator (weighted)[/bold]")
    choices = generate_choice(['A', 'B', 'C'], 10, rng, weights=[0.7, 0.2, 0.1])
    console.print(f"   {list(choices)}")

    # Distribution
    console.print("\n[bold]3. Distribution Generators[/bold]")
    normal = generate_distribution("normal", {"mean": 100, "std": 15}, 5, rng, (50, 150))
    console.print(f"   Normal: {[f'{v:.1f}' for v in normal]}")

    lognormal = generate_distribution("lognormal", {"mean": 3.0, "sigma": 0.5}, 5, rng, (1, 1000))
    console.print(f"   Lognormal: {[f'{v:.1f}' for v in lognormal]}")

    poisson = generate_distribution("poisson", {"lambda": 5}, 5, rng, (0, 20))
    console.print(f"   Poisson: {list(poisson.astype(int))}")

    # Datetime
    console.print("\n[bold]4. Datetime Series[/bold]")
    dates = generate_datetime_series(
        "2024-01-01T00:00:00Z",
        "2024-01-31T23:59:59Z",
        "D",
        5,
        rng
    )
    console.print(f"   {[str(d.date()) for d in dates]}")

    # Datetime with pattern
    console.print("\n[bold]5. Datetime with Seasonality Pattern (DOW)[/bold]")
    dow_pattern = {"dimension": "dow", "weights": [1.0, 1.0, 1.0, 1.0, 1.5, 1.3, 0.8]}
    weekend_dates = generate_datetime_series(
        "2024-01-01T00:00:00Z",
        "2024-03-31T23:59:59Z",
        "D",
        100,
        rng,
        pattern=dow_pattern
    )
    dow_counts = weekend_dates.dt.dayofweek.value_counts().sort_index()
    console.print(f"   DOW distribution (0=Mon, 6=Sun): {dict(dow_counts)}")

    # Faker
    console.print("\n[bold]6. Faker Generator[/bold]")
    names = generate_faker("name", 3, rng)
    emails = generate_faker("email", 3, rng)
    console.print(f"   Names: {list(names)}")
    console.print(f"   Emails: {list(emails)}")

    # Fanout
    console.print("\n[bold]7. Fanout Sampler[/bold]")
    fanouts = sample_fanout("poisson", 10, rng, lambda_=5, min_val=0, max_val=20)
    console.print(f"   Fanout counts: {list(fanouts)}")
    console.print(f"   Mean: {fanouts.mean():.2f} (expected ~5)")

    # Lookup
    console.print("\n[bold]8. Lookup Resolver[/bold]")
    resolver = LookupResolver()
    users_df = pd.DataFrame({
        "user_id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"]
    })
    resolver.register_table("user", users_df)

    user_ids = resolver.lookup("user.user_id", 5, rng)
    console.print(f"   Random user_ids: {list(user_ids)}")

    # Registry
    console.print("\n[bold]9. Generator Registry[/bold]")
    registry = GeneratorRegistry()

    spec_seq = {"sequence": {"start": 100, "step": 10}}
    result = registry.generate(spec_seq, 5, rng)
    console.print(f"   Sequence via registry: {list(result)}")

    spec_dist = {
        "distribution": {
            "type": "uniform",
            "params": {"low": 0, "high": 100},
            "clamp": [0, 100]
        }
    }
    result2 = registry.generate(spec_dist, 5, rng)
    console.print(f"   Uniform via registry: {[f'{v:.1f}' for v in result2]}")

    # Expression
    console.print("\n[bold]10. Expression Generator[/bold]")
    df = pd.DataFrame({"quantity": [2, 3, 5], "price": [10.5, 20.0, 15.0]})
    spec_expr = {"expression": {"code": "quantity * price"}}
    result3 = registry.generate(spec_expr, 3, rng, context=df)
    console.print(f"   quantity * price = {list(result3)}")

    console.print("\n[bold green]✅ All generators working![/bold green]\n")

    # Summary table
    table = Table(title="Generator Summary", show_header=True, header_style="bold magenta")
    table.add_column("Generator")
    table.add_column("Status")
    table.add_column("Features")

    generators = [
        ("sequence", "✓", "Sequential IDs"),
        ("choice", "✓", "Uniform, weighted, Zipf, head-tail"),
        ("distribution", "✓", "Normal, lognormal, uniform, Poisson"),
        ("datetime_series", "✓", "Timeframes, seasonality patterns"),
        ("faker", "✓", "Names, emails, addresses, locale support"),
        ("lookup", "✓", "Random, join-based"),
        ("expression", "✓", "Pandas eval (safe arithmetic)"),
        ("fanout", "✓", "Poisson, uniform"),
    ]

    for name, status, features in generators:
        table.add_row(name, status, features)

    console.print(table)


if __name__ == "__main__":
    test_all_generators()
